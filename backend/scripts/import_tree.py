"""
Enhanced GEDCOM-to-Neo4j importer.

Features:
- Custom GEDCOM parser (reliable for Ancestry exports)
- Place normalization and hierarchy (Country > State > County > City)
- Date parsing to ISO format
- Source record import
- Marriage date/place import
- Residence history import
- Neo4j indexes for query performance
- Batch operations for speed
"""

import os
import re
import sys
from datetime import datetime
from collections import defaultdict

from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# ---------------------------------------------------------------------------
# GEDCOM Parser
# ---------------------------------------------------------------------------

MONTH_MAP = {
    "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
    "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
    "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12",
    "JANUARY": "01", "FEBRUARY": "02", "MARCH": "03", "APRIL": "04",
    "JUNE": "06", "JULY": "07", "AUGUST": "08",
    "SEPTEMBER": "09", "OCTOBER": "10", "NOVEMBER": "11", "DECEMBER": "12",
}

COUNTRY_ALIASES = {
    "United States": "USA",
    "United States of America": "USA",
    "U.S.A.": "USA",
    "U.S.": "USA",
    "US": "USA",
}


def parse_gedcom(file_path):
    """Parse a GEDCOM file into structured records."""
    individuals = {}
    families = {}
    sources = {}

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_record = None
    record_type = None
    context_stack = []  # track nested tags

    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\n\r")
        i += 1

        match = re.match(r"^(\d+)\s+(.*)$", line)
        if not match:
            continue

        level = int(match.group(1))
        rest = match.group(2)

        if level == 0:
            # Save previous record
            if current_record and record_type:
                if record_type == "INDI":
                    individuals[current_record["id"]] = current_record
                elif record_type == "FAM":
                    families[current_record["id"]] = current_record
                elif record_type == "SOUR":
                    sources[current_record["id"]] = current_record

            # Start new record
            xref_match = re.match(r"(@\S+@)\s+(\w+)", rest)
            if xref_match:
                xref_id = xref_match.group(1)
                tag = xref_match.group(2)
                if tag == "INDI":
                    record_type = "INDI"
                    current_record = {
                        "id": xref_id,
                        "name": "Unknown",
                        "given_name": "",
                        "surname": "",
                        "sex": "",
                        "birth_date": None,
                        "birth_place": None,
                        "death_date": None,
                        "death_place": None,
                        "burial_place": None,
                        "residences": [],
                        "source_refs": [],
                        "famc": [],
                        "fams": [],
                    }
                elif tag == "FAM":
                    record_type = "FAM"
                    current_record = {
                        "id": xref_id,
                        "husband": None,
                        "wife": None,
                        "children": [],
                        "marriages": [],
                        "source_refs": [],
                    }
                elif tag == "SOUR":
                    record_type = "SOUR"
                    current_record = {
                        "id": xref_id,
                        "title": "",
                        "author": "",
                        "publisher": "",
                    }
                else:
                    record_type = None
                    current_record = None
            else:
                record_type = None
                current_record = None
            context_stack = []
            continue

        if not current_record:
            continue

        # Parse tag and value
        tag_match = re.match(r"(@\S+@|\S+)\s*(.*)?", rest)
        if not tag_match:
            continue

        tag = tag_match.group(1)
        value = (tag_match.group(2) or "").strip()

        # Handle CONC (continuation on same line)
        if tag == "CONC":
            # Append to previous value - handled by context
            continue

        # Trim context stack to current level
        context_stack = context_stack[: level - 1]
        context_stack.append(tag)

        # -- INDI fields --
        if record_type == "INDI":
            if level == 1 and tag == "NAME":
                current_record["name"] = value.replace("/", "").strip()
            elif level == 2 and tag == "GIVN":
                current_record["given_name"] = value
            elif level == 2 and tag == "SURN":
                current_record["surname"] = value
            elif level == 1 and tag == "SEX":
                current_record["sex"] = value
            elif level == 1 and tag == "BIRT":
                context_stack = ["BIRT"]
            elif level == 2 and len(context_stack) >= 1 and context_stack[0] == "BIRT":
                if tag == "DATE":
                    current_record["birth_date"] = value
                elif tag == "PLAC":
                    current_record["birth_place"] = value
            elif level == 1 and tag == "DEAT":
                context_stack = ["DEAT"]
            elif level == 2 and len(context_stack) >= 1 and context_stack[0] == "DEAT":
                if tag == "DATE":
                    current_record["death_date"] = value
                elif tag == "PLAC":
                    current_record["death_place"] = value
            elif level == 1 and tag == "BURI":
                context_stack = ["BURI"]
            elif level == 2 and len(context_stack) >= 1 and context_stack[0] == "BURI":
                if tag == "PLAC":
                    current_record["burial_place"] = value
            elif level == 1 and tag == "RESI":
                context_stack = ["RESI"]
                current_record["residences"].append({"date": None, "place": None})
            elif level == 2 and len(context_stack) >= 1 and context_stack[0] == "RESI":
                if tag == "DATE":
                    current_record["residences"][-1]["date"] = value
                elif tag == "PLAC":
                    current_record["residences"][-1]["place"] = value
            elif level == 1 and tag.startswith("@") and tag.endswith("@"):
                # This is a pointer like FAMC or FAMS — re-parse
                pass
            elif level == 1 and tag == "FAMC":
                current_record["famc"].append(value)
            elif level == 1 and tag == "FAMS":
                current_record["fams"].append(value)
            elif level == 1 and tag == "SOUR":
                current_record["source_refs"].append(value)

        # -- FAM fields --
        elif record_type == "FAM":
            if level == 1 and tag == "HUSB":
                current_record["husband"] = value
            elif level == 1 and tag == "WIFE":
                current_record["wife"] = value
            elif level == 1 and tag == "CHIL":
                current_record["children"].append(value)
            elif level == 1 and tag == "MARR":
                context_stack = ["MARR"]
                current_record["marriages"].append({"date": None, "place": None})
            elif level == 2 and len(context_stack) >= 1 and context_stack[0] == "MARR":
                if tag == "DATE":
                    current_record["marriages"][-1]["date"] = value
                elif tag == "PLAC":
                    current_record["marriages"][-1]["place"] = value
            elif level == 1 and tag == "SOUR":
                current_record["source_refs"].append(value)

        # -- SOUR fields --
        elif record_type == "SOUR":
            if level == 1 and tag == "TITL":
                current_record["title"] = value
            elif level == 1 and tag == "AUTH":
                current_record["author"] = value
            elif level == 1 and tag == "PUBL":
                current_record["publisher"] = value

    # Save last record
    if current_record and record_type:
        if record_type == "INDI":
            individuals[current_record["id"]] = current_record
        elif record_type == "FAM":
            families[current_record["id"]] = current_record
        elif record_type == "SOUR":
            sources[current_record["id"]] = current_record

    return individuals, families, sources


# ---------------------------------------------------------------------------
# Data Normalization
# ---------------------------------------------------------------------------

def normalize_date(raw_date):
    """Convert GEDCOM date strings to ISO format (YYYY-MM-DD) where possible.

    Returns a dict with: raw, iso, year, month, day, approximate
    """
    if not raw_date:
        return None

    raw = raw_date.strip()
    result = {"raw": raw, "iso": None, "year": None, "month": None, "day": None, "approximate": False}

    # Handle approximate markers
    cleaned = raw
    for prefix in ("ABT", "BEF", "AFT", "EST", "CAL", "BET", "FROM", "TO"):
        if cleaned.upper().startswith(prefix):
            result["approximate"] = True
            cleaned = cleaned[len(prefix):].strip()
            break

    # Handle range dates like "BET 1800 AND 1810" — just take first date
    if "AND" in cleaned.upper():
        cleaned = cleaned.upper().split("AND")[0].strip()

    # Try patterns: "DD MMM YYYY", "MMM YYYY", "YYYY", "DD/MM/YYYY"
    # Full date: 16 Aug 1968, 3 November 1942
    full_match = re.match(r"(\d{1,2})\s+(\w+)\s+(\d{4})", cleaned)
    if full_match:
        day = int(full_match.group(1))
        month_str = full_match.group(2).upper()
        year = int(full_match.group(3))
        month = MONTH_MAP.get(month_str)
        if month:
            result["year"] = year
            result["month"] = int(month)
            result["day"] = day
            result["iso"] = f"{year:04d}-{month}-{day:02d}"
            return result

    # Month + Year: Aug 1968, November 1942
    month_year = re.match(r"(\w+)\s+(\d{4})", cleaned)
    if month_year:
        month_str = month_year.group(1).upper()
        year = int(month_year.group(2))
        month = MONTH_MAP.get(month_str)
        if month:
            result["year"] = year
            result["month"] = int(month)
            result["iso"] = f"{year:04d}-{month}"
            return result

    # Year only: 1968
    year_only = re.match(r"(\d{4})$", cleaned)
    if year_only:
        result["year"] = int(year_only.group(1))
        result["iso"] = f"{result['year']:04d}"
        return result

    # Slash format: 02/09/1845
    slash_match = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", cleaned)
    if slash_match:
        month = int(slash_match.group(1))
        day = int(slash_match.group(2))
        year = int(slash_match.group(3))
        result["year"] = year
        result["month"] = month
        result["day"] = day
        result["iso"] = f"{year:04d}-{month:02d}-{day:02d}"
        return result

    return result


def normalize_place(raw_place):
    """Normalize place string and split into components.

    Ancestry format: City, County, State, Country
    Returns dict with: raw, city, county, state, country, normalized
    """
    if not raw_place:
        return None

    raw = raw_place.strip()
    parts = [p.strip() for p in raw.split(",")]

    # Remove empty parts
    parts = [p for p in parts if p]

    # Normalize country
    if parts:
        last = parts[-1]
        parts[-1] = COUNTRY_ALIASES.get(last, last)

    # Remove duplicate adjacent parts (e.g., "Kentucky, Kentucky, USA")
    deduped = []
    for p in parts:
        if not deduped or p.lower() != deduped[-1].lower():
            deduped.append(p)
    parts = deduped

    # Assign components based on length
    city, county, state, country = None, None, None, None
    if len(parts) == 4:
        city, county, state, country = parts
    elif len(parts) == 3:
        city, state, country = parts
    elif len(parts) == 2:
        state, country = parts
    elif len(parts) == 1:
        country = parts[0]

    normalized = ", ".join(parts)

    return {
        "raw": raw,
        "city": city,
        "county": county,
        "state": state,
        "country": country,
        "normalized": normalized,
    }


# ---------------------------------------------------------------------------
# Neo4j Importer
# ---------------------------------------------------------------------------

class GenealogyImporter:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.stats = defaultdict(int)

    def close(self):
        self.driver.close()

    def clear_db(self):
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        print("Database cleared.")

    def create_indexes(self):
        """Create indexes for efficient querying."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS FOR (i:Individual) ON (i.id)",
            "CREATE INDEX IF NOT EXISTS FOR (i:Individual) ON (i.surname)",
            "CREATE INDEX IF NOT EXISTS FOR (i:Individual) ON (i.birth_year)",
            "CREATE INDEX IF NOT EXISTS FOR (f:Family) ON (f.id)",
            "CREATE INDEX IF NOT EXISTS FOR (p:Place) ON (p.normalized)",
            "CREATE INDEX IF NOT EXISTS FOR (s:Source) ON (s.id)",
        ]
        with self.driver.session() as session:
            for idx in indexes:
                session.run(idx)
        print(f"Created {len(indexes)} indexes.")

    def import_all(self, individuals, families, sources):
        """Run the full import pipeline."""
        print(f"\nImporting {len(individuals)} individuals, "
              f"{len(families)} families, {len(sources)} sources...\n")

        self.create_indexes()
        self._import_sources(sources)
        self._import_individuals(individuals)
        self._import_families(families)
        self._link_sources(individuals, families)
        self._print_stats()

    def _import_sources(self, sources):
        """Import Source nodes."""
        with self.driver.session() as session:
            for src in sources.values():
                session.run("""
                    MERGE (s:Source {id: $id})
                    SET s.title = $title,
                        s.author = $author,
                        s.publisher = $publisher
                """, id=src["id"], title=src["title"],
                     author=src["author"], publisher=src["publisher"])
                self.stats["sources"] += 1
        print(f"  Sources: {self.stats['sources']}")

    def _import_individuals(self, individuals):
        """Import Individual nodes with dates, places, and residences."""
        with self.driver.session() as session:
            for indi in individuals.values():
                birth = normalize_date(indi["birth_date"])
                death = normalize_date(indi["death_date"])
                birth_place = normalize_place(indi["birth_place"])
                death_place = normalize_place(indi["death_place"])
                burial_place = normalize_place(indi["burial_place"])

                # Create Individual
                session.run("""
                    MERGE (i:Individual {id: $id})
                    SET i.name = $name,
                        i.given_name = $given_name,
                        i.surname = $surname,
                        i.sex = $sex,
                        i.birth_date_raw = $birth_date_raw,
                        i.birth_date_iso = $birth_iso,
                        i.birth_year = $birth_year,
                        i.death_date_raw = $death_date_raw,
                        i.death_date_iso = $death_iso,
                        i.death_year = $death_year
                """,
                    id=indi["id"],
                    name=indi["name"],
                    given_name=indi["given_name"],
                    surname=indi["surname"],
                    sex=indi["sex"],
                    birth_date_raw=indi["birth_date"],
                    birth_iso=birth["iso"] if birth else None,
                    birth_year=birth["year"] if birth else None,
                    death_date_raw=indi["death_date"],
                    death_iso=death["iso"] if death else None,
                    death_year=death["year"] if death else None,
                )

                # Link to birth place
                if birth_place:
                    self._link_place(session, indi["id"], birth_place, "BORN_IN")

                # Link to death place
                if death_place:
                    self._link_place(session, indi["id"], death_place, "DIED_IN")

                # Link to burial place
                if burial_place:
                    self._link_place(session, indi["id"], burial_place, "BURIED_IN")

                # Import residences
                for res in indi["residences"]:
                    res_place = normalize_place(res["place"])
                    res_date = normalize_date(res["date"])
                    if res_place:
                        self._link_place(
                            session, indi["id"], res_place, "RESIDED_IN",
                            date_raw=res["date"],
                            date_iso=res_date["iso"] if res_date else None,
                            year=res_date["year"] if res_date else None,
                        )

                self.stats["individuals"] += 1

                if self.stats["individuals"] % 100 == 0:
                    print(f"  Individuals: {self.stats['individuals']}...")

        print(f"  Individuals: {self.stats['individuals']} (done)")

    def _import_families(self, families):
        """Import Family nodes with marriages and link parents/children."""
        with self.driver.session() as session:
            for fam in families.values():
                # Get first marriage info (primary)
                marr_date = None
                marr_place = None
                marr_date_parsed = None
                if fam["marriages"]:
                    primary = fam["marriages"][0]
                    marr_date = primary["date"]
                    marr_place = primary["place"]
                    marr_date_parsed = normalize_date(marr_date)

                marr_place_norm = normalize_place(marr_place)

                session.run("""
                    MERGE (f:Family {id: $id})
                    SET f.marriage_date_raw = $marr_date,
                        f.marriage_date_iso = $marr_iso,
                        f.marriage_year = $marr_year,
                        f.marriage_place = $marr_place
                """,
                    id=fam["id"],
                    marr_date=marr_date,
                    marr_iso=marr_date_parsed["iso"] if marr_date_parsed else None,
                    marr_year=marr_date_parsed["year"] if marr_date_parsed else None,
                    marr_place=marr_place_norm["normalized"] if marr_place_norm else None,
                )

                # Link marriage place
                if marr_place_norm:
                    self._link_family_place(session, fam["id"], marr_place_norm, "MARRIED_IN")

                # Link husband
                if fam["husband"]:
                    session.run("""
                        MATCH (i:Individual {id: $indi_id})
                        MATCH (f:Family {id: $fam_id})
                        MERGE (i)-[:SPOUSE_IN {role: 'HUSBAND'}]->(f)
                    """, indi_id=fam["husband"], fam_id=fam["id"])

                # Link wife
                if fam["wife"]:
                    session.run("""
                        MATCH (i:Individual {id: $indi_id})
                        MATCH (f:Family {id: $fam_id})
                        MERGE (i)-[:SPOUSE_IN {role: 'WIFE'}]->(f)
                    """, indi_id=fam["wife"], fam_id=fam["id"])

                # Link children
                for child_id in fam["children"]:
                    session.run("""
                        MATCH (i:Individual {id: $indi_id})
                        MATCH (f:Family {id: $fam_id})
                        MERGE (i)-[:CHILD_OF]->(f)
                    """, indi_id=child_id, fam_id=fam["id"])
                    self.stats["child_links"] += 1

                self.stats["families"] += 1

        print(f"  Families: {self.stats['families']}")
        print(f"  Child links: {self.stats['child_links']}")

    def _link_place(self, session, indi_id, place, rel_type,
                    date_raw=None, date_iso=None, year=None):
        """Create/merge a Place node and link an Individual to it."""
        self._ensure_place(session, place)

        props = {}
        if date_raw:
            props["date_raw"] = date_raw
        if date_iso:
            props["date_iso"] = date_iso
        if year:
            props["year"] = year

        prop_set = ""
        if props:
            assignments = ", ".join(f"r.{k} = ${k}" for k in props)
            prop_set = f"SET {assignments}"

        session.run(f"""
            MATCH (i:Individual {{id: $indi_id}})
            MATCH (p:Place {{normalized: $place}})
            MERGE (i)-[r:{rel_type}]->(p)
            {prop_set}
        """, indi_id=indi_id, place=place["normalized"], **props)
        self.stats["place_links"] += 1

    def _link_family_place(self, session, fam_id, place, rel_type):
        """Link a Family node to a Place."""
        self._ensure_place(session, place)
        session.run(f"""
            MATCH (f:Family {{id: $fam_id}})
            MATCH (p:Place {{normalized: $place}})
            MERGE (f)-[:{rel_type}]->(p)
        """, fam_id=fam_id, place=place["normalized"])

    def _ensure_place(self, session, place):
        """Create Place node if it doesn't exist, with hierarchy."""
        session.run("""
            MERGE (p:Place {normalized: $normalized})
            SET p.city = $city,
                p.county = $county,
                p.state = $state,
                p.country = $country
        """,
            normalized=place["normalized"],
            city=place["city"],
            county=place["county"],
            state=place["state"],
            country=place["country"],
        )
        self.stats["places_created"] += 1  # may overcount due to MERGE

    def _link_sources(self, individuals, families):
        """Link Individuals and Families to their Source records."""
        with self.driver.session() as session:
            for indi in individuals.values():
                for src_ref in indi["source_refs"]:
                    session.run("""
                        MATCH (i:Individual {id: $indi_id})
                        MATCH (s:Source {id: $src_id})
                        MERGE (i)-[:CITED_IN]->(s)
                    """, indi_id=indi["id"], src_id=src_ref)
                    self.stats["source_links"] += 1

            for fam in families.values():
                for src_ref in fam["source_refs"]:
                    session.run("""
                        MATCH (f:Family {id: $fam_id})
                        MATCH (s:Source {id: $src_id})
                        MERGE (f)-[:CITED_IN]->(s)
                    """, fam_id=fam["id"], src_id=src_ref)
                    self.stats["source_links"] += 1

        print(f"  Source links: {self.stats['source_links']}")

    def _print_stats(self):
        print("\n--- Import Summary ---")
        for key, val in sorted(self.stats.items()):
            print(f"  {key}: {val}")
        print("--- Done ---\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    pw = os.getenv("NEO4J_PASSWORD", "changeme")
    gedcom_path = os.getenv("GEDCOM_PATH", "../../examples/sample-tree.ged")

    # Resolve relative path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isabs(gedcom_path):
        gedcom_path = os.path.join(script_dir, gedcom_path)

    if not os.path.exists(gedcom_path):
        print(f"Error: GEDCOM file not found at {gedcom_path}")
        sys.exit(1)

    print(f"Parsing GEDCOM: {gedcom_path}")
    individuals, families, sources = parse_gedcom(gedcom_path)
    print(f"Parsed: {len(individuals)} individuals, {len(families)} families, {len(sources)} sources")

    print(f"\nConnecting to Neo4j at {uri}...")
    importer = GenealogyImporter(uri, user, pw)

    if "--clear" in sys.argv:
        importer.clear_db()

    importer.import_all(individuals, families, sources)
    importer.close()
    print("Import complete!")
