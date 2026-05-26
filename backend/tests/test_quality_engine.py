from app.quality_engine import GedcomQualityRunner
from app.quality_engine.normalizers import normalize_gedcom_date, normalize_place


def test_normalize_gedcom_date_proposes_standard_month_case():
    normalized = normalize_gedcom_date("Mar 1896")

    assert normalized is not None
    assert normalized.normalized == "MAR 1896"
    assert normalized.year == 1896
    assert normalized.changed is True


def test_normalize_place_removes_duplicate_components_and_aliases():
    assert normalize_place("Kentucky, Kentucky, United States of America") == "Kentucky, USA"


def test_runner_reports_safe_fixes_and_review_fixes():
    individuals = {
        "@I1@": {
            "id": "@I1@",
            "name": "ALEX EXAMPLE",
            "given_name": "Alex",
            "surname": "Example",
            "birth_date": "Mar 1896",
            "birth_place": "KENTUCKY, KENTUCKY, United States of America",
            "death_date": "1980",
            "death_place": None,
            "burial_place": None,
        },
        "@I2@": {
            "id": "@I2@",
            "name": "Alex Example",
            "given_name": "Alex",
            "surname": "Example",
            "birth_date": "1896",
            "birth_place": None,
            "death_date": None,
            "death_place": None,
            "burial_place": None,
        },
    }

    report = GedcomQualityRunner().run(individuals, {})
    check_ids = {finding.check_id for finding in report.findings}

    assert "PERSON_ALL_CAPS_NAME" in check_ids
    assert "DATE_NON_GEDCOM_FORMAT" in check_ids
    assert "PLACE_DUP_NORMALIZED" in check_ids
    assert "PERSON_DUP_EXACT" in check_ids
    assert report.summary["automatic_fixes"] == 3
    assert report.summary["review_fixes"] == 2


def test_runner_reports_family_chronology_issues():
    individuals = {
        "@P1@": {
            "id": "@P1@",
            "name": "Young Parent",
            "given_name": "Young",
            "surname": "Parent",
            "birth_date": "1900",
            "death_date": "1908",
        },
        "@C1@": {
            "id": "@C1@",
            "name": "Late Child",
            "given_name": "Late",
            "surname": "Child",
            "birth_date": "1910",
            "death_date": None,
        },
    }
    families = {
        "@F1@": {
            "id": "@F1@",
            "husband": "@P1@",
            "wife": None,
            "children": ["@C1@"],
            "marriages": [{"date": "1905", "place": None}],
        }
    }

    report = GedcomQualityRunner().run(individuals, families)
    check_ids = {finding.check_id for finding in report.findings}

    assert "FAMILY_PARENT_TOO_YOUNG" in check_ids
    assert "FAMILY_CHILD_AFTER_FATHER_DEATH" in check_ids
    assert "FAMILY_MARRIAGE_TOO_YOUNG" in check_ids
