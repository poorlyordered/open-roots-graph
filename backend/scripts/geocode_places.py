"""
Batch geocode all Place nodes in Neo4j.

Reads each Place.normalized, geocodes it via Nominatim + cache + overrides,
and writes lat/lng back to the Place node.

Usage:
    python -m scripts.geocode_places
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from app.services.geocoding import GeocodingService


def main():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    pw = os.getenv("NEO4J_PASSWORD", "changeme")
    cache_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "geocode_cache.json")

    driver = GraphDatabase.driver(uri, auth=(user, pw))
    geocoder = GeocodingService(cache_path)

    # Fetch all places
    with driver.session() as session:
        result = session.run("""
            MATCH (p:Place)
            WHERE p.latitude IS NULL
            RETURN p.normalized AS normalized
            ORDER BY p.normalized
        """)
        places = [r["normalized"] for r in result]

    print(f"Found {len(places)} places to geocode")

    success = 0
    failed = 0
    skipped = 0

    for i, place in enumerate(places):
        coords = geocoder.geocode(place)
        if coords:
            lat, lng = coords
            with driver.session() as session:
                session.run("""
                    MATCH (p:Place {normalized: $normalized})
                    SET p.latitude = $lat, p.longitude = $lng, p.geocode_source = 'nominatim'
                """, normalized=place, lat=lat, lng=lng)
            success += 1
            status = f"({lat:.4f}, {lng:.4f})"
        else:
            failed += 1
            status = "FAILED"

        if (i + 1) % 25 == 0 or status == "FAILED":
            print(f"  [{i+1}/{len(places)}] {place}: {status}")

        # Save cache periodically
        if (i + 1) % 50 == 0:
            geocoder.save_cache()

    geocoder.save_cache()
    driver.close()

    print(f"\nDone: {success} geocoded, {failed} failed, {skipped} skipped")
    print(f"Success rate: {success / len(places) * 100:.1f}%" if places else "No places")


if __name__ == "__main__":
    main()
