import re


WRITE_KEYWORDS = re.compile(
    r"\b(CREATE|MERGE|DELETE|DETACH|SET|REMOVE|DROP|FOREACH|LOAD|CSV|EXPLAIN|PROFILE)\b",
    re.IGNORECASE,
)

SAFE_PROCEDURES = {
    "db.labels",
    "db.relationshiptypes",
    "db.schema.nodetypeproperties",
    "db.schema.reltypeproperties",
    "db.indexes",
    "db.constraints",
    "apoc.meta.nodetypeproperties",
}


class CypherSanitizer:
    def validate(self, cypher: str) -> tuple[bool, str]:
        stripped = cypher.strip()
        if not stripped:
            return False, "Empty query"

        # Strip single-line and block comments before checking keywords
        no_comments = re.sub(r"//.*$", "", stripped, flags=re.MULTILINE)
        no_comments = re.sub(r"/\*.*?\*/", "", no_comments, flags=re.DOTALL)

        match = WRITE_KEYWORDS.search(no_comments)
        if match:
            return False, f"Write operation not allowed: {match.group()}"

        # Block IN TRANSACTIONS subquery syntax
        if re.search(r"\bIN\s+TRANSACTIONS\b", no_comments, re.IGNORECASE):
            return False, "IN TRANSACTIONS not allowed"

        # Check CALL statements — only allow whitelisted procedures
        # Match both CALL proc.name and CALL { subquery }
        call_matches = re.finditer(r"\bCALL\s+(\{|[\w.]+)", no_comments, re.IGNORECASE)
        for m in call_matches:
            if m.group(1) == "{":
                return False, "CALL subqueries not allowed"
            proc = m.group(1).lower()
            if proc not in SAFE_PROCEDURES:
                return False, f"Procedure not allowed: {m.group(1)}"

        # Enforce LIMIT to prevent unbounded results
        if not re.search(r"\bLIMIT\b", no_comments, re.IGNORECASE):
            return True, "missing_limit"

        return True, ""

    def enforce_limit(self, cypher: str, default_limit: int = 100) -> str:
        if not re.search(r"\bLIMIT\b", cypher, re.IGNORECASE):
            return f"{cypher.rstrip().rstrip(';')}\nLIMIT {default_limit}"
        return cypher
