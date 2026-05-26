"""
Standardize all date fields in Neo4j to consistent format.

Target format: "D Mon YYYY" (e.g. "16 Aug 1968")
- Full month names → 3-letter abbreviations
- Leading zero days stripped (06 → 6)
- MM/DD/YYYY converted to D Mon YYYY
- DD/Month/YYYY converted to D Mon YYYY
- Uppercase months → title case (JUN → Jun)
- Qualifiers preserved (abt, Bef., Aft, between)
- Year-only values left as-is
- Also updates birth_date_iso/death_date_iso where parseable

Usage:
    python -m scripts.standardize_dates
"""

import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

MONTH_MAP = {
    "january": "Jan", "february": "Feb", "march": "Mar",
    "april": "Apr", "may": "May", "june": "Jun",
    "july": "Jul", "august": "Aug", "september": "Sep",
    "october": "Oct", "november": "Nov", "december": "Dec",
    "jan": "Jan", "feb": "Feb", "mar": "Mar",
    "apr": "Apr", "jun": "Jun", "jul": "Jul",
    "aug": "Aug", "sep": "Sep", "oct": "Oct",
    "nov": "Nov", "dec": "Dec",
}

MONTH_NUM = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

MONTH_FROM_NUM = {v: k for k, v in MONTH_NUM.items()}


def normalize_month(m: str) -> str | None:
    """Convert any month string to 3-letter abbreviation."""
    return MONTH_MAP.get(m.lower())


def standardize_date(raw: str) -> tuple[str, str | None]:
    """
    Returns (standardized_raw, iso_date_or_none).
    """
    if not raw or not raw.strip():
        return raw, None

    original = raw.strip()

    # Year only: "1792"
    if re.match(r"^\d{4}$", original):
        return original, f"{original}-01-01"

    # "abt YYYY" / "about YYYY"
    m = re.match(r"^(abt\.?|about)\s+(\d{4})$", original, re.I)
    if m:
        year = m.group(2)
        return f"abt {year}", f"{year}-01-01"

    # "DD/Month/YYYY" e.g. "04/November/1915"
    m = re.match(r"^(\d{1,2})/(\w+)/(\d{4})$", original)
    if m:
        day = int(m.group(1))
        month = normalize_month(m.group(2))
        year = m.group(3)
        if month:
            iso = f"{year}-{MONTH_NUM[month]:02d}-{day:02d}"
            return f"{day} {month} {year}", iso

    # MM/DD/YYYY e.g. "11/17/1969" or DD/MM/YYYY "28/11/1985"
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", original)
    if m:
        a, b, year = int(m.group(1)), int(m.group(2)), m.group(3)
        # If first number > 12, it's DD/MM/YYYY
        if a > 12:
            day, month_num = a, b
        else:
            # Assume MM/DD/YYYY (US format)
            month_num, day = a, b
        if 1 <= month_num <= 12 and 1 <= day <= 31:
            month = MONTH_FROM_NUM[month_num]
            iso = f"{year}-{month_num:02d}-{day:02d}"
            return f"{day} {month} {year}", iso

    # "D Month YYYY" or "DD Mon YYYY" (full or abbreviated month)
    m = re.match(r"^(\d{1,2})\s+(\w+)\s+(\d{4})$", original)
    if m:
        day = int(m.group(1))
        month = normalize_month(m.group(2))
        year = m.group(3)
        if month:
            iso = f"{year}-{MONTH_NUM[month]:02d}-{day:02d}"
            return f"{day} {month} {year}", iso

    # "Mon YYYY" or "Month YYYY"
    m = re.match(r"^(\w+)\s+(\d{4})$", original)
    if m:
        month = normalize_month(m.group(1))
        year = m.group(2)
        if month:
            iso = f"{year}-{MONTH_NUM[month]:02d}-01"
            return f"{month} {year}", iso

    # Qualified dates: "Bef. D Mon YYYY", "Aft D Mon YYYY", "After YYYY"
    m = re.match(r"^(Bef\.?|Before|Aft\.?|After)\s+(.+)$", original, re.I)
    if m:
        qualifier = m.group(1).rstrip(".")
        # Normalize qualifier
        if qualifier.lower() in ("bef", "before"):
            qualifier = "Bef."
        elif qualifier.lower() in ("aft", "after"):
            qualifier = "Aft."
        inner, iso = standardize_date(m.group(2))
        return f"{qualifier} {inner}", iso

    # "between YYYY and YYYY"
    m = re.match(r"^between\s+(\d{4})\s+and\s+(\d{4})$", original, re.I)
    if m:
        return f"bet. {m.group(1)}-{m.group(2)}", f"{m.group(1)}-01-01"

    # Can't parse — return as-is
    return original, None


def main():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    pw = os.getenv("NEO4J_PASSWORD", "changeme")

    driver = GraphDatabase.driver(uri, auth=(user, pw))

    # Fetch all individuals with dates
    with driver.session() as session:
        result = session.run("""
            MATCH (i:Individual)
            WHERE i.birth_date_raw IS NOT NULL OR i.death_date_raw IS NOT NULL
            RETURN i.id AS id, i.birth_date_raw AS bd, i.death_date_raw AS dd
        """)
        records = [(r["id"], r["bd"], r["dd"]) for r in result]

    print(f"Found {len(records)} individuals with dates")

    changed = 0
    for indi_id, bd, dd in records:
        updates = {}

        if bd:
            new_bd, bd_iso = standardize_date(bd)
            if new_bd != bd:
                updates["birth_date_raw"] = new_bd
            if bd_iso:
                updates["birth_date_iso"] = bd_iso

        if dd:
            new_dd, dd_iso = standardize_date(dd)
            if new_dd != dd:
                updates["death_date_raw"] = new_dd
            if dd_iso:
                updates["death_date_iso"] = dd_iso

        if updates:
            set_clauses = ", ".join(f"i.{k} = ${k}" for k in updates)
            with driver.session() as session:
                session.execute_write(
                    lambda tx, q=f"MATCH (i:Individual {{id: $id}}) SET {set_clauses}",
                           p={**updates, "id": indi_id}: tx.run(q, **p).consume()
                )
            changed += 1

    driver.close()
    print(f"Updated {changed} individuals")

    # Show summary of what was changed
    print("\nSample standardizations:")
    count = 0
    for indi_id, bd, dd in records:
        if bd:
            new_bd, _ = standardize_date(bd)
            if new_bd != bd:
                print(f"  birth: {bd!r:35s} → {new_bd!r}")
                count += 1
        if dd:
            new_dd, _ = standardize_date(dd)
            if new_dd != dd:
                print(f"  death: {dd!r:35s} → {new_dd!r}")
                count += 1
        if count >= 20:
            print("  ...")
            break


if __name__ == "__main__":
    main()
