from app.models.evidence import Claim, Conflict, ResearchTask, EvidenceSummary
from app.repositories.base import BaseRepository


class EvidenceRepository(BaseRepository):

    # --- Claims ---

    def get_claims_for_individual(self, indi_id: str) -> list[Claim]:
        rows = self._read("""
            MATCH (c:Claim)-[:ABOUT]->(i:Individual {id: $id})
            OPTIONAL MATCH (c)-[:EXTRACTED_FROM]->(r:Record)
            RETURN c.id AS id, c.claim_type AS claim_type, c.value AS value,
                   c.confidence AS confidence, c.status AS status,
                   c.extracted_by AS extracted_by,
                   i.id AS individual_id, i.name AS individual_name,
                   r.title AS record_title
            ORDER BY c.claim_type, c.confidence DESC
        """, id=indi_id)
        return [Claim(**r) for r in rows]

    def update_claim(self, claim_id: str, status: str | None = None,
                     confidence: float | None = None):
        sets = []
        params: dict = {"id": claim_id}
        if status is not None:
            sets.append("c.status = $status")
            params["status"] = status
        if confidence is not None:
            sets.append("c.confidence = $confidence")
            params["confidence"] = confidence
        if sets:
            self._write(f"""
                MATCH (c:Claim {{id: $id}})
                SET {', '.join(sets)}
            """, **params)

    # --- Conflicts ---

    def get_conflicts(
        self,
        status: str | None = None,
        severity: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Conflict], int]:
        where_clauses = []
        params: dict = {"limit": limit, "offset": offset}

        if status:
            where_clauses.append("cf.status = $status")
            params["status"] = status
        if severity:
            where_clauses.append("cf.severity = $severity")
            params["severity"] = severity

        where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        count_row = self._read_single(
            f"MATCH (cf:Conflict) {where} RETURN count(cf) AS total", **params
        )
        total = count_row["total"] if count_row else 0

        rows = self._read(f"""
            MATCH (cf:Conflict)
            {where}
            OPTIONAL MATCH (cf)-[:REGARDING]->(i:Individual)
            WITH cf, collect({{id: i.id, name: i.name, birth_year: i.birth_year}}) AS individuals
            RETURN cf.id AS id, cf.description AS description,
                   cf.field AS field, cf.severity AS severity,
                   cf.status AS status, cf.resolution AS resolution,
                   individuals
            ORDER BY
                CASE cf.severity
                    WHEN 'critical' THEN 0
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                END,
                cf.created_at DESC
            SKIP $offset LIMIT $limit
        """, **params)

        conflicts = [Conflict(**r) for r in rows]
        return conflicts, total

    def get_conflicts_for_individual(self, indi_id: str) -> list[Conflict]:
        rows = self._read("""
            MATCH (cf:Conflict)-[:REGARDING]->(i:Individual {id: $id})
            OPTIONAL MATCH (cf)-[:REGARDING]->(other:Individual)
            WITH cf, collect({id: other.id, name: other.name, birth_year: other.birth_year}) AS individuals
            RETURN cf.id AS id, cf.description AS description,
                   cf.field AS field, cf.severity AS severity,
                   cf.status AS status, cf.resolution AS resolution,
                   individuals
            ORDER BY
                CASE cf.severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 ELSE 2 END
        """, id=indi_id)
        return [Conflict(**r) for r in rows]

    def update_conflict(self, conflict_id: str, status: str, resolution: str | None = None):
        self._write("""
            MATCH (cf:Conflict {id: $id})
            SET cf.status = $status, cf.resolution = $resolution,
                cf.resolved_at = CASE WHEN $status = 'resolved' THEN datetime() ELSE NULL END
        """, id=conflict_id, status=status, resolution=resolution)

    # --- Research Tasks ---

    def get_tasks(
        self,
        status: str | None = None,
        priority: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[ResearchTask], int]:
        where_clauses = []
        params: dict = {"limit": limit, "offset": offset}

        if status:
            where_clauses.append("rt.status = $status")
            params["status"] = status
        if priority:
            where_clauses.append("rt.priority = $priority")
            params["priority"] = priority

        where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        count_row = self._read_single(
            f"MATCH (rt:ResearchTask) {where} RETURN count(rt) AS total", **params
        )
        total = count_row["total"] if count_row else 0

        rows = self._read(f"""
            MATCH (rt:ResearchTask)
            {where}
            OPTIONAL MATCH (rt)-[:TARGETS]->(i:Individual)
            RETURN rt.id AS id, rt.title AS title, rt.description AS description,
                   rt.priority AS priority, rt.status AS status,
                   i.name AS target_name, i.id AS target_id
            ORDER BY
                CASE rt.priority
                    WHEN 'critical' THEN 0
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                END
            SKIP $offset LIMIT $limit
        """, **params)

        tasks = [ResearchTask(**r) for r in rows]
        return tasks, total

    def update_task(self, task_id: str, status: str):
        self._write("""
            MATCH (rt:ResearchTask {id: $id})
            SET rt.status = $status,
                rt.completed_at = CASE WHEN $status = 'done' THEN datetime() ELSE NULL END
        """, id=task_id, status=status)

    # --- Summary ---

    def get_summary(self) -> EvidenceSummary:
        # Batch counts using subqueries to avoid cartesian products
        counts = self._read_single("""
            CALL { MATCH (c:Claim) RETURN count(c) AS total_claims }
            CALL { MATCH (cf:Conflict) RETURN count(cf) AS total_conflicts }
            CALL { MATCH (cfo:Conflict {status: 'open'}) RETURN count(cfo) AS open_conflicts }
            CALL { MATCH (rt:ResearchTask) RETURN count(rt) AS total_tasks }
            CALL { MATCH (rto:ResearchTask) WHERE rto.status IN ['todo', 'in_progress'] RETURN count(rto) AS open_tasks }
            RETURN total_claims, total_conflicts, open_conflicts, total_tasks, open_tasks
        """)

        # Claims by type
        type_rows = self._read("""
            MATCH (c:Claim)
            RETURN c.claim_type AS type, count(c) AS count
            ORDER BY count DESC
        """)
        claims_by_type = {r["type"]: r["count"] for r in type_rows}

        # Conflicts by severity
        sev_rows = self._read("""
            MATCH (cf:Conflict)
            RETURN cf.severity AS severity, count(cf) AS count
        """)
        conflicts_by_severity = {r["severity"]: r["count"] for r in sev_rows}

        # Completeness in a single query
        comp = self._read_single("""
            MATCH (i:Individual)
            WITH count(i) AS total,
                 count(CASE WHEN i.birth_year IS NOT NULL THEN 1 END) AS with_birth,
                 count(CASE WHEN i.death_year IS NOT NULL THEN 1 END) AS with_death
            OPTIONAL MATCH (bp:Individual)-[:BORN_IN]->()
            WITH total, with_birth, with_death, count(DISTINCT bp) AS with_place
            OPTIONAL MATCH (si:Individual)-[:CITED_IN]->()
            RETURN total, with_birth, with_death, with_place, count(DISTINCT si) AS with_source
        """)

        completeness = {}
        if comp and comp["total"] > 0:
            t = comp["total"]
            completeness = {
                "birth_date": round(comp["with_birth"] / t * 100, 1),
                "death_date": round(comp["with_death"] / t * 100, 1),
                "birth_place": round(comp["with_place"] / t * 100, 1),
                "source_citation": round(comp["with_source"] / t * 100, 1),
            }

        return EvidenceSummary(
            total_claims=counts["total_claims"] if counts else 0,
            total_conflicts=counts["total_conflicts"] if counts else 0,
            open_conflicts=counts["open_conflicts"] if counts else 0,
            total_tasks=counts["total_tasks"] if counts else 0,
            open_tasks=counts["open_tasks"] if counts else 0,
            claims_by_type=claims_by_type,
            conflicts_by_severity=conflicts_by_severity,
            completeness=completeness,
        )
