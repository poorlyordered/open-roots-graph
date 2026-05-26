"""
Export Neo4j genealogy data to a clean GEDCOM 5.5.1 file.

READ-ONLY against Neo4j. All cleanup/transforms happen in Python memory.

Usage:
    python -m scripts.export_gedcom
"""

import csv
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OUTPUT_GED = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "clean-tree.ged"
)
DEDUP_CSV = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "dedup_candidates.csv"
)

GEDCOM_MAX_LINE = 255

# Month mappings
MONTH_ABBREV = {
    "january": "JAN", "february": "FEB", "march": "MAR", "april": "APR",
    "may": "MAY", "june": "JUN", "july": "JUL", "august": "AUG",
    "september": "SEP", "october": "OCT", "november": "NOV", "december": "DEC",
    "jan": "JAN", "feb": "FEB", "mar": "MAR", "apr": "APR",
    "jun": "JUN", "jul": "JUL", "aug": "AUG", "sep": "SEP",
    "oct": "OCT", "nov": "NOV", "dec": "DEC",
}

MONTH_NUM_TO_ABBREV = {
    1: "JAN", 2: "FEB", 3: "MAR", 4: "APR", 5: "MAY", 6: "JUN",
    7: "JUL", 8: "AUG", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DEC",
}

# Full 50-state abbreviation map
US_STATE_ABBREVS = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}

# Reverse map: full name -> abbreviation (for validation)
US_STATE_NAMES = {v.upper(): v for v in US_STATE_ABBREVS.values()}

COUNTRY_NORMALIZE = {
    "united states": "USA",
    "united states of america": "USA",
    "u.s.a.": "USA",
    "u.s.": "USA",
    "us": "USA",
}

SUFFIX_PATTERN = re.compile(
    r"\b(Jr\.?|Sr\.?|II|III|IV|V|2nd|3rd|4th)\s*$", re.IGNORECASE
)

# Qualifier normalization for GEDCOM dates
QUALIFIER_MAP = {
    "abt": "ABT", "abt.": "ABT", "about": "ABT", "circa": "ABT", "ca": "ABT",
    "bef": "BEF", "bef.": "BEF", "before": "BEF",
    "aft": "AFT", "aft.": "AFT", "after": "AFT",
    "bet": "BET", "bet.": "BET", "between": "BET",
    "est": "EST", "est.": "EST",
    "cal": "CAL", "cal.": "CAL",
    "from": "FROM", "to": "TO",
}

# ---------------------------------------------------------------------------
# Stats tracking
# ---------------------------------------------------------------------------

stats = defaultdict(int)


# ---------------------------------------------------------------------------
# Neo4j Data Extraction (READ-ONLY)
# ---------------------------------------------------------------------------

def extract_individuals(session):
    """Extract all individuals with their properties."""
    rows = session.run("""
        MATCH (i:Individual)
        OPTIONAL MATCH (i)-[:BORN_IN]->(bp:Place)
        OPTIONAL MATCH (i)-[:DIED_IN]->(dp:Place)
        OPTIONAL MATCH (i)-[:BURIED_IN]->(bup:Place)
        RETURN i.id AS id, i.name AS name, i.given_name AS given_name,
               i.surname AS surname, i.sex AS sex,
               i.birth_date_raw AS birth_date_raw, i.birth_date_iso AS birth_date_iso,
               i.birth_year AS birth_year,
               i.death_date_raw AS death_date_raw, i.death_date_iso AS death_date_iso,
               i.death_year AS death_year,
               bp.normalized AS birth_place,
               dp.normalized AS death_place,
               bup.normalized AS burial_place
        ORDER BY i.surname, i.birth_year
    """)
    return [dict(r) for r in rows]


def extract_residences(session):
    """Extract all residence relationships."""
    rows = session.run("""
        MATCH (i:Individual)-[r:RESIDED_IN]->(p:Place)
        RETURN i.id AS indi_id, p.normalized AS place,
               r.date_raw AS date_raw, r.year AS year
        ORDER BY i.id, r.year
    """)
    result = defaultdict(list)
    for r in rows:
        result[r["indi_id"]].append({
            "place": r["place"],
            "date_raw": r["date_raw"],
            "year": r["year"],
        })
    return result


def extract_families(session):
    """Extract all families with spouse and child relationships."""
    rows = session.run("""
        MATCH (f:Family)
        OPTIONAL MATCH (husb:Individual)-[sh:SPOUSE_IN {role: 'HUSBAND'}]->(f)
        OPTIONAL MATCH (wife:Individual)-[sw:SPOUSE_IN {role: 'WIFE'}]->(f)
        RETURN f.id AS id, f.marriage_date_raw AS marriage_date_raw,
               f.marriage_year AS marriage_year, f.marriage_place AS marriage_place,
               husb.id AS husband_id, wife.id AS wife_id
        ORDER BY f.id
    """)
    families = {}
    for r in rows:
        fam_id = r["id"]
        families[fam_id] = {
            "id": fam_id,
            "husband_id": r["husband_id"],
            "wife_id": r["wife_id"],
            "marriage_date_raw": r["marriage_date_raw"],
            "marriage_year": r["marriage_year"],
            "marriage_place": r["marriage_place"],
            "children": [],
        }

    # Fetch children
    child_rows = session.run("""
        MATCH (c:Individual)-[:CHILD_OF]->(f:Family)
        RETURN c.id AS child_id, f.id AS fam_id
        ORDER BY f.id, c.birth_year
    """)
    for r in child_rows:
        fam_id = r["fam_id"]
        if fam_id in families:
            families[fam_id]["children"].append(r["child_id"])

    return families


def extract_family_links(session):
    """Extract CHILD_OF and SPOUSE_IN links per individual."""
    famc = defaultdict(list)  # individual -> list of family IDs (as child)
    fams = defaultdict(list)  # individual -> list of family IDs (as spouse)

    rows = session.run("""
        MATCH (i:Individual)-[:CHILD_OF]->(f:Family)
        RETURN i.id AS indi_id, f.id AS fam_id
    """)
    for r in rows:
        famc[r["indi_id"]].append(r["fam_id"])

    rows = session.run("""
        MATCH (i:Individual)-[:SPOUSE_IN]->(f:Family)
        RETURN i.id AS indi_id, f.id AS fam_id
    """)
    for r in rows:
        fams[r["indi_id"]].append(r["fam_id"])

    return famc, fams


def extract_sources(session):
    """Extract all source records."""
    rows = session.run("""
        MATCH (s:Source)
        RETURN s.id AS id, s.title AS title, s.author AS author,
               s.publisher AS publisher
        ORDER BY s.id
    """)
    return [dict(r) for r in rows]


def extract_source_citations(session):
    """Extract individual -> source links."""
    rows = session.run("""
        MATCH (i:Individual)-[:CITED_IN]->(s:Source)
        RETURN i.id AS indi_id, s.id AS source_id
    """)
    result = defaultdict(list)
    for r in rows:
        result[r["indi_id"]].append(r["source_id"])
    return result


# ---------------------------------------------------------------------------
# In-Memory Cleanup Transforms
# ---------------------------------------------------------------------------

def clean_name(name_str):
    """Title-case a given name, strip whitespace, collapse spaces."""
    if not name_str:
        return name_str
    cleaned = " ".join(name_str.split())  # collapse whitespace
    parts = cleaned.split()
    titled = []
    for p in parts:
        if p.upper() == p and len(p) > 1:
            # ALL CAPS -> Title Case
            titled.append(p.capitalize())
        elif p.lower() == p and len(p) > 1:
            # all lower -> Title Case
            titled.append(p.capitalize())
        else:
            titled.append(p)
    return " ".join(titled)


def extract_suffix(name_str):
    """Extract suffix (Jr, Sr, II, III, IV, V) from name. Returns (cleaned_name, suffix)."""
    if not name_str:
        return name_str, None
    m = SUFFIX_PATTERN.search(name_str)
    if m:
        suffix = m.group(1).rstrip(".")
        # Normalize suffix
        suffix_map = {
            "jr": "Jr", "sr": "Sr", "ii": "II", "iii": "III", "iv": "IV", "v": "V",
            "2nd": "II", "3rd": "III", "4th": "IV",
        }
        suffix = suffix_map.get(suffix.lower(), suffix)
        cleaned = name_str[:m.start()].rstrip()
        return cleaned, suffix
    return name_str, None


def normalize_place_for_export(place_str):
    """Normalize a place string: expand state abbrevs, normalize country, add County suffix."""
    if not place_str:
        return place_str, False

    original = place_str
    parts = [p.strip() for p in place_str.split(",")]
    parts = [p for p in parts if p]

    changed = False

    # Remove empty parts and double commas
    new_parts = []
    for p in parts:
        stripped = p.strip()
        if stripped:
            new_parts.append(stripped)
    parts = new_parts

    # Normalize country (last element)
    if parts:
        last_lower = parts[-1].strip().lower()
        if last_lower in COUNTRY_NORMALIZE:
            parts[-1] = COUNTRY_NORMALIZE[last_lower]
            changed = True

    # Find and expand state abbreviations
    for i, part in enumerate(parts):
        stripped = part.strip()
        if stripped.upper() in US_STATE_ABBREVS and len(stripped) == 2:
            parts[i] = US_STATE_ABBREVS[stripped.upper()]
            changed = True

    # Detect county names without "County" suffix
    # Heuristic: in a 4-part US address (City, County, State, Country),
    # the second element is typically a county
    if len(parts) == 4 and parts[-1] == "USA":
        county_part = parts[1].strip()
        if (county_part
                and not county_part.lower().endswith("county")
                and not county_part.lower().endswith("co.")
                and county_part.upper() not in US_STATE_ABBREVS
                and county_part.upper() not in US_STATE_NAMES):
            # Check it's not actually a state name
            if county_part not in US_STATE_ABBREVS.values():
                parts[1] = f"{county_part} County"
                changed = True

    # Handle "Co." -> "County"
    for i, part in enumerate(parts):
        if part.strip().endswith(" Co."):
            parts[i] = part.strip()[:-4] + " County"
            changed = True

    result = ", ".join(parts)
    return result, changed


def normalize_date_for_gedcom(raw_date):
    """Convert a date string to GEDCOM 5.5.1 format. Returns (gedcom_date, was_fixed)."""
    if not raw_date:
        return None, False

    original = raw_date.strip()

    # Skip "DECEASED"
    if original.upper() == "DECEASED":
        return None, True

    # Extract qualifier
    qualifier = None
    working = original
    qualifier_match = re.match(
        r"^(abt\.?|about|circa|ca\.?|bef\.?|before|aft\.?|after|bet\.?|between|est\.?|cal\.?|from|to)\s+",
        working, re.IGNORECASE,
    )
    if qualifier_match:
        raw_q = qualifier_match.group(1).lower().rstrip(".")
        # Map to standard including the dot-versions
        for key, val in QUALIFIER_MAP.items():
            if raw_q == key.rstrip("."):
                qualifier = val
                break
        if not qualifier:
            qualifier = QUALIFIER_MAP.get(raw_q, raw_q.upper())
        working = working[qualifier_match.end():]

    # Handle "bet. YYYY-YYYY" or "between YYYY and YYYY"
    bet_match = re.match(r"^(\d{4})\s*[-–]\s*(\d{4})$", working)
    if bet_match:
        q = qualifier if qualifier else "BET"
        result = f"{q} {bet_match.group(1)} AND {bet_match.group(2)}"
        return result, result != original

    bet_and = re.match(r"^(\d{4})\s+and\s+(\d{4})$", working, re.IGNORECASE)
    if bet_and:
        q = qualifier if qualifier else "BET"
        result = f"{q} {bet_and.group(1)} AND {bet_and.group(2)}"
        return result, result != original

    # Handle weird date: "26/March/1854/1849" -> take first valid date
    weird = re.match(r"^(\d{1,2})/(\w+)/(\d{4})/\d{4}$", working)
    if weird:
        day = int(weird.group(1))
        month_str = weird.group(2).lower()
        year = weird.group(3)
        month = MONTH_ABBREV.get(month_str)
        if month:
            result = f"{day} {month} {year}"
            if qualifier:
                result = f"{qualifier} {result}"
            return result, True

    # "abt 1780s" -> "ABT 1780"
    decade_match = re.match(r"^(\d{4})s$", working)
    if decade_match:
        year = decade_match.group(1)
        result = f"ABT {year}" if not qualifier else f"{qualifier} {year}"
        return result, True

    # Year only: "1792"
    if re.match(r"^\d{4}$", working):
        result = working
        if qualifier:
            result = f"{qualifier} {working}"
        was_fixed = result != original
        return result, was_fixed

    # DD/Month/YYYY: "04/November/1915"
    m = re.match(r"^(\d{1,2})/(\w+)/(\d{4})$", working)
    if m:
        day = int(m.group(1))
        month_str = m.group(2).lower()
        year = m.group(3)
        month = MONTH_ABBREV.get(month_str)
        if month:
            result = f"{day} {month} {year}"
            if qualifier:
                result = f"{qualifier} {result}"
            return result, True

    # MM/DD/YYYY or DD/MM/YYYY
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", working)
    if m:
        a, b, year = int(m.group(1)), int(m.group(2)), m.group(3)
        if a > 12:
            day, month_num = a, b
        else:
            month_num, day = a, b
        if 1 <= month_num <= 12 and 1 <= day <= 31:
            month = MONTH_NUM_TO_ABBREV[month_num]
            result = f"{day} {month} {year}"
            if qualifier:
                result = f"{qualifier} {result}"
            return result, True

    # D Mon YYYY or D Month YYYY (various cases)
    m = re.match(r"^(\d{1,2})\s+(\w+)\s+(\d{4})$", working)
    if m:
        day = int(m.group(1))
        month_str = m.group(2).lower()
        year = m.group(3)
        month = MONTH_ABBREV.get(month_str)
        if month:
            result = f"{day} {month} {year}"
            if qualifier:
                result = f"{qualifier} {result}"
            was_fixed = result != original
            return result, was_fixed

    # Mon YYYY or Month YYYY (like "Dec 1885", "Jun 1823")
    m = re.match(r"^(\w+)\s+(\d{4})$", working)
    if m:
        month_str = m.group(1).lower()
        year = m.group(2)
        month = MONTH_ABBREV.get(month_str)
        if month:
            result = f"{month} {year}"
            if qualifier:
                result = f"{qualifier} {result}"
            was_fixed = result != original
            return result, was_fixed

    # If we get here, just uppercase any month abbreviations we can find
    result = working
    for name, abbrev in MONTH_ABBREV.items():
        pattern = re.compile(r"\b" + re.escape(name) + r"\b", re.IGNORECASE)
        result = pattern.sub(abbrev, result)
    if qualifier:
        result = f"{qualifier} {result}"
    was_fixed = result != original
    return result, was_fixed


def detect_duplicates(individuals):
    """Find candidate duplicate pairs: exact name + same birth year."""
    by_key = defaultdict(list)
    for indi in individuals:
        name = (indi.get("name") or "").strip().lower()
        by = indi.get("birth_year")
        if name and by:
            by_key[(name, by)].append(indi)

    pairs = []
    seen = set()
    for key, group in by_key.items():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                pair_key = tuple(sorted([group[i]["id"], group[j]["id"]]))
                if pair_key not in seen:
                    seen.add(pair_key)
                    pairs.append((group[i], group[j]))
    return pairs


def detect_chronological_issues(individuals):
    """Detect: death before birth, impossible parent ages, lifespan > 110."""
    issues = {}  # indi_id -> list of issue strings

    indi_by_id = {i["id"]: i for i in individuals}

    for indi in individuals:
        indi_issues = []
        by = indi.get("birth_year")
        dy = indi.get("death_year")

        if by and dy:
            if dy < by:
                indi_issues.append(f"CHRONOLOGY: Death year ({dy}) before birth year ({by})")
            elif (dy - by) > 110:
                indi_issues.append(f"CHRONOLOGY: Lifespan exceeds 110 years ({dy - by} years)")

        if indi_issues:
            issues[indi["id"]] = indi_issues

    return issues


def detect_orphans(famc_links, fams_links, individuals):
    """Find individuals with no CHILD_OF and no SPOUSE_IN."""
    orphans = set()
    for indi in individuals:
        indi_id = indi["id"]
        if not famc_links.get(indi_id) and not fams_links.get(indi_id):
            orphans.add(indi_id)
    return orphans


def deduplicate_sources(sources):
    """Deduplicate sources by normalized title (case-insensitive).
    Returns (deduped_sources, remap: old_id -> canonical_id)."""
    title_to_canonical = {}
    remap = {}
    deduped = []

    for src in sources:
        title = (src.get("title") or "").strip()
        title_lower = title.lower()
        if title_lower in title_to_canonical:
            # Map this ID to the canonical source
            remap[src["id"]] = title_to_canonical[title_lower]["id"]
        else:
            cleaned = {
                "id": src["id"],
                "title": title,
                "author": (src.get("author") or "").strip(),
                "publisher": (src.get("publisher") or "").strip(),
            }
            title_to_canonical[title_lower] = cleaned
            deduped.append(cleaned)
            remap[src["id"]] = src["id"]

    return deduped, remap


# ---------------------------------------------------------------------------
# GEDCOM Writer
# ---------------------------------------------------------------------------

def gedcom_line(level, tag, value="", xref=""):
    """Format a single GEDCOM line, splitting with CONC if > 255 chars."""
    if xref:
        line = f"{level} {xref} {tag}"
    else:
        line = f"{level} {tag}"

    if value:
        line = f"{line} {value}"

    lines = []
    if len(line) <= GEDCOM_MAX_LINE:
        lines.append(line)
    else:
        # Split with CONC
        first_part = line[:GEDCOM_MAX_LINE]
        lines.append(first_part)
        remainder = line[GEDCOM_MAX_LINE:]
        conc_level = level + 1
        while remainder:
            chunk = remainder[:GEDCOM_MAX_LINE - len(f"{conc_level} CONC ")]
            lines.append(f"{conc_level} CONC {chunk}")
            remainder = remainder[len(chunk):]

    return lines


def write_gedcom(
    output_path,
    individuals,
    families,
    sources,
    residences,
    famc_links,
    fams_links,
    source_citations,
    source_remap,
    duplicate_notes,
    chrono_issues,
    orphan_ids,
):
    """Write the complete GEDCOM 5.5.1 file."""
    today = datetime.now()
    date_str = f"{today.day} {MONTH_NUM_TO_ABBREV[today.month]} {today.year}"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8-sig") as f:  # UTF-8 BOM
        def w(lines_or_str):
            if isinstance(lines_or_str, list):
                for line in lines_or_str:
                    f.write(line + "\n")
            else:
                f.write(lines_or_str + "\n")

        # HEAD
        w("0 HEAD")
        w("1 SOUR RootsGraph")
        w("2 VERS 1.0")
        w("2 NAME Roots Graph")
        w("1 DEST ANSTFILE")
        w(f"1 DATE {date_str}")
        w("1 FILE clean-tree.ged")
        w("1 GEDC")
        w("2 VERS 5.5.1")
        w("2 FORM LINEAGE-LINKED")
        w("1 CHAR UTF-8")
        w("1 SUBM @SUBM1@")

        # SUBM
        w("0 @SUBM1@ SUBM")
        w("1 NAME Roots Graph Export")

        # INDIVIDUALS
        for indi in individuals:
            indi_id = indi["id"]
            w(f"0 {indi_id} INDI")

            given = indi.get("_clean_given") or ""
            surname = indi.get("_clean_surname") or ""
            suffix = indi.get("_suffix")

            # NAME tag
            name_str = f"{given} /{surname}/"
            if suffix:
                name_str = f"{name_str} {suffix}"
            w(gedcom_line(1, "NAME", name_str))

            if given:
                w(gedcom_line(2, "GIVN", given))
            if surname:
                w(gedcom_line(2, "SURN", surname))
            if suffix:
                w(gedcom_line(2, "NSFX", suffix))

            # SEX
            sex = indi.get("sex")
            if sex and sex in ("M", "F"):
                w(f"1 SEX {sex}")
            else:
                w("1 SEX U")

            # BIRT
            birth_date = indi.get("_ged_birth_date")
            birth_place = indi.get("_clean_birth_place")
            if birth_date or birth_place:
                w("1 BIRT")
                if birth_date:
                    w(gedcom_line(2, "DATE", birth_date))
                if birth_place:
                    w(gedcom_line(2, "PLAC", birth_place))

            # DEAT
            death_date = indi.get("_ged_death_date")
            death_place = indi.get("_clean_death_place")
            if death_date or death_place:
                w("1 DEAT")
                if death_date:
                    w(gedcom_line(2, "DATE", death_date))
                if death_place:
                    w(gedcom_line(2, "PLAC", death_place))

            # BURI
            burial_place = indi.get("_clean_burial_place")
            if burial_place:
                w("1 BURI")
                w(gedcom_line(2, "PLAC", burial_place))

            # RESI
            for res in residences.get(indi_id, []):
                res_place = res.get("_clean_place")
                res_date = res.get("_ged_date")
                res_year = res.get("year")
                if res_place or res_date or res_year:
                    w("1 RESI")
                    if res_date:
                        w(gedcom_line(2, "DATE", res_date))
                    elif res_year:
                        w(gedcom_line(2, "DATE", str(res_year)))
                    if res_place:
                        w(gedcom_line(2, "PLAC", res_place))

            # FAMC
            for fam_id in famc_links.get(indi_id, []):
                w(f"1 FAMC {fam_id}")

            # FAMS
            for fam_id in fams_links.get(indi_id, []):
                w(f"1 FAMS {fam_id}")

            # SOUR citations
            cited_ids = set()
            for src_id in source_citations.get(indi_id, []):
                canonical_id = source_remap.get(src_id, src_id)
                if canonical_id not in cited_ids:
                    cited_ids.add(canonical_id)
                    w(f"1 SOUR {canonical_id}")

            # NOTE tags (flags)
            notes = []
            if indi_id in duplicate_notes:
                for note in duplicate_notes[indi_id]:
                    notes.append(note)
            if indi_id in chrono_issues:
                for issue in chrono_issues[indi_id]:
                    notes.append(issue)
            if indi_id in orphan_ids:
                notes.append("ORPHAN: no family connections")

            for note in notes:
                w(gedcom_line(1, "NOTE", note))

        # FAMILIES
        for fam_id, fam in sorted(families.items()):
            w(f"0 {fam_id} FAM")

            if fam.get("husband_id"):
                w(f"1 HUSB {fam['husband_id']}")
            if fam.get("wife_id"):
                w(f"1 WIFE {fam['wife_id']}")

            for child_id in fam.get("children", []):
                w(f"1 CHIL {child_id}")

            marr_date = fam.get("_ged_marriage_date")
            marr_place = fam.get("_clean_marriage_place")
            if marr_date or marr_place:
                w("1 MARR")
                if marr_date:
                    w(gedcom_line(2, "DATE", marr_date))
                if marr_place:
                    w(gedcom_line(2, "PLAC", marr_place))

        # SOURCES
        for src in sources:
            w(f"0 {src['id']} SOUR")
            if src.get("title"):
                w(gedcom_line(1, "TITL", src["title"]))
            if src.get("author"):
                w(gedcom_line(1, "AUTH", src["author"]))
            if src.get("publisher"):
                w(gedcom_line(1, "PUBL", src["publisher"]))

        # TRLR
        w("0 TRLR")


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def main():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    pw = os.getenv("NEO4J_PASSWORD", "changeme")

    print(f"Connecting to Neo4j at {uri}...")
    driver = GraphDatabase.driver(uri, auth=(user, pw))

    # -----------------------------------------------------------------------
    # Step 1: Extract all data (READ-ONLY)
    # -----------------------------------------------------------------------
    print("\n=== Step 1: Extracting data from Neo4j (read-only) ===")

    with driver.session() as session:
        individuals = extract_individuals(session)
        print(f"  Individuals: {len(individuals)}")

        residences = extract_residences(session)
        res_count = sum(len(v) for v in residences.values())
        print(f"  Residences: {res_count}")

        families = extract_families(session)
        print(f"  Families: {len(families)}")

        famc_links, fams_links = extract_family_links(session)
        print(f"  Child-of links: {sum(len(v) for v in famc_links.values())}")
        print(f"  Spouse-in links: {sum(len(v) for v in fams_links.values())}")

        sources_raw = extract_sources(session)
        print(f"  Sources: {len(sources_raw)}")

        source_citations = extract_source_citations(session)
        print(f"  Source citations: {sum(len(v) for v in source_citations.values())}")

    driver.close()

    # -----------------------------------------------------------------------
    # Step 2: In-memory transforms
    # -----------------------------------------------------------------------
    print("\n=== Step 2: In-memory cleanup transforms ===")

    # --- Name cleanup ---
    print("  Cleaning names...")
    for indi in individuals:
        given_raw = indi.get("given_name") or ""
        surname_raw = indi.get("surname") or ""
        name_raw = indi.get("name") or ""

        # Clean given name
        given_clean = clean_name(given_raw)
        given_clean, suffix_g = extract_suffix(given_clean)

        # Clean surname
        surname_clean = clean_name(surname_raw)
        surname_clean, suffix_s = extract_suffix(surname_clean)

        # Also check full name for suffix
        _, suffix_n = extract_suffix(name_raw)

        suffix = suffix_g or suffix_s or suffix_n

        # If given_name is empty, try to derive from name
        if not given_clean and name_raw:
            name_parts = name_raw.replace("/", "").strip().split()
            if surname_clean:
                # Remove surname from name parts
                given_parts = [p for p in name_parts if p.lower() != surname_clean.lower()]
                given_clean = clean_name(" ".join(given_parts))
                given_clean, extra_suffix = extract_suffix(given_clean)
                if not suffix:
                    suffix = extra_suffix
            else:
                given_clean = clean_name(name_raw)
                given_clean, extra_suffix = extract_suffix(given_clean)
                if not suffix:
                    suffix = extra_suffix

        original_given = indi.get("given_name") or ""
        original_surname = indi.get("surname") or ""
        if given_clean != original_given or surname_clean != original_surname:
            stats["names_cleaned"] += 1

        indi["_clean_given"] = given_clean
        indi["_clean_surname"] = surname_clean
        indi["_suffix"] = suffix

    print(f"    Names cleaned: {stats['names_cleaned']}")

    # --- Place standardization ---
    print("  Standardizing places...")
    for indi in individuals:
        for field_in, field_out in [
            ("birth_place", "_clean_birth_place"),
            ("death_place", "_clean_death_place"),
            ("burial_place", "_clean_burial_place"),
        ]:
            raw = indi.get(field_in)
            if raw:
                cleaned, changed = normalize_place_for_export(raw)
                indi[field_out] = cleaned
                if changed:
                    stats["places_normalized"] += 1
            else:
                indi[field_out] = None

    # Normalize residence places
    for indi_id, res_list in residences.items():
        for res in res_list:
            raw = res.get("place")
            if raw:
                cleaned, changed = normalize_place_for_export(raw)
                res["_clean_place"] = cleaned
                if changed:
                    stats["places_normalized"] += 1
            else:
                res["_clean_place"] = None

    # Normalize family marriage places
    for fam in families.values():
        raw = fam.get("marriage_place")
        if raw:
            cleaned, changed = normalize_place_for_export(raw)
            fam["_clean_marriage_place"] = cleaned
            if changed:
                stats["places_normalized"] += 1
        else:
            fam["_clean_marriage_place"] = None

    print(f"    Places normalized: {stats['places_normalized']}")

    # --- Date standardization ---
    print("  Standardizing dates...")
    for indi in individuals:
        bd_raw = indi.get("birth_date_raw")
        if bd_raw:
            ged_date, fixed = normalize_date_for_gedcom(bd_raw)
            indi["_ged_birth_date"] = ged_date
            if fixed:
                stats["dates_fixed"] += 1
        else:
            indi["_ged_birth_date"] = None

        dd_raw = indi.get("death_date_raw")
        if dd_raw:
            ged_date, fixed = normalize_date_for_gedcom(dd_raw)
            indi["_ged_death_date"] = ged_date
            if fixed:
                stats["dates_fixed"] += 1
        else:
            indi["_ged_death_date"] = None

    # Normalize residence dates
    for indi_id, res_list in residences.items():
        for res in res_list:
            raw = res.get("date_raw")
            if raw:
                ged_date, fixed = normalize_date_for_gedcom(raw)
                res["_ged_date"] = ged_date
                if fixed:
                    stats["dates_fixed"] += 1
            else:
                res["_ged_date"] = None

    # Normalize family marriage dates
    for fam in families.values():
        raw = fam.get("marriage_date_raw")
        if raw:
            ged_date, fixed = normalize_date_for_gedcom(raw)
            fam["_ged_marriage_date"] = ged_date
            if fixed:
                stats["dates_fixed"] += 1
        else:
            fam["_ged_marriage_date"] = None

    print(f"    Dates fixed: {stats['dates_fixed']}")

    # --- Dedup detection ---
    print("  Detecting duplicates...")
    dup_pairs = detect_duplicates(individuals)
    duplicate_notes = defaultdict(list)

    for a, b in dup_pairs:
        duplicate_notes[a["id"]].append(f"POSSIBLE DUPLICATE: see {b['id']}")
        duplicate_notes[b["id"]].append(f"POSSIBLE DUPLICATE: see {a['id']}")
        stats["duplicate_flags"] += 1

    # Write dedup CSV
    dedup_path = os.path.abspath(DEDUP_CSV)
    os.makedirs(os.path.dirname(dedup_path), exist_ok=True)
    with open(dedup_path, "w", newline="", encoding="utf-8") as csvf:
        writer = csv.writer(csvf)
        writer.writerow(["id_a", "name_a", "birth_year_a", "id_b", "name_b", "birth_year_b"])
        for a, b in dup_pairs:
            writer.writerow([
                a["id"], a.get("name", ""), a.get("birth_year", ""),
                b["id"], b.get("name", ""), b.get("birth_year", ""),
            ])

    print(f"    Duplicate pairs found: {len(dup_pairs)} (flags: {stats['duplicate_flags']})")
    print(f"    Dedup candidates written to: {dedup_path}")

    # --- Orphan detection ---
    print("  Detecting orphans...")
    orphan_ids = detect_orphans(famc_links, fams_links, individuals)
    stats["orphan_flags"] = len(orphan_ids)
    print(f"    Orphans found: {stats['orphan_flags']}")

    # --- Chronological issues ---
    print("  Checking chronological issues...")
    chrono_issues = detect_chronological_issues(individuals)
    stats["chrono_flags"] = sum(len(v) for v in chrono_issues.values())
    print(f"    Chronological issues: {stats['chrono_flags']}")

    # --- Source dedup ---
    print("  Deduplicating sources...")
    sources_deduped, source_remap = deduplicate_sources(sources_raw)
    remapped_count = len(sources_raw) - len(sources_deduped)
    print(f"    Sources deduped: {len(sources_raw)} -> {len(sources_deduped)} ({remapped_count} merged)")

    # -----------------------------------------------------------------------
    # Step 3: Write GEDCOM
    # -----------------------------------------------------------------------
    output_path = os.path.abspath(OUTPUT_GED)
    print(f"\n=== Step 3: Writing GEDCOM 5.5.1 ===")
    print(f"  Output: {output_path}")

    write_gedcom(
        output_path=output_path,
        individuals=individuals,
        families=families,
        sources=sources_deduped,
        residences=residences,
        famc_links=famc_links,
        fams_links=fams_links,
        source_citations=source_citations,
        source_remap=source_remap,
        duplicate_notes=duplicate_notes,
        chrono_issues=chrono_issues,
        orphan_ids=orphan_ids,
    )

    # -----------------------------------------------------------------------
    # Step 4: Validation summary
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("EXPORT SUMMARY")
    print("=" * 60)
    print(f"  Total individuals exported:    {len(individuals)}")
    print(f"  Total families exported:       {len(families)}")
    print(f"  Total sources exported:        {len(sources_deduped)}")
    print(f"  Duplicate flags added:         {stats['duplicate_flags']}")
    print(f"  Chronological flags added:     {stats['chrono_flags']}")
    print(f"  Orphan flags added:            {stats['orphan_flags']}")
    print(f"  Place names normalized:        {stats['places_normalized']}")
    print(f"  Names cleaned up:              {stats['names_cleaned']}")
    print(f"  Dates fixed:                   {stats['dates_fixed']}")
    print("=" * 60)
    print(f"  Output file: {output_path}")
    print(f"  Dedup CSV:   {dedup_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
