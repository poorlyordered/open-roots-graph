"""
Comprehensive data audit for the genealogy Neo4j database.

Phase 1 of GEDCOM export cleanup — READ ONLY, no writes.
Checks for duplicates, orphans, place variations, missing fields,
source quality, relationship integrity, chronological issues, and name issues.

Outputs a clear report to stdout and saves JSON to data/audit_report.json.

Usage:
    python -m scripts.audit_data
"""

import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
REPORT_PATH = os.path.join(REPORT_DIR, "audit_report.json")


def run_query(session, query, **params):
    result = session.run(query, **params)
    return [dict(r) for r in result]


def section(title):
    width = 70
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}")


def subsection(title):
    print(f"\n  --- {title} ---")


def main():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    pw = os.getenv("NEO4J_PASSWORD", "changeme")

    driver = GraphDatabase.driver(uri, auth=(user, pw))
    report = {}

    with driver.session() as s:
        # =============================================================
        # 9. OVERALL STATS (run first for context)
        # =============================================================
        section("9. OVERALL STATS")
        stats = {}

        row = run_query(s, """
            MATCH (i:Individual) WITH count(i) AS c RETURN c
        """)
        stats["total_individuals"] = row[0]["c"] if row else 0

        row = run_query(s, "MATCH (f:Family) RETURN count(f) AS c")
        stats["total_families"] = row[0]["c"] if row else 0

        row = run_query(s, "MATCH (p:Place) RETURN count(p) AS c")
        stats["total_places"] = row[0]["c"] if row else 0

        row = run_query(s, "MATCH (src:Source) RETURN count(src) AS c")
        stats["total_sources"] = row[0]["c"] if row else 0

        row = run_query(s, "MATCH (p:Place) WHERE p.latitude IS NOT NULL RETURN count(p) AS c")
        stats["geocoded_places"] = row[0]["c"] if row else 0

        # Date format check — non-standardized dates
        date_rows = run_query(s, """
            MATCH (i:Individual)
            WHERE i.birth_date_raw IS NOT NULL OR i.death_date_raw IS NOT NULL
            RETURN i.id AS id, i.name AS name,
                   i.birth_date_raw AS bd, i.death_date_raw AS dd
        """)
        std_pattern = re.compile(
            r"^(abt |Bef\. |Aft\. |bet\. )?"
            r"(\d{1,2} (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) )?\d{4}"
            r"(-\d{4})?$"
        )
        non_std = []
        for r in date_rows:
            for field, val in [("birth_date_raw", r["bd"]), ("death_date_raw", r["dd"])]:
                if val and not std_pattern.match(val):
                    non_std.append({"id": r["id"], "name": r["name"], "field": field, "value": val})
        stats["non_standardized_dates"] = len(non_std)
        stats["non_standardized_date_samples"] = non_std[:20]

        for k, v in stats.items():
            if k == "non_standardized_date_samples":
                continue
            print(f"  {k}: {v}")
        if non_std:
            print(f"\n  Non-standardized date samples ({len(non_std)} total):")
            for d in non_std[:15]:
                print(f"    {d['name']:40s} {d['field']}: {d['value']}")
            if len(non_std) > 15:
                print(f"    ... and {len(non_std) - 15} more")

        report["overall_stats"] = stats

        # =============================================================
        # 1. POTENTIAL DUPLICATE INDIVIDUALS
        # =============================================================
        section("1. POTENTIAL DUPLICATE INDIVIDUALS")

        # Exact: same name + same birth year
        exact_dupes = run_query(s, """
            MATCH (a:Individual), (b:Individual)
            WHERE a.id < b.id
              AND a.name IS NOT NULL AND b.name IS NOT NULL
              AND a.name = b.name
              AND a.birth_year IS NOT NULL AND b.birth_year IS NOT NULL
              AND a.birth_year = b.birth_year
            RETURN a.id AS id_a, a.name AS name_a, a.birth_year AS by_a,
                   b.id AS id_b, b.name AS name_b, b.birth_year AS by_b
            ORDER BY a.name
        """)
        subsection(f"Exact name + same birth year: {len(exact_dupes)} pairs")
        for d in exact_dupes:
            print(f"    {d['name_a']} (b.{d['by_a']})  [{d['id_a']}] vs [{d['id_b']}]")
        report["duplicate_exact"] = exact_dupes

        # Fuzzy: same surname + given starts same 3 chars + birth year within 3
        fuzzy_dupes = run_query(s, """
            MATCH (a:Individual), (b:Individual)
            WHERE a.id < b.id
              AND a.surname IS NOT NULL AND b.surname IS NOT NULL
              AND a.surname = b.surname
              AND a.given_name IS NOT NULL AND b.given_name IS NOT NULL
              AND size(a.given_name) >= 3 AND size(b.given_name) >= 3
              AND left(toLower(a.given_name), 3) = left(toLower(b.given_name), 3)
              AND a.birth_year IS NOT NULL AND b.birth_year IS NOT NULL
              AND abs(a.birth_year - b.birth_year) <= 3
              AND NOT (a.name = b.name AND a.birth_year = b.birth_year)
            RETURN a.id AS id_a, a.name AS name_a, a.birth_year AS by_a,
                   b.id AS id_b, b.name AS name_b, b.birth_year AS by_b
            ORDER BY a.surname, a.given_name
        """)
        subsection(f"Fuzzy matches (surname + 3-char given + birth +/- 3yr): {len(fuzzy_dupes)} pairs")
        for d in fuzzy_dupes[:30]:
            print(f"    {d['name_a']} (b.{d['by_a']}) vs {d['name_b']} (b.{d['by_b']})")
        if len(fuzzy_dupes) > 30:
            print(f"    ... and {len(fuzzy_dupes) - 30} more")
        report["duplicate_fuzzy"] = fuzzy_dupes

        # =============================================================
        # 2. ORPHANED INDIVIDUALS
        # =============================================================
        section("2. ORPHANED INDIVIDUALS")

        orphans = run_query(s, """
            MATCH (i:Individual)
            WHERE NOT (i)-[:CHILD_OF]->(:Family)
              AND NOT (i)-[:SPOUSE_IN]->(:Family)
            RETURN i.id AS id, i.name AS name, i.birth_year AS birth_year
            ORDER BY i.name
        """)
        print(f"  Individuals with no CHILD_OF and no SPOUSE_IN: {len(orphans)}")
        for o in orphans[:30]:
            yr = f" (b.{o['birth_year']})" if o["birth_year"] else ""
            print(f"    {o['name']}{yr}  [{o['id']}]")
        if len(orphans) > 30:
            print(f"    ... and {len(orphans) - 30} more")
        report["orphaned_individuals"] = orphans

        # =============================================================
        # 3. PLACE NAME VARIATIONS
        # =============================================================
        section("3. PLACE NAME VARIATIONS")

        # State values and counts
        state_rows = run_query(s, """
            MATCH (p:Place)
            WHERE p.state IS NOT NULL
            RETURN p.state AS state, count(*) AS count
            ORDER BY count DESC
        """)
        subsection(f"Distinct state values: {len(state_rows)}")
        for r in state_rows:
            print(f"    {r['state']:30s} ({r['count']})")

        # Look for abbreviation issues
        state_names = [r["state"] for r in state_rows]
        abbrev_suspects = [st for st in state_names if len(st) <= 3 or st.isupper()]
        if abbrev_suspects:
            print(f"\n  Possible abbreviations (check for duplicates): {abbrev_suspects}")

        report["place_state_distribution"] = state_rows

        # Places missing state or country
        missing_state = run_query(s, """
            MATCH (p:Place)
            WHERE p.state IS NULL
            RETURN p.normalized AS normalized, p.city AS city,
                   p.county AS county, p.country AS country
            ORDER BY p.normalized
        """)
        subsection(f"Places missing state: {len(missing_state)}")
        for r in missing_state[:20]:
            print(f"    {r['normalized']}")
        if len(missing_state) > 20:
            print(f"    ... and {len(missing_state) - 20} more")
        report["places_missing_state"] = missing_state

        missing_country = run_query(s, """
            MATCH (p:Place)
            WHERE p.country IS NULL
            RETURN p.normalized AS normalized, p.state AS state
            ORDER BY p.normalized
        """)
        subsection(f"Places missing country: {len(missing_country)}")
        for r in missing_country[:20]:
            print(f"    {r['normalized']}  (state: {r['state']})")
        if len(missing_country) > 20:
            print(f"    ... and {len(missing_country) - 20} more")
        report["places_missing_country"] = missing_country

        # Normalized field inconsistencies — look for near-duplicates
        all_places = run_query(s, """
            MATCH (p:Place)
            RETURN p.normalized AS normalized, p.city AS city,
                   p.state AS state, p.country AS country
            ORDER BY p.normalized
        """)
        # Group by stripped/lower for near-dupe detection
        norm_groups = {}
        for p in all_places:
            key = re.sub(r"[^a-z0-9]", "", (p["normalized"] or "").lower())
            norm_groups.setdefault(key, []).append(p["normalized"])
        norm_dupes = {k: v for k, v in norm_groups.items() if len(v) > 1}
        subsection(f"Possible normalized-field near-duplicates: {len(norm_dupes)} groups")
        for k, vals in list(norm_dupes.items())[:15]:
            print(f"    {vals}")
        report["place_normalized_near_dupes"] = {k: v for k, v in norm_dupes.items()}

        # =============================================================
        # 4. EMPTY/NULL FIELD ANALYSIS
        # =============================================================
        section("4. EMPTY/NULL FIELD ANALYSIS")

        fields_to_check = [
            "given_name", "surname", "sex", "birth_year", "death_year",
            "birth_date_raw", "death_date_raw",
        ]
        missing_counts = {}
        for field in fields_to_check:
            row = run_query(s, f"""
                MATCH (i:Individual)
                WHERE i.{field} IS NULL OR i.{field} = ''
                RETURN count(i) AS c
            """)
            missing_counts[field] = row[0]["c"] if row else 0

        subsection("Missing field counts")
        for field, count in missing_counts.items():
            pct = (count / stats["total_individuals"] * 100) if stats["total_individuals"] else 0
            print(f"    {field:20s}: {count:5d}  ({pct:.1f}%)")

        report["missing_field_counts"] = missing_counts

        # Individuals with name = "Unknown" or empty/null
        unknown_names = run_query(s, """
            MATCH (i:Individual)
            WHERE i.name IS NULL OR i.name = '' OR i.name = 'Unknown'
               OR i.name =~ '(?i)^unknown.*'
            RETURN i.id AS id, i.name AS name, i.surname AS surname,
                   i.birth_year AS birth_year
            ORDER BY i.name
        """)
        subsection(f"Individuals with Unknown/empty name: {len(unknown_names)}")
        for r in unknown_names[:20]:
            print(f"    [{r['id']}] name={r['name']!r}  surname={r['surname']!r}  b.{r['birth_year']}")
        report["unknown_names"] = unknown_names

        # =============================================================
        # 5. SOURCE CITATION QUALITY
        # =============================================================
        section("5. SOURCE CITATION QUALITY")

        # Unsourced individuals
        row = run_query(s, """
            MATCH (i:Individual)
            WHERE NOT (i)-[:CITED_IN]->(:Source)
            RETURN count(i) AS c
        """)
        unsourced_count = row[0]["c"] if row else 0
        pct = (unsourced_count / stats["total_individuals"] * 100) if stats["total_individuals"] else 0
        print(f"  Unsourced individuals (no CITED_IN): {unsourced_count}  ({pct:.1f}%)")
        report["unsourced_individuals_count"] = unsourced_count

        # Sources with empty/null titles
        empty_sources = run_query(s, """
            MATCH (src:Source)
            WHERE src.title IS NULL OR src.title = ''
            RETURN src.id AS id, src.author AS author
        """)
        print(f"  Sources with empty/null title: {len(empty_sources)}")
        for r in empty_sources[:10]:
            print(f"    [{r['id']}] author={r['author']!r}")
        report["empty_title_sources"] = empty_sources

        # Duplicate source titles
        dup_sources = run_query(s, """
            MATCH (src:Source)
            WHERE src.title IS NOT NULL AND src.title <> ''
            WITH src.title AS title, collect(src.id) AS ids, count(*) AS cnt
            WHERE cnt > 1
            RETURN title, ids, cnt
            ORDER BY cnt DESC
        """)
        print(f"  Duplicate source titles: {len(dup_sources)} groups")
        for r in dup_sources[:10]:
            print(f"    \"{r['title']}\"  ({r['cnt']}x)  ids: {r['ids']}")
        report["duplicate_source_titles"] = dup_sources

        # Citation distribution
        citation_dist = run_query(s, """
            MATCH (i:Individual)
            OPTIONAL MATCH (i)-[:CITED_IN]->(src:Source)
            WITH i, count(src) AS src_count
            RETURN
              CASE
                WHEN src_count = 0 THEN '0'
                WHEN src_count = 1 THEN '1'
                WHEN src_count = 2 THEN '2'
                ELSE '3+'
              END AS bucket,
              count(i) AS count
            ORDER BY bucket
        """)
        subsection("Source citation distribution")
        for r in citation_dist:
            print(f"    {r['bucket']:5s} sources: {r['count']} individuals")
        report["citation_distribution"] = citation_dist

        # =============================================================
        # 6. RELATIONSHIP INTEGRITY
        # =============================================================
        section("6. RELATIONSHIP INTEGRITY")

        # Empty families (no spouses AND no children)
        empty_fams = run_query(s, """
            MATCH (f:Family)
            WHERE NOT (:Individual)-[:SPOUSE_IN]->(f)
              AND NOT (:Individual)-[:CHILD_OF]->(f)
            RETURN f.id AS id
        """)
        print(f"  Empty families (no spouses, no children): {len(empty_fams)}")
        for r in empty_fams[:10]:
            print(f"    [{r['id']}]")
        report["empty_families"] = empty_fams

        # Individuals who are CHILD_OF more than one family
        multi_child = run_query(s, """
            MATCH (i:Individual)-[:CHILD_OF]->(f:Family)
            WITH i, count(f) AS fam_count, collect(f.id) AS fam_ids
            WHERE fam_count > 1
            RETURN i.id AS id, i.name AS name, fam_count, fam_ids
            ORDER BY fam_count DESC
        """)
        print(f"  Individuals CHILD_OF multiple families: {len(multi_child)}")
        for r in multi_child[:10]:
            print(f"    {r['name']} [{r['id']}]  in {r['fam_count']} families: {r['fam_ids']}")
        report["multi_family_children"] = multi_child

        # Families with only children, no spouses
        no_spouse_fams = run_query(s, """
            MATCH (f:Family)
            WHERE NOT (:Individual)-[:SPOUSE_IN]->(f)
              AND (:Individual)-[:CHILD_OF]->(f)
            WITH f
            OPTIONAL MATCH (c:Individual)-[:CHILD_OF]->(f)
            RETURN f.id AS id, count(c) AS child_count,
                   collect(c.name)[..5] AS sample_children
        """)
        print(f"  Families with children but no spouses: {len(no_spouse_fams)}")
        for r in no_spouse_fams[:10]:
            print(f"    [{r['id']}]  {r['child_count']} children: {r['sample_children']}")
        report["families_no_spouses"] = no_spouse_fams

        # =============================================================
        # 7. CHRONOLOGICAL ISSUES
        # =============================================================
        section("7. CHRONOLOGICAL ISSUES")
        chrono_issues = {
            "death_before_birth": [],
            "parent_born_after_child": [],
            "parent_age_suspicious": [],
            "lifespan_over_110": [],
            "marriage_before_14": [],
        }

        # Death before birth
        dbb = run_query(s, """
            MATCH (i:Individual)
            WHERE i.birth_year IS NOT NULL AND i.death_year IS NOT NULL
              AND i.death_year < i.birth_year
            RETURN i.id AS id, i.name AS name,
                   i.birth_year AS birth_year, i.death_year AS death_year
        """)
        chrono_issues["death_before_birth"] = dbb
        subsection(f"Death before birth: {len(dbb)}")
        for r in dbb:
            print(f"    {r['name']}  b.{r['birth_year']} d.{r['death_year']}  [{r['id']}]")

        # Parent born after child
        pac = run_query(s, """
            MATCH (child:Individual)-[:CHILD_OF]->(f:Family)<-[:SPOUSE_IN]-(parent:Individual)
            WHERE parent.birth_year IS NOT NULL AND child.birth_year IS NOT NULL
              AND parent.birth_year >= child.birth_year
            RETURN parent.id AS parent_id, parent.name AS parent_name,
                   parent.birth_year AS parent_by,
                   child.id AS child_id, child.name AS child_name,
                   child.birth_year AS child_by
        """)
        chrono_issues["parent_born_after_child"] = pac
        subsection(f"Parent born after child: {len(pac)}")
        for r in pac:
            print(f"    Parent: {r['parent_name']} (b.{r['parent_by']}) -> "
                  f"Child: {r['child_name']} (b.{r['child_by']})")

        # Parent age suspicious
        suspicious_ages = run_query(s, """
            MATCH (child:Individual)-[:CHILD_OF]->(f:Family)<-[:SPOUSE_IN]-(parent:Individual)
            WHERE parent.birth_year IS NOT NULL AND child.birth_year IS NOT NULL
              AND parent.birth_year < child.birth_year
            WITH parent, child, child.birth_year - parent.birth_year AS age_at_birth
            WHERE (parent.sex = 'F' AND (age_at_birth < 14 OR age_at_birth > 50))
               OR (parent.sex = 'M' AND (age_at_birth < 14 OR age_at_birth > 75))
               OR (parent.sex IS NULL AND (age_at_birth < 14 OR age_at_birth > 75))
            RETURN parent.id AS parent_id, parent.name AS parent_name,
                   parent.sex AS sex, parent.birth_year AS parent_by,
                   child.id AS child_id, child.name AS child_name,
                   child.birth_year AS child_by, age_at_birth
            ORDER BY age_at_birth DESC
        """)
        chrono_issues["parent_age_suspicious"] = suspicious_ages
        subsection(f"Suspicious parent age at child birth: {len(suspicious_ages)}")
        for r in suspicious_ages[:20]:
            print(f"    {r['parent_name']} ({r['sex'] or '?'}, b.{r['parent_by']}) "
                  f"age {r['age_at_birth']} at birth of {r['child_name']} (b.{r['child_by']})")
        if len(suspicious_ages) > 20:
            print(f"    ... and {len(suspicious_ages) - 20} more")

        # Lifespan > 110
        long_life = run_query(s, """
            MATCH (i:Individual)
            WHERE i.birth_year IS NOT NULL AND i.death_year IS NOT NULL
              AND i.death_year - i.birth_year > 110
            RETURN i.id AS id, i.name AS name,
                   i.birth_year AS birth_year, i.death_year AS death_year,
                   i.death_year - i.birth_year AS lifespan
            ORDER BY lifespan DESC
        """)
        chrono_issues["lifespan_over_110"] = long_life
        subsection(f"Lifespan > 110 years: {len(long_life)}")
        for r in long_life:
            print(f"    {r['name']}  b.{r['birth_year']} d.{r['death_year']} "
                  f"({r['lifespan']} years)  [{r['id']}]")

        # Marriage before age 14
        early_marriage = run_query(s, """
            MATCH (i:Individual)-[:SPOUSE_IN]->(f:Family)
            WHERE i.birth_year IS NOT NULL AND f.marriage_year IS NOT NULL
              AND f.marriage_year - i.birth_year < 14
              AND f.marriage_year > i.birth_year
            RETURN i.id AS id, i.name AS name, i.birth_year AS birth_year,
                   f.id AS fam_id, f.marriage_year AS marriage_year,
                   f.marriage_year - i.birth_year AS age_at_marriage
            ORDER BY age_at_marriage
        """)
        # Also try marriage_date_raw parse if marriage_year not present
        if not early_marriage:
            early_marriage = run_query(s, """
                MATCH (i:Individual)-[:SPOUSE_IN]->(f:Family)
                WHERE i.birth_year IS NOT NULL
                  AND f.marriage_date_raw IS NOT NULL
                  AND f.marriage_date_raw =~ '.*\\\\d{4}$'
                WITH i, f,
                     toInteger(right(f.marriage_date_raw, 4)) AS m_year
                WHERE m_year IS NOT NULL
                  AND m_year - i.birth_year < 14
                  AND m_year > i.birth_year
                RETURN i.id AS id, i.name AS name, i.birth_year AS birth_year,
                       f.id AS fam_id, m_year AS marriage_year,
                       m_year - i.birth_year AS age_at_marriage
                ORDER BY age_at_marriage
            """)
        chrono_issues["marriage_before_14"] = early_marriage
        subsection(f"Marriage before age 14: {len(early_marriage)}")
        for r in early_marriage:
            print(f"    {r['name']} (b.{r['birth_year']}) married at age "
                  f"{r['age_at_marriage']} [{r['id']}]")

        report["chronological_issues"] = chrono_issues

        # =============================================================
        # 8. NAME ISSUES
        # =============================================================
        section("8. NAME ISSUES")

        # ALL CAPS components
        all_indis = run_query(s, """
            MATCH (i:Individual)
            RETURN i.id AS id, i.name AS name,
                   i.given_name AS given_name, i.surname AS surname
        """)
        all_caps = []
        for r in all_indis:
            for field in ["name", "given_name", "surname"]:
                val = r.get(field)
                if val:
                    words = val.split()
                    for w in words:
                        if len(w) > 1 and w == w.upper() and w.isalpha():
                            all_caps.append({
                                "id": r["id"], "name": r["name"],
                                "field": field, "value": val
                            })
                            break

        subsection(f"Names with ALL CAPS components: {len(all_caps)}")
        seen = set()
        for r in all_caps[:20]:
            key = r["id"] + r["field"]
            if key not in seen:
                seen.add(key)
                print(f"    {r['name']:40s} {r['field']}={r['value']!r}  [{r['id']}]")
        if len(all_caps) > 20:
            print(f"    ... and {len(all_caps) - 20} more")
        report["names_all_caps"] = all_caps

        # Suffixes in name fields
        suffix_pattern = re.compile(
            r'\b(Jr\.?|Sr\.?|II|III|IV|V|VI|VII|VIII)\b', re.IGNORECASE
        )
        suffix_issues = []
        for r in all_indis:
            for field in ["given_name", "surname", "name"]:
                val = r.get(field)
                if val and suffix_pattern.search(val):
                    suffix_issues.append({
                        "id": r["id"], "name": r["name"],
                        "field": field, "value": val
                    })

        # Deduplicate by id
        seen_suffix = set()
        unique_suffix = []
        for s_item in suffix_issues:
            if s_item["id"] not in seen_suffix:
                seen_suffix.add(s_item["id"])
                unique_suffix.append(s_item)

        subsection(f"Names with suffixes in name field: {len(unique_suffix)}")
        for r in unique_suffix[:20]:
            print(f"    {r['name']:40s} {r['field']}={r['value']!r}  [{r['id']}]")
        if len(unique_suffix) > 20:
            print(f"    ... and {len(unique_suffix) - 20} more")
        report["names_with_suffixes"] = unique_suffix

        # Empty given_name or surname where name exists
        empty_parts = run_query(s, """
            MATCH (i:Individual)
            WHERE i.name IS NOT NULL AND i.name <> '' AND i.name <> 'Unknown'
              AND (i.given_name IS NULL OR i.given_name = ''
                   OR i.surname IS NULL OR i.surname = '')
            RETURN i.id AS id, i.name AS name,
                   i.given_name AS given_name, i.surname AS surname
            ORDER BY i.name
        """)
        subsection(f"Name exists but given_name or surname empty: {len(empty_parts)}")
        for r in empty_parts[:20]:
            print(f"    {r['name']:40s} given={r['given_name']!r}  surname={r['surname']!r}  [{r['id']}]")
        if len(empty_parts) > 20:
            print(f"    ... and {len(empty_parts) - 20} more")
        report["names_missing_parts"] = empty_parts

    driver.close()

    # =============================================================
    # SUMMARY
    # =============================================================
    section("AUDIT SUMMARY")
    summary = {
        "total_individuals": stats["total_individuals"],
        "total_families": stats["total_families"],
        "total_places": stats["total_places"],
        "total_sources": stats["total_sources"],
        "exact_duplicates": len(exact_dupes),
        "fuzzy_duplicates": len(fuzzy_dupes),
        "orphaned_individuals": len(orphans),
        "unsourced_individuals": unsourced_count,
        "empty_families": len(empty_fams),
        "multi_family_children": len(multi_child),
        "death_before_birth": len(dbb),
        "parent_born_after_child": len(pac),
        "suspicious_parent_age": len(suspicious_ages),
        "lifespan_over_110": len(long_life),
        "marriage_before_14": len(early_marriage),
        "names_all_caps": len(all_caps),
        "names_with_suffixes": len(unique_suffix),
        "non_standardized_dates": len(non_std),
    }
    for k, v in summary.items():
        flag = " !!!" if isinstance(v, int) and v > 0 and k not in (
            "total_individuals", "total_families", "total_places", "total_sources"
        ) else ""
        print(f"  {k:35s}: {v}{flag}")

    report["summary"] = summary

    # Save JSON report
    os.makedirs(REPORT_DIR, exist_ok=True)

    # Convert neo4j types to JSON-serializable
    def make_serializable(obj):
        if isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [make_serializable(i) for i in obj]
        if isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        return str(obj)

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(make_serializable(report), f, indent=2, ensure_ascii=False)
    print(f"\n  JSON report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
