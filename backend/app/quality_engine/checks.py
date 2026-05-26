from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from app.quality_engine.models import FixProposal, QualityFinding
from app.quality_engine.normalizers import (
    normalize_gedcom_date,
    normalize_person_name,
    normalize_place,
    normalized_identity_key,
)


def check_people(individuals: dict[str, dict]) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    identity_groups: dict[tuple[str, int | None], list[dict]] = defaultdict(list)

    for person in individuals.values():
        person_id = person["id"]
        name = person.get("name")
        given = person.get("given_name")
        surname = person.get("surname")

        if not name or normalized_identity_key(name) in {"unknown", "private", "living"}:
            findings.append(
                QualityFinding(
                    check_id="PERSON_UNKNOWN_NAME",
                    severity="medium",
                    entity_type="individual",
                    entity_id=person_id,
                    field="name",
                    observed=name,
                    message="Individual has a blank, unknown, or private placeholder name.",
                    suggested_action="Replace with a researched name or mark the person private for export.",
                )
            )

        if not given or not surname:
            findings.append(
                QualityFinding(
                    check_id="PERSON_MISSING_NAME_PARTS",
                    severity="medium",
                    entity_type="individual",
                    entity_id=person_id,
                    field="name",
                    observed=name,
                    message="Individual is missing a structured given name or surname.",
                    suggested_action="Split the display name into GEDCOM GIVN and SURN fields.",
                )
            )

        normalized_name = normalize_person_name(name)
        if name and normalized_name and name != normalized_name:
            findings.append(
                QualityFinding(
                    check_id="PERSON_ALL_CAPS_NAME",
                    severity="low",
                    entity_type="individual",
                    entity_id=person_id,
                    field="name",
                    observed=name,
                    message="Individual name casing can be normalized.",
                    suggested_action="Apply title casing after reviewing surname conventions.",
                    confidence=0.85,
                    fix=FixProposal(
                        field="name",
                        before=name,
                        after=normalized_name,
                        mode="automatic",
                        confidence=0.85,
                        note="Normalize all-caps display name.",
                    ),
                )
            )

        birth_year = _year_from_person(person, "birth_date")
        key = (normalized_identity_key(name), birth_year)
        if key[0] and key[1]:
            identity_groups[key].append(person)

        findings.extend(_date_findings(person, "birth_date"))
        findings.extend(_date_findings(person, "death_date"))
        findings.extend(_place_findings(person, "birth_place"))
        findings.extend(_place_findings(person, "death_place"))
        findings.extend(_place_findings(person, "burial_place"))

        birth = _year_from_person(person, "birth_date")
        death = _year_from_person(person, "death_date")
        if birth and death and death < birth:
            findings.append(
                QualityFinding(
                    check_id="DATE_DEATH_BEFORE_BIRTH",
                    severity="critical",
                    entity_type="individual",
                    entity_id=person_id,
                    field="death_date",
                    observed={"birth_year": birth, "death_year": death},
                    message="Death year occurs before birth year.",
                    suggested_action="Verify birth and death dates before relying on this person.",
                )
            )
        elif birth and death and death - birth > 110:
            findings.append(
                QualityFinding(
                    check_id="DATE_LIFESPAN_OVER_LIMIT",
                    severity="high",
                    entity_type="individual",
                    entity_id=person_id,
                    field="death_date",
                    observed={"birth_year": birth, "death_year": death},
                    message="Lifespan exceeds the configured 110-year threshold.",
                    suggested_action="Verify dates and possible person merges.",
                )
            )

    for group in identity_groups.values():
        if len(group) < 2:
            continue
        for person in group:
            findings.append(
                QualityFinding(
                    check_id="PERSON_DUP_EXACT",
                    severity="high",
                    entity_type="individual",
                    entity_id=person["id"],
                    related_entity_ids=[p["id"] for p in group if p["id"] != person["id"]],
                    observed={"name": person.get("name"), "birth_year": _year_from_person(person, "birth_date")},
                    message="Multiple individuals share the same normalized name and birth year.",
                    suggested_action="Review these people as possible duplicates before merging.",
                    confidence=0.9,
                    fix=FixProposal(
                        field="individual",
                        before=[p["id"] for p in group],
                        after=group[0]["id"],
                        mode="review",
                        confidence=0.9,
                        note="Possible duplicate person merge.",
                    ),
                )
            )

    return findings


def check_families(individuals: dict[str, dict], families: dict[str, dict]) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    child_to_families: dict[str, list[str]] = defaultdict(list)

    for family in families.values():
        family_id = family["id"]
        spouses = [p for p in [family.get("husband"), family.get("wife")] if p]
        children = family.get("children", [])

        if not spouses and not children:
            findings.append(
                QualityFinding(
                    check_id="FAMILY_EMPTY",
                    severity="high",
                    entity_type="family",
                    entity_id=family_id,
                    message="Family has no spouses and no children.",
                    suggested_action="Delete the empty family or reconnect its members.",
                )
            )

        if children and not spouses:
            findings.append(
                QualityFinding(
                    check_id="FAMILY_NO_SPOUSE",
                    severity="medium",
                    entity_type="family",
                    entity_id=family_id,
                    related_entity_ids=children,
                    message="Family has children but no spouse or parent records.",
                    suggested_action="Confirm whether this is intentional or missing parent data.",
                )
            )

        for child_id in children:
            child_to_families[child_id].append(family_id)

        findings.extend(_check_parent_child_ages(family, individuals))
        findings.extend(_check_marriage_ages(family, individuals))
        findings.extend(_check_sibling_spacing(family, individuals))

    for child_id, family_ids in child_to_families.items():
        if len(family_ids) > 1:
            findings.append(
                QualityFinding(
                    check_id="FAMILY_MULTI_PARENT_FAMILY",
                    severity="high",
                    entity_type="individual",
                    entity_id=child_id,
                    related_entity_ids=family_ids,
                    observed={"family_count": len(family_ids)},
                    message="Individual is linked as a child in multiple families.",
                    suggested_action="Review biological, adoptive, step, or duplicate family relationships.",
                )
            )

    return findings


def _date_findings(person: dict, field: str) -> list[QualityFinding]:
    raw = person.get(field)
    normalized = normalize_gedcom_date(raw)
    if not raw or normalized is None:
        return []

    if not normalized.parseable:
        return [
            QualityFinding(
                check_id="DATE_PARSE_FAILED",
                severity="medium",
                entity_type="individual",
                entity_id=person["id"],
                field=field,
                observed=raw,
                message="Date could not be parsed into a GEDCOM-compatible date.",
                suggested_action="Rewrite the date using GEDCOM date syntax.",
            )
        ]

    if normalized.changed and normalized.normalized:
        return [
            QualityFinding(
                check_id="DATE_NON_GEDCOM_FORMAT",
                severity="medium",
                entity_type="individual",
                entity_id=person["id"],
                field=field,
                observed=raw,
                message="Date can be normalized to GEDCOM-compatible syntax.",
                suggested_action="Apply the normalized date after reviewing uncertainty qualifiers.",
                confidence=0.95,
                fix=FixProposal(
                    field=field,
                    before=raw,
                    after=normalized.normalized,
                    mode="automatic",
                    confidence=0.95,
                    note="Normalize date syntax.",
                ),
            )
        ]

    return []


def _place_findings(person: dict, field: str) -> list[QualityFinding]:
    raw = person.get(field)
    normalized = normalize_place(raw)
    if not raw or not normalized or raw == normalized:
        return []
    return [
        QualityFinding(
            check_id="PLACE_DUP_NORMALIZED",
            severity="medium",
            entity_type="individual",
            entity_id=person["id"],
            field=field,
            observed=raw,
            message="Place can be normalized for casing, punctuation, aliases, or duplicate components.",
            suggested_action="Apply normalized place text if it matches the intended jurisdiction.",
            confidence=0.9,
            fix=FixProposal(
                field=field,
                before=raw,
                after=normalized,
                mode="automatic",
                confidence=0.9,
                note="Normalize place text.",
            ),
        )
    ]


def _check_parent_child_ages(family: dict, individuals: dict[str, dict]) -> Iterable[QualityFinding]:
    family_id = family["id"]
    parents = [p for p in [family.get("husband"), family.get("wife")] if p]
    for child_id in family.get("children", []):
        child = individuals.get(child_id)
        child_birth = _year_from_person(child, "birth_date") if child else None
        if not child_birth:
            continue

        for parent_id in parents:
            parent = individuals.get(parent_id)
            parent_birth = _year_from_person(parent, "birth_date") if parent else None
            parent_death = _year_from_person(parent, "death_date") if parent else None
            if not parent_birth:
                continue

            age = child_birth - parent_birth
            if age < 14:
                yield QualityFinding(
                    check_id="FAMILY_PARENT_TOO_YOUNG",
                    severity="high",
                    entity_type="individual",
                    entity_id=parent_id,
                    related_entity_ids=[child_id, family_id],
                    observed={"parent_age": age, "child_birth_year": child_birth},
                    message="Parent is younger than the configured minimum age at child birth.",
                    suggested_action="Verify parentage, parent birth year, and child birth year.",
                )
            elif age > 80:
                yield QualityFinding(
                    check_id="FAMILY_PARENT_TOO_OLD",
                    severity="medium",
                    entity_type="individual",
                    entity_id=parent_id,
                    related_entity_ids=[child_id, family_id],
                    observed={"parent_age": age, "child_birth_year": child_birth},
                    message="Parent is older than the configured maximum age at child birth.",
                    suggested_action="Verify generation, parentage, and duplicate same-name relatives.",
                )

            if parent_death and child_birth > parent_death + 1:
                check_id = "FAMILY_CHILD_AFTER_FATHER_DEATH" if parent_id == family.get("husband") else "FAMILY_CHILD_AFTER_MOTHER_DEATH"
                yield QualityFinding(
                    check_id=check_id,
                    severity="critical",
                    entity_type="individual",
                    entity_id=child_id,
                    related_entity_ids=[parent_id, family_id],
                    observed={"child_birth_year": child_birth, "parent_death_year": parent_death},
                    message="Child birth occurs after the parent's death grace period.",
                    suggested_action="Verify parent death date, child birth date, and family assignment.",
                )


def _check_marriage_ages(family: dict, individuals: dict[str, dict]) -> Iterable[QualityFinding]:
    if not family.get("marriages"):
        return
    marriage_year = None
    for marriage in family["marriages"]:
        marriage_year = _year_from_value(marriage.get("date"))
        if marriage_year:
            break
    if not marriage_year:
        return

    for spouse_id in [family.get("husband"), family.get("wife")]:
        if not spouse_id:
            continue
        spouse = individuals.get(spouse_id)
        birth_year = _year_from_person(spouse, "birth_date") if spouse else None
        if birth_year and marriage_year - birth_year < 14:
            yield QualityFinding(
                check_id="FAMILY_MARRIAGE_TOO_YOUNG",
                severity="high",
                entity_type="individual",
                entity_id=spouse_id,
                related_entity_ids=[family["id"]],
                observed={"marriage_age": marriage_year - birth_year, "marriage_year": marriage_year},
                message="Marriage age is below the configured minimum.",
                suggested_action="Verify spouse identity, birth date, and marriage date.",
            )


def _check_sibling_spacing(family: dict, individuals: dict[str, dict]) -> Iterable[QualityFinding]:
    children = []
    for child_id in family.get("children", []):
        child = individuals.get(child_id)
        year = _year_from_person(child, "birth_date") if child else None
        if year:
            children.append((year, child_id))
    children.sort()

    for (year_a, id_a), (year_b, id_b) in zip(children, children[1:]):
        if year_a == year_b:
            yield QualityFinding(
                check_id="FAMILY_CHILDREN_TOO_CLOSE",
                severity="medium",
                entity_type="family",
                entity_id=family["id"],
                related_entity_ids=[id_a, id_b],
                observed={"birth_years": [year_a, year_b]},
                message="Children in the same family have birth years too close to distinguish from twins or duplicates.",
                suggested_action="Verify whether these are twins, duplicates, or approximate dates.",
                confidence=0.75,
            )


def _year_from_person(person: dict | None, field: str) -> int | None:
    if not person:
        return None
    return _year_from_value(person.get(field))


def _year_from_value(value: str | None) -> int | None:
    normalized = normalize_gedcom_date(value)
    return normalized.year if normalized else None

