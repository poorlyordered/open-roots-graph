from app.services.cypher_sanitizer import CypherSanitizer


def test_blocks_write_queries():
    sanitizer = CypherSanitizer()

    valid, reason = sanitizer.validate("MATCH (n) DETACH DELETE n")

    assert valid is False
    assert "DETACH" in reason


def test_enforces_limit_for_read_queries():
    sanitizer = CypherSanitizer()

    query = sanitizer.enforce_limit("MATCH (i:Individual) RETURN i.name", 50)

    assert query.endswith("LIMIT 50")


def test_allows_read_query_with_limit():
    sanitizer = CypherSanitizer()

    valid, reason = sanitizer.validate("MATCH (i:Individual) RETURN i.name LIMIT 10")

    assert valid is True
    assert reason == ""
