# Genealogy Data Quality Checks

This document defines reusable checks for GEDCOM-style genealogy data. The checks are intended to work on private local datasets without requiring users to publish family records.

## Severity Levels

- `critical`: The data is logically impossible and should be reviewed before relying on the affected relationship or fact.
- `high`: The data is likely wrong or duplicated and can distort research priorities, pedigrees, and exports.
- `medium`: The data is incomplete, ambiguous, or non-standard but may still be usable.
- `low`: The data is stylistically inconsistent or needs normalization.

## Person Identity Checks

| ID | Severity | Check | Rationale |
| --- | --- | --- | --- |
| `PERSON_DUP_EXACT` | high | Same normalized full name and same birth year across multiple individuals. | Often indicates duplicate imports or repeated attachment of the same ancestor. |
| `PERSON_DUP_FUZZY` | high | Similar normalized names with close birth years and overlapping family/place context. | Catches spelling variants, casing differences, initials, nicknames, and duplicated branches. |
| `PERSON_MISSING_NAME_PARTS` | medium | Missing given name or surname. | Weakens search, duplicate detection, and surname-line analysis. |
| `PERSON_UNKNOWN_NAME` | medium | Name is blank, unknown, private, living placeholder, or only punctuation. | Usually requires either privacy handling or source review. |
| `PERSON_ALL_CAPS_NAME` | low | Name is all caps or inconsistent casing. | Affects readability and duplicate matching. |
| `PERSON_SUFFIX_IN_NAME` | low | Suffix appears inside name fields rather than a structured suffix field. | Helps normalize Jr., Sr., II, III, and similar values. |

## Date Checks

| ID | Severity | Check | Rationale |
| --- | --- | --- | --- |
| `DATE_PARSE_FAILED` | medium | Raw date cannot be parsed into year, month, or day. | Prevents chronological checks and timeline views. |
| `DATE_NON_GEDCOM_FORMAT` | medium | Date is parseable but not GEDCOM-standard, such as slash dates or free text. | Standardizing dates improves export quality and interoperability. |
| `DATE_AMBIGUOUS_RANGE` | medium | Date range cannot be represented cleanly, such as partial `BET` or conflicting year ranges. | Requires preserving uncertainty while extracting sortable year bounds. |
| `DATE_FUTURE_EVENT` | high | Birth, death, marriage, burial, or residence date is in the future. | Usually a typo or import error. |
| `DATE_DEATH_BEFORE_BIRTH` | critical | Death date occurs before birth date. | Logically impossible. |
| `DATE_LIFESPAN_OVER_LIMIT` | high | Lifespan exceeds a configured threshold, default 110 or 120 years. | May indicate wrong person merge, typo, or wrong generation. |

## Family Chronology Checks

| ID | Severity | Check | Rationale |
| --- | --- | --- | --- |
| `FAMILY_PARENT_TOO_YOUNG` | high | Parent is younger than configured minimum age at child birth, default 14. | Often indicates parent/child misassignment or duplicate same-name relatives. |
| `FAMILY_PARENT_TOO_OLD` | medium | Parent is older than configured maximum age at child birth. Suggested defaults: mother 55, father 80. | Can reveal generation skips or incorrect parentage. |
| `FAMILY_CHILD_AFTER_MOTHER_DEATH` | critical | Child birth is after mother's death. | Logically impossible unless death or parentage is wrong. |
| `FAMILY_CHILD_AFTER_FATHER_DEATH` | critical | Child birth is more than a configured grace period after father's death, default 1 year. | Indicates wrong death date or parent assignment. |
| `FAMILY_MARRIAGE_BEFORE_BIRTH` | critical | Marriage occurs before either spouse's birth. | Logically impossible. |
| `FAMILY_MARRIAGE_TOO_YOUNG` | high | Marriage age is below configured minimum, default 14. | Often related to wrong generation or wrong spouse assignment. |
| `FAMILY_CHILDREN_TOO_CLOSE` | medium | Non-twin siblings in same family are born less than 9 months apart. | May indicate duplicate children, approximate dates, or twin/multiple birth evidence needed. |
| `FAMILY_MULTI_PARENT_FAMILY` | high | Individual is linked as a child in multiple families without adoption/step/guardian evidence. | Can distort pedigrees and ancestor traversal. |
| `FAMILY_EMPTY` | high | Family has no spouses and no children. | Usually import residue. |
| `FAMILY_NO_SPOUSE` | medium | Family has children but no parent spouse records. | May be valid, but should be visible for research planning. |

## Source and Evidence Checks

| ID | Severity | Check | Rationale |
| --- | --- | --- | --- |
| `SOURCE_UNSOURCED_PERSON` | medium | Individual has no source citations or evidence claims. | Useful for research priority scoring. |
| `SOURCE_LOW_CITATION_COUNT` | low | Individual has fewer than a configured citation count. | Helps distinguish lightly supported facts from well-evidenced ones. |
| `SOURCE_EMPTY_TITLE` | low | Source has no title. | Hard to evaluate or cite later. |
| `SOURCE_DUP_TITLE` | medium | Multiple source records share the same normalized title and metadata. | May indicate duplicated source imports. |
| `CLAIM_CONFLICTING_VALUES` | high | Multiple accepted claims for the same field disagree. | Supports evidence-first cleanup workflows. |
| `CLAIM_LOW_CONFIDENCE_ACCEPTED` | medium | Accepted claim confidence is below configured threshold. | Flags facts that should be re-reviewed. |

## Place Checks

| ID | Severity | Check | Rationale |
| --- | --- | --- | --- |
| `PLACE_MISSING_COUNTRY` | medium | Place has no country component. | Reduces geocoding and disambiguation quality. |
| `PLACE_MISSING_STATE_REGION` | medium | Place has no state, province, or region where expected. | Common in US-heavy data and weakens maps. |
| `PLACE_STATE_ONLY` | low | Place only identifies broad state/country. | May be valid but low precision. |
| `PLACE_DUP_NORMALIZED` | medium | Different raw places normalize to the same key or near-key. | Helps merge casing, punctuation, abbreviation, and country variants. |
| `PLACE_GEOCODE_MISSING` | low | Place has no latitude/longitude after geocoding. | Affects migration maps but not genealogical correctness. |
| `PLACE_COMPONENT_DUPLICATE` | low | Adjacent place parts repeat, such as `Kentucky, Kentucky, USA`. | Common GEDCOM export cleanup issue. |

## Graph Topology Checks

| ID | Severity | Check | Rationale |
| --- | --- | --- | --- |
| `GRAPH_ORPHAN_PERSON` | medium | Individual has no family links. | Can be valid, but often represents detached imports or notes. |
| `GRAPH_CYCLE_ANCESTRY` | critical | Person is reachable as their own ancestor. | Breaks pedigree traversal and research scoring. |
| `GRAPH_DUP_RELATIONSHIP` | low | Duplicate identical relationships exist between the same nodes. | Usually import residue and can inflate counts. |
| `GRAPH_ROLE_CONFLICT` | high | A person has conflicting spouse/parent role data in the same family. | Can distort family views and GEDCOM export. |

## Privacy Checks

| ID | Severity | Check | Rationale |
| --- | --- | --- | --- |
| `PRIVACY_LIVING_PERSON_WITH_DETAILS` | high | Living or likely-living person has birth date, place, notes, or source details in an export intended for sharing. | Prevents accidental disclosure. |
| `PRIVACY_PRIVATE_PLACEHOLDER` | medium | Person has placeholder names such as Private, Living, or Unknown with attached relationship details. | Needs explicit handling before publication. |
| `PRIVACY_RECENT_EVENT` | medium | Event date is within a configurable recent window, default 100 years. | Useful for public export redaction. |

## Recommended Output Model

Every check should produce structured findings:

```json
{
  "check_id": "FAMILY_PARENT_TOO_YOUNG",
  "severity": "high",
  "entity_type": "individual",
  "entity_id": "@I1@",
  "related_entity_ids": ["@I2@", "@F1@"],
  "field": "birth_year",
  "observed": "parent age 11",
  "message": "Parent is younger than the configured minimum age at child birth.",
  "suggested_action": "Verify parentage, parent birth year, and child birth year.",
  "confidence": 0.95
}
```

## Suggested Cleanup Order

1. Fix critical chronology and graph-cycle issues.
2. Resolve exact duplicate people and duplicated family branches.
3. Normalize dates enough to support chronological checks.
4. Normalize places enough to support deduplication and geocoding.
5. Review unsourced or weakly sourced direct ancestors.
6. Clean names, suffixes, casing, and low-severity style issues.

