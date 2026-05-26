"""
Create the evidence layer schema in Neo4j.

Adds indexes and constraints for Record, Claim, Conflict, and ResearchTask nodes.
This is additive — existing schema is preserved.

Usage:
    python -m scripts.seed_evidence_schema
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


def main():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    pw = os.getenv("NEO4J_PASSWORD", "changeme")

    driver = GraphDatabase.driver(uri, auth=(user, pw))

    indexes = [
        # Record indexes
        "CREATE INDEX IF NOT EXISTS FOR (r:Record) ON (r.id)",
        "CREATE INDEX IF NOT EXISTS FOR (r:Record) ON (r.record_type)",
        "CREATE INDEX IF NOT EXISTS FOR (r:Record) ON (r.year)",
        # Claim indexes
        "CREATE INDEX IF NOT EXISTS FOR (c:Claim) ON (c.id)",
        "CREATE INDEX IF NOT EXISTS FOR (c:Claim) ON (c.claim_type)",
        "CREATE INDEX IF NOT EXISTS FOR (c:Claim) ON (c.status)",
        "CREATE INDEX IF NOT EXISTS FOR (c:Claim) ON (c.confidence)",
        # Conflict indexes
        "CREATE INDEX IF NOT EXISTS FOR (cf:Conflict) ON (cf.id)",
        "CREATE INDEX IF NOT EXISTS FOR (cf:Conflict) ON (cf.status)",
        "CREATE INDEX IF NOT EXISTS FOR (cf:Conflict) ON (cf.field)",
        # ResearchTask indexes
        "CREATE INDEX IF NOT EXISTS FOR (rt:ResearchTask) ON (rt.id)",
        "CREATE INDEX IF NOT EXISTS FOR (rt:ResearchTask) ON (rt.status)",
        "CREATE INDEX IF NOT EXISTS FOR (rt:ResearchTask) ON (rt.priority)",
    ]

    with driver.session() as session:
        for idx in indexes:
            session.run(idx)
            print(f"  Created: {idx.split('FOR')[1].strip() if 'FOR' in idx else idx}")

    # Add Conclusion label to all Individual nodes
    with driver.session() as session:
        result = session.run("""
            MATCH (i:Individual)
            WHERE NOT i:Conclusion
            SET i:Conclusion
            RETURN count(i) AS count
        """)
        count = result.single()["count"]
        print(f"\n  Added :Conclusion label to {count} Individual nodes")

    driver.close()
    print(f"\nEvidence schema seeded ({len(indexes)} indexes created)")


if __name__ == "__main__":
    main()
