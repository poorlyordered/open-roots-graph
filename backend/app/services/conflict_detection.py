"""
Conflict detection engine.

Scans the graph for data quality issues and creates Conflict nodes
linking the problematic Claims or Individuals.
"""

import uuid

from neo4j import Driver


def create_id():
    return str(uuid.uuid4())[:12]


class ConflictDetector:
    def __init__(self, driver: Driver):
        self._driver = driver
        self.stats = {"conflicts": 0, "tasks": 0}

    def run_all_checks(self):
        """Run all conflict detection checks."""
        print("Running conflict detection...")
        self._check_child_born_before_parent()
        self._check_death_before_birth()
        self._check_impossible_parent_age()
        self._check_child_born_after_mother_death()
        self._check_child_born_after_father_death()
        self._check_duplicate_individuals()
        self._check_marriage_age()
        print(f"\nConflict detection complete: {self.stats['conflicts']} conflicts, "
              f"{self.stats['tasks']} research tasks")

    def _create_conflict(self, session, description: str, field: str,
                         individual_ids: list[str], severity: str = "high"):
        """Create a Conflict node and link it to the involved individuals."""
        conflict_id = f"conf-{create_id()}"
        session.run("""
            CREATE (cf:Conflict {
                id: $id,
                description: $description,
                field: $field,
                severity: $severity,
                status: 'open',
                created_at: datetime()
            })
        """, id=conflict_id, description=description, field=field, severity=severity)

        for indi_id in individual_ids:
            session.run("""
                MATCH (cf:Conflict {id: $conf_id})
                MATCH (i:Individual {id: $indi_id})
                MERGE (cf)-[:REGARDING]->(i)
            """, conf_id=conflict_id, indi_id=indi_id)

        self.stats["conflicts"] += 1

    def _create_research_task(self, session, title: str, description: str,
                              individual_id: str, priority: str = "medium"):
        """Create a ResearchTask node."""
        task_id = f"task-{create_id()}"
        session.run("""
            CREATE (rt:ResearchTask {
                id: $id,
                title: $title,
                description: $description,
                priority: $priority,
                status: 'todo',
                created_at: datetime()
            })
            WITH rt
            MATCH (i:Individual {id: $indi_id})
            CREATE (rt)-[:TARGETS]->(i)
        """, id=task_id, title=title, description=description,
             priority=priority, indi_id=individual_id)
        self.stats["tasks"] += 1

    def _check_death_before_birth(self):
        """Find individuals whose death year is before their birth year."""
        with self._driver.session() as session:
            results = session.run("""
                MATCH (i:Individual)
                WHERE i.birth_year IS NOT NULL AND i.death_year IS NOT NULL
                  AND i.death_year < i.birth_year
                RETURN i.id AS id, i.name AS name,
                       i.birth_year AS birth, i.death_year AS death
            """)
            for r in results:
                self._create_conflict(
                    session,
                    f"{r['name']}: death ({r['death']}) before birth ({r['birth']})",
                    "chronology",
                    [r["id"]],
                    "critical",
                )
                print(f"  CRITICAL: {r['name']} died before born")

    def _check_child_born_before_parent(self):
        """Find children born before their parents."""
        with self._driver.session() as session:
            results = session.run("""
                MATCH (child:Individual)-[:CHILD_OF]->(f:Family)<-[:SPOUSE_IN]-(parent:Individual)
                WHERE child.birth_year IS NOT NULL AND parent.birth_year IS NOT NULL
                  AND child.birth_year <= parent.birth_year
                RETURN child.id AS child_id, child.name AS child_name,
                       child.birth_year AS child_birth,
                       parent.id AS parent_id, parent.name AS parent_name,
                       parent.birth_year AS parent_birth
            """)
            for r in results:
                self._create_conflict(
                    session,
                    f"{r['child_name']} (b.{r['child_birth']}) born before/same year as "
                    f"parent {r['parent_name']} (b.{r['parent_birth']})",
                    "parent_child_chronology",
                    [r["child_id"], r["parent_id"]],
                    "critical",
                )
                print(f"  CRITICAL: {r['child_name']} born before parent {r['parent_name']}")

    def _check_impossible_parent_age(self):
        """Find parents who were under 14 at child's birth."""
        with self._driver.session() as session:
            results = session.run("""
                MATCH (child:Individual)-[:CHILD_OF]->(f:Family)<-[:SPOUSE_IN]-(parent:Individual)
                WHERE child.birth_year IS NOT NULL AND parent.birth_year IS NOT NULL
                  AND (child.birth_year - parent.birth_year) < 14
                  AND (child.birth_year - parent.birth_year) > 0
                RETURN child.id AS child_id, child.name AS child_name,
                       child.birth_year AS child_birth,
                       parent.id AS parent_id, parent.name AS parent_name,
                       parent.birth_year AS parent_birth,
                       (child.birth_year - parent.birth_year) AS age_at_birth
            """)
            for r in results:
                self._create_conflict(
                    session,
                    f"{r['parent_name']} was only {r['age_at_birth']} when "
                    f"{r['child_name']} was born ({r['child_birth']}). "
                    f"Likely wrong family assignment.",
                    "parent_age",
                    [r["child_id"], r["parent_id"]],
                    "critical",
                )
                self._create_research_task(
                    session,
                    f"Verify parentage of {r['child_name']}",
                    f"{r['parent_name']} was {r['age_at_birth']} at {r['child_name']}'s birth. "
                    f"Check if this child belongs to a different family.",
                    r["child_id"],
                    "critical",
                )
                print(f"  CRITICAL: {r['parent_name']} age {r['age_at_birth']} at "
                      f"{r['child_name']}'s birth")

    def _check_child_born_after_mother_death(self):
        """Find children born after their mother's death."""
        with self._driver.session() as session:
            results = session.run("""
                MATCH (child:Individual)-[:CHILD_OF]->(f:Family)<-[:SPOUSE_IN {role: 'WIFE'}]-(mother:Individual)
                WHERE child.birth_year IS NOT NULL AND mother.death_year IS NOT NULL
                  AND child.birth_year > mother.death_year
                RETURN child.id AS child_id, child.name AS child_name,
                       child.birth_year AS child_birth,
                       mother.id AS mother_id, mother.name AS mother_name,
                       mother.death_year AS mother_death
            """)
            for r in results:
                gap = r["child_birth"] - r["mother_death"]
                self._create_conflict(
                    session,
                    f"{r['child_name']} (b.{r['child_birth']}) born {gap} year(s) after "
                    f"mother {r['mother_name']}'s death ({r['mother_death']})",
                    "mother_death_chronology",
                    [r["child_id"], r["mother_id"]],
                    "critical",
                )
                print(f"  CRITICAL: {r['child_name']} born {gap}y after mother's death")

    def _check_child_born_after_father_death(self):
        """Find children born >1 year after their father's death."""
        with self._driver.session() as session:
            results = session.run("""
                MATCH (child:Individual)-[:CHILD_OF]->(f:Family)<-[:SPOUSE_IN {role: 'HUSBAND'}]-(father:Individual)
                WHERE child.birth_year IS NOT NULL AND father.death_year IS NOT NULL
                  AND child.birth_year > father.death_year + 1
                RETURN child.id AS child_id, child.name AS child_name,
                       child.birth_year AS child_birth,
                       father.id AS father_id, father.name AS father_name,
                       father.death_year AS father_death
            """)
            for r in results:
                gap = r["child_birth"] - r["father_death"]
                self._create_conflict(
                    session,
                    f"{r['child_name']} (b.{r['child_birth']}) born {gap} year(s) after "
                    f"father {r['father_name']}'s death ({r['father_death']})",
                    "father_death_chronology",
                    [r["child_id"], r["father_id"]],
                    "high",
                )
                print(f"  HIGH: {r['child_name']} born {gap}y after father's death")

    def _check_duplicate_individuals(self):
        """Find potential duplicate individuals (same name + same birth year)."""
        with self._driver.session() as session:
            results = session.run("""
                MATCH (i:Individual)
                WHERE i.name IS NOT NULL AND i.birth_year IS NOT NULL
                WITH i.name AS name, i.birth_year AS birth_year,
                     collect(i.id) AS ids, count(*) AS cnt
                WHERE cnt > 1
                RETURN name, birth_year, ids, cnt
                ORDER BY cnt DESC
            """)
            for r in results:
                self._create_conflict(
                    session,
                    f"Potential duplicate: {r['name']} (b.{r['birth_year']}) — "
                    f"{r['cnt']} records found",
                    "duplicate",
                    r["ids"],
                    "medium",
                )
                self._create_research_task(
                    session,
                    f"Resolve duplicate: {r['name']} (b.{r['birth_year']})",
                    f"Found {r['cnt']} records for {r['name']} born {r['birth_year']}. "
                    f"Determine if these are the same person or different individuals. "
                    f"IDs: {', '.join(r['ids'])}",
                    r["ids"][0],
                    "medium",
                )
                print(f"  MEDIUM: Duplicate {r['name']} (b.{r['birth_year']}) x{r['cnt']}")

    def _check_marriage_age(self):
        """Find individuals married before age 14."""
        with self._driver.session() as session:
            results = session.run("""
                MATCH (i:Individual)-[:SPOUSE_IN]->(f:Family)
                WHERE i.birth_year IS NOT NULL AND f.marriage_year IS NOT NULL
                  AND (f.marriage_year - i.birth_year) < 14
                  AND (f.marriage_year - i.birth_year) >= 0
                RETURN i.id AS id, i.name AS name,
                       i.birth_year AS birth, f.marriage_year AS marriage,
                       (f.marriage_year - i.birth_year) AS age_at_marriage
            """)
            for r in results:
                self._create_conflict(
                    session,
                    f"{r['name']} married at age {r['age_at_marriage']} "
                    f"(b.{r['birth']}, m.{r['marriage']})",
                    "marriage_age",
                    [r["id"]],
                    "high",
                )
                print(f"  HIGH: {r['name']} married at age {r['age_at_marriage']}")
