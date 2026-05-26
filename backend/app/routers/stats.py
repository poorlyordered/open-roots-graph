from fastapi import APIRouter

from app.dependencies import get_driver
from app.repositories.base import BaseRepository

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/dashboard")
def get_dashboard_stats():
    repo = BaseRepository(get_driver())

    counts = repo._read_single("""
        MATCH (i:Individual) WITH count(i) AS individuals
        MATCH (f:Family) WITH individuals, count(f) AS families
        MATCH (p:Place) WITH individuals, families, count(p) AS places
        OPTIONAL MATCH (gp:Place) WHERE gp.latitude IS NOT NULL
        RETURN individuals, families, places, count(gp) AS geocoded
    """)

    surname_rows = repo._read("""
        MATCH (i:Individual)
        WHERE i.surname IS NOT NULL
        RETURN i.surname AS surname, count(*) AS count
        ORDER BY count DESC
        LIMIT 20
    """)

    birth_rows = repo._read("""
        MATCH (i:Individual)
        WHERE i.birth_year IS NOT NULL
        RETURN (i.birth_year / 10) * 10 AS decade, count(*) AS count
        ORDER BY decade
    """)

    death_rows = repo._read("""
        MATCH (i:Individual)
        WHERE i.death_year IS NOT NULL
        RETURN (i.death_year / 10) * 10 AS decade, count(*) AS count
        ORDER BY decade
    """)

    oldest = repo._read_single("""
        MATCH (i:Individual)
        WHERE i.birth_year IS NOT NULL
        RETURN i.name AS name, i.birth_year AS year
        ORDER BY i.birth_year ASC
        LIMIT 1
    """)

    most_recent = repo._read_single("""
        MATCH (i:Individual)
        WHERE i.birth_year IS NOT NULL
        RETURN i.name AS name, i.birth_year AS year
        ORDER BY i.birth_year DESC
        LIMIT 1
    """)

    return {
        "success": True,
        "data": {
            "individuals_count": counts["individuals"] if counts else 0,
            "families_count": counts["families"] if counts else 0,
            "places_count": counts["places"] if counts else 0,
            "geocoded_count": counts["geocoded"] if counts else 0,
            "surname_distribution": [
                {"surname": r["surname"], "count": r["count"]} for r in surname_rows
            ],
            "birth_decade_histogram": [
                {"decade": r["decade"], "count": r["count"]} for r in birth_rows
            ],
            "death_decade_histogram": [
                {"decade": r["decade"], "count": r["count"]} for r in death_rows
            ],
            "oldest_individual": dict(oldest) if oldest else None,
            "most_recent_individual": dict(most_recent) if most_recent else None,
        },
    }
