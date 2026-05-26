from pathlib import Path

from scripts.import_tree import normalize_date, normalize_place, parse_gedcom


ROOT = Path(__file__).resolve().parents[2]


def test_parse_sample_tree_fixture():
    individuals, families, sources = parse_gedcom(ROOT / "examples" / "sample-tree.ged")

    assert len(individuals) == 3
    assert len(families) == 1
    assert sources == {}
    assert individuals["@I1@"]["surname"] == "Example"
    assert families["@F1@"]["children"] == ["@I3@"]


def test_normalize_date_year_month_day():
    result = normalize_date("1 JAN 1900")

    assert result["iso"] == "1900-01-01"
    assert result["year"] == 1900


def test_normalize_place_components():
    result = normalize_place("Springfield, Example County, Illinois, USA")

    assert result["city"] == "Springfield"
    assert result["county"] == "Example County"
    assert result["state"] == "Illinois"
    assert result["country"] == "USA"

