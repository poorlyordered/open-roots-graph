"""
Run conflict detection on the graph.

Usage:
    python -m scripts.detect_conflicts
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from app.services.conflict_detection import ConflictDetector


def main():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    pw = os.getenv("NEO4J_PASSWORD", "changeme")

    driver = GraphDatabase.driver(uri, auth=(user, pw))

    # Clear existing conflicts and tasks (re-run safe)
    with driver.session() as session:
        result = session.run("MATCH (cf:Conflict) DETACH DELETE cf RETURN count(cf) AS count")
        print(f"Cleared {result.single()['count']} existing conflicts")
        result = session.run("MATCH (rt:ResearchTask) DETACH DELETE rt RETURN count(rt) AS count")
        print(f"Cleared {result.single()['count']} existing research tasks")

    detector = ConflictDetector(driver)
    detector.run_all_checks()

    driver.close()


if __name__ == "__main__":
    main()
