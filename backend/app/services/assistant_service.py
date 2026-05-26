import json
import re
from collections.abc import Generator

import httpx
from neo4j import Driver

from app.services.cypher_sanitizer import CypherSanitizer
from app.services.schema_introspector import SchemaIntrospector


CYPHER_BLOCK_RE = re.compile(r"```cypher\s*\n(.*?)```", re.DOTALL)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MODE_INSTRUCTIONS = {
    "query": (
        "You are a genealogy research assistant. Answer questions by generating Cypher queries "
        "against the Neo4j database. Wrap each query in a ```cypher``` block. After the query, "
        "explain the results in plain language with genealogical context. "
        "Always use LIMIT to bound results. Return only read queries (MATCH/RETURN/WITH/WHERE/ORDER BY)."
    ),
    "hypothesis": (
        "You are a genealogy hypothesis generator. Analyze the family tree data to suggest "
        "possible connections, identify patterns, and propose theories about family relationships. "
        "Use Cypher queries to gather evidence, then present hypotheses with confidence ratings "
        "(high/medium/low) and reasoning. Look for shared locations, overlapping dates, surname "
        "variants, and migration patterns."
    ),
    "research": (
        "You are a genealogy research planner. Analyze data gaps, unresolved conflicts, and "
        "missing information. Generate Cypher queries to identify individuals with incomplete "
        "records, unverified claims, or open conflicts. Prioritize research tasks by impact "
        "and suggest specific records or sources to investigate."
    ),
}


def _build_system_prompt(schema: str, mode: str) -> str:
    instructions = MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS["query"])
    return f"""{instructions}

# Neo4j Database Schema

{schema}

# Data Model

The database uses an evidence-first genealogy model:
- **Individual** (also labeled :Conclusion) — A person in the tree. Properties: id, name, given_name, surname, sex, birth_date_raw, birth_date_iso, birth_year, death_date_raw, death_date_iso, death_year
- **Family** — A family unit. Individuals connect via SPOUSE_IN and CHILD_OF relationships
- **Place** — A geographic location (normalized). Properties: normalized, city, county, state, country, latitude, longitude
- **Source** — An original source document
- **Record** — A specific record from a source
- **Claim** — An assertion extracted from a record (e.g., birth date, name). Properties: id, claim_type, value, confidence, status
- **Conflict** — A detected data inconsistency. Properties: id, description, field, severity, status, resolution
- **ResearchTask** — A suggested research action. Properties: id, title, description, priority, status

# Key Relationships
- (Individual)-[:CHILD_OF]->(Family) — person is a child in this family
- (Individual)-[:SPOUSE_IN]->(Family) — person is a spouse in this family
- (Individual)-[:BORN_IN]->(Place), [:DIED_IN], [:BURIED_IN], [:RESIDED_IN]
- (Individual)-[:CITED_IN]->(Source)
- (Claim)-[:ABOUT]->(Individual) — claim is about this person
- (Claim)-[:EXTRACTED_FROM]->(Record) — claim extracted from this record
- (Claim)-[:ASSERTS_PLACE]->(Place) — claim references this place
- (Record)-[:FROM_SOURCE]->(Source)
- (Conflict)-[:REGARDING]->(Individual)

# Rules
- ONLY generate read-only Cypher (MATCH, RETURN, WITH, WHERE, ORDER BY, LIMIT, OPTIONAL MATCH)
- NEVER use CREATE, MERGE, DELETE, SET, REMOVE, or DROP
- Always include LIMIT (max 50 rows) to prevent unbounded results
- Use parameterized patterns where possible
- When referring to individuals, use their `name` property for display
- Dates: use birth_year/death_year (integers) for comparisons, birth_date_raw for display
"""


class AssistantService:
    def __init__(self, driver: Driver, api_key: str, model: str):
        self._driver = driver
        self._api_key = api_key
        self._model = model
        self._introspector = SchemaIntrospector(driver)
        self._sanitizer = CypherSanitizer()
        self._http_client = httpx.Client(timeout=120.0)

    def stream_response(
        self, message: str, history: list[dict], mode: str
    ) -> Generator[dict, None, None]:
        schema = self._introspector.get_schema_prompt()
        system_prompt = _build_system_prompt(schema, mode)

        messages = [{"role": "system", "content": system_prompt}]
        for m in history:
            messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": message})

        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": 4096,
            "stream": True,
        }

        accumulated = ""

        try:
            with self._http_client.stream(
                    "POST",
                    OPENROUTER_URL,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "http://localhost:3000",
                        "X-Title": "Roots Graph Research Assistant",
                    },
                ) as response:
                    if response.status_code != 200:
                        body = response.read().decode()
                        yield {"type": "error", "content": f"API error {response.status_code}: {body}"}
                        yield {"type": "done", "content": ""}
                        return

                    buffer = ""
                    for chunk in response.iter_text():
                        buffer += chunk
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            line = line.strip()
                            if not line or not line.startswith("data: "):
                                continue
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break

                            try:
                                data = json.loads(data_str)
                                choices = data.get("choices", [])
                                if not choices:
                                    continue
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    accumulated += content
                                    yield {"type": "text", "content": content}
                            except (json.JSONDecodeError, IndexError, KeyError):
                                continue

        except httpx.HTTPError as e:
            yield {"type": "error", "content": f"Connection error: {str(e)}"}
            yield {"type": "done", "content": ""}
            return

        # Extract and execute Cypher blocks from the full response
        cypher_blocks = CYPHER_BLOCK_RE.findall(accumulated)
        for cypher in cypher_blocks:
            cypher = cypher.strip()
            yield {"type": "cypher", "content": cypher}

            valid, reason = self._sanitizer.validate(cypher)
            if not valid:
                yield {"type": "error", "content": f"Query blocked: {reason}"}
                continue

            cypher = self._sanitizer.enforce_limit(cypher, 50)

            try:
                with self._driver.session() as session:
                    def _run_read(tx):
                        result = tx.run(cypher)
                        records = []
                        for record in result:
                            row = {}
                            for key in record.keys():
                                val = record[key]
                                if hasattr(val, "__dict__") and hasattr(val, "items"):
                                    row[key] = dict(val.items())
                                else:
                                    row[key] = val
                            records.append(row)
                        return records

                    records = session.execute_read(_run_read)
                    yield {
                        "type": "data",
                        "content": json.dumps(records, default=str),
                    }
            except Exception as e:
                yield {
                    "type": "error",
                    "content": f"Query execution error: {str(e)}",
                }

        yield {"type": "done", "content": ""}

    def get_suggestions(self) -> list[dict]:
        suggestions = []

        with self._driver.session() as session:
            def _read_context(tx):
                surnames = [r["surname"] for r in tx.run(
                    "MATCH (i:Individual) WHERE i.surname IS NOT NULL "
                    "RETURN i.surname AS surname, count(*) AS cnt "
                    "ORDER BY cnt DESC LIMIT 5"
                )]
                conflicts = tx.run(
                    "MATCH (c:Conflict {status: 'open'}) RETURN count(c) AS cnt"
                ).single()["cnt"]
                dates = tx.run(
                    "MATCH (i:Individual) WHERE i.birth_year IS NOT NULL "
                    "RETURN min(i.birth_year) AS earliest, max(i.birth_year) AS latest"
                ).single()
                return surnames, conflicts, dates["earliest"], dates["latest"]

            top_surnames, open_conflicts, earliest, latest = session.execute_read(_read_context)

        if top_surnames:
            suggestions.append({
                "mode": "query",
                "text": f"Who are the earliest ancestors in the {top_surnames[0]} line?",
            })
            suggestions.append({
                "mode": "query",
                "text": f"Show all {top_surnames[0]} family members and their birth places",
            })

        suggestions.append({
            "mode": "query",
            "text": "Who lived the longest in the tree?",
        })
        suggestions.append({
            "mode": "query",
            "text": "Which families had the most children?",
        })

        if earliest and latest:
            suggestions.append({
                "mode": "query",
                "text": f"Show people born between {earliest} and {earliest + 50}",
            })

        suggestions.append({
            "mode": "hypothesis",
            "text": "Which individuals might be related based on shared locations and time periods?",
        })
        suggestions.append({
            "mode": "hypothesis",
            "text": "Are there surname variants that might represent the same family?",
        })

        if open_conflicts > 0:
            suggestions.append({
                "mode": "research",
                "text": f"There are {open_conflicts} open conflicts. Which should I resolve first?",
            })
        suggestions.append({
            "mode": "research",
            "text": "Which individuals have the most incomplete records?",
        })
        suggestions.append({
            "mode": "research",
            "text": "What are the biggest data gaps in the tree?",
        })

        return suggestions
