"""
Migrate existing GEDCOM-imported data into the evidence layer.

For each Individual, creates Claims for every known property (name, birth, death, etc.)
and links them to Records derived from Source nodes.

Usage:
    python -m scripts.migrate_legacy_claims
"""

import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


def create_id():
    return str(uuid.uuid4())[:12]


def main():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    pw = os.getenv("NEO4J_PASSWORD", "changeme")

    driver = GraphDatabase.driver(uri, auth=(user, pw))
    stats = {"records": 0, "claims": 0, "links": 0}

    # Step 1: Create Record nodes from existing Sources
    print("Step 1: Creating Record nodes from Sources...")
    with driver.session() as session:
        result = session.run("""
            MATCH (s:Source)
            WHERE NOT EXISTS { MATCH (:Record)-[:FROM_SOURCE]->(s) }
            RETURN s.id AS id, s.title AS title, s.author AS author
        """)
        sources = list(result)

    with driver.session() as session:
        for src in sources:
            record_id = f"rec-{create_id()}"
            session.run("""
                MATCH (s:Source {id: $src_id})
                CREATE (r:Record {
                    id: $record_id,
                    record_type: 'ancestry_source',
                    title: $title,
                    created_at: datetime()
                })
                CREATE (r)-[:FROM_SOURCE]->(s)
            """, src_id=src["id"], record_id=record_id,
                 title=src["title"] or "Unknown Source")
            stats["records"] += 1

    print(f"  Created {stats['records']} Record nodes")

    # Step 2: Create a catch-all Record for GEDCOM import
    print("Step 2: Creating GEDCOM import record...")
    gedcom_record_id = f"rec-gedcom-import"
    with driver.session() as session:
        session.run("""
            MERGE (r:Record {id: $id})
            SET r.record_type = 'gedcom_import',
                r.title = 'GEDCOM Import',
                r.created_at = datetime()
        """, id=gedcom_record_id)

    # Step 3: Create Claims for each Individual
    print("Step 3: Creating Claims for all individuals...")
    with driver.session() as session:
        result = session.run("""
            MATCH (i:Individual)
            OPTIONAL MATCH (i)-[:BORN_IN]->(bp:Place)
            OPTIONAL MATCH (i)-[:DIED_IN]->(dp:Place)
            OPTIONAL MATCH (i)-[:BURIED_IN]->(bup:Place)
            RETURN i.id AS id, i.name AS name, i.given_name AS given_name,
                   i.surname AS surname, i.sex AS sex,
                   i.birth_date_raw AS birth_date, i.birth_year AS birth_year,
                   i.death_date_raw AS death_date, i.death_year AS death_year,
                   bp.normalized AS birth_place,
                   dp.normalized AS death_place,
                   bup.normalized AS burial_place
        """)
        individuals = list(result)

    print(f"  Processing {len(individuals)} individuals...")

    claim_batch = []
    for indi in individuals:
        indi_id = indi["id"]

        # Name claim
        if indi["name"] and indi["name"] != "Unknown":
            claim_batch.append({
                "claim_id": f"clm-{create_id()}",
                "indi_id": indi_id,
                "claim_type": "name",
                "value": indi["name"],
                "confidence": 0.8,
            })

        # Birth date claim
        if indi["birth_date"]:
            claim_batch.append({
                "claim_id": f"clm-{create_id()}",
                "indi_id": indi_id,
                "claim_type": "birth_date",
                "value": indi["birth_date"],
                "year": indi["birth_year"],
                "confidence": 0.7,
            })

        # Birth place claim
        if indi["birth_place"]:
            claim_batch.append({
                "claim_id": f"clm-{create_id()}",
                "indi_id": indi_id,
                "claim_type": "birth_place",
                "value": indi["birth_place"],
                "confidence": 0.7,
            })

        # Death date claim
        if indi["death_date"]:
            claim_batch.append({
                "claim_id": f"clm-{create_id()}",
                "indi_id": indi_id,
                "claim_type": "death_date",
                "value": indi["death_date"],
                "year": indi["death_year"],
                "confidence": 0.7,
            })

        # Death place claim
        if indi["death_place"]:
            claim_batch.append({
                "claim_id": f"clm-{create_id()}",
                "indi_id": indi_id,
                "claim_type": "death_place",
                "value": indi["death_place"],
                "confidence": 0.7,
            })

        # Burial place claim
        if indi["burial_place"]:
            claim_batch.append({
                "claim_id": f"clm-{create_id()}",
                "indi_id": indi_id,
                "claim_type": "burial_place",
                "value": indi["burial_place"],
                "confidence": 0.6,
            })

    # Batch insert claims
    with driver.session() as session:
        for claim in claim_batch:
            session.run("""
                MATCH (i:Individual {id: $indi_id})
                MATCH (r:Record {id: $record_id})
                CREATE (c:Claim {
                    id: $claim_id,
                    claim_type: $claim_type,
                    value: $value,
                    confidence: $confidence,
                    status: 'accepted',
                    extracted_by: 'gedcom_import',
                    created_at: datetime()
                })
                CREATE (c)-[:ABOUT]->(i)
                CREATE (c)-[:EXTRACTED_FROM]->(r)
            """,
                indi_id=claim["indi_id"],
                record_id=gedcom_record_id,
                claim_id=claim["claim_id"],
                claim_type=claim["claim_type"],
                value=claim["value"],
                confidence=claim["confidence"],
            )
            stats["claims"] += 1

            if stats["claims"] % 500 == 0:
                print(f"    Claims created: {stats['claims']}...")

    print(f"  Created {stats['claims']} Claims")

    # Step 4: Link Claims to Place nodes where applicable
    print("Step 4: Linking place claims to Place nodes...")
    with driver.session() as session:
        result = session.run("""
            MATCH (c:Claim)
            WHERE c.claim_type IN ['birth_place', 'death_place', 'burial_place']
            MATCH (p:Place {normalized: c.value})
            WHERE NOT EXISTS { MATCH (c)-[:ASSERTS_PLACE]->(p) }
            CREATE (c)-[:ASSERTS_PLACE]->(p)
            RETURN count(*) AS count
        """)
        place_links = result.single()["count"]
        stats["links"] = place_links

    print(f"  Created {place_links} ASSERTS_PLACE links")

    # Summary
    driver.close()
    print(f"\n--- Migration Complete ---")
    print(f"  Records: {stats['records']}")
    print(f"  Claims: {stats['claims']}")
    print(f"  Place links: {stats['links']}")


if __name__ == "__main__":
    main()
