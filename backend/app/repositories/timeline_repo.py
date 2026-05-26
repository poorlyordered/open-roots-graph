from app.models.timeline import TimelineEvent
from app.repositories.base import BaseRepository


class TimelineRepository(BaseRepository):

    def get_events(
        self,
        surname: str | None = None,
        location: str | None = None,
        year_start: int | None = None,
        year_end: int | None = None,
        event_types: list[str] | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> tuple[list[TimelineEvent], int]:
        allowed_types = event_types or ["birth", "death", "marriage", "residence"]
        queries = []
        params: dict = {}

        if "birth" in allowed_types:
            queries.append("""
                MATCH (i:Individual)
                OPTIONAL MATCH (i)-[:BORN_IN]->(p:Place)
                WHERE i.birth_year IS NOT NULL
                RETURN i.id AS individual_id, i.name AS name, i.surname AS surname,
                       i.sex AS sex, 'birth' AS event_type, i.birth_year AS year,
                       i.birth_date_raw AS date_raw, p.normalized AS place
            """)

        if "death" in allowed_types:
            queries.append("""
                MATCH (i:Individual)
                OPTIONAL MATCH (i)-[:DIED_IN]->(p:Place)
                WHERE i.death_year IS NOT NULL
                RETURN i.id AS individual_id, i.name AS name, i.surname AS surname,
                       i.sex AS sex, 'death' AS event_type, i.death_year AS year,
                       i.death_date_raw AS date_raw, p.normalized AS place
            """)

        if "marriage" in allowed_types:
            queries.append("""
                MATCH (i:Individual)-[:SPOUSE_IN]->(f:Family)
                WHERE f.marriage_year IS NOT NULL
                RETURN i.id AS individual_id, i.name AS name, i.surname AS surname,
                       i.sex AS sex, 'marriage' AS event_type, f.marriage_year AS year,
                       f.marriage_date_raw AS date_raw, f.marriage_place AS place
            """)

        if "residence" in allowed_types:
            queries.append("""
                MATCH (i:Individual)-[r:RESIDED_IN]->(p:Place)
                WHERE r.year IS NOT NULL
                RETURN i.id AS individual_id, i.name AS name, i.surname AS surname,
                       i.sex AS sex, 'residence' AS event_type, r.year AS year,
                       r.date_raw AS date_raw, p.normalized AS place
            """)

        if not queries:
            return [], 0

        union_query = " UNION ALL ".join(queries)

        # Apply filters in a wrapping query
        filters = []
        if surname:
            filters.append("surname = $surname")
            params["surname"] = surname
        if location:
            filters.append("place CONTAINS $location")
            params["location"] = location
        if year_start is not None:
            filters.append("year >= $year_start")
            params["year_start"] = year_start
        if year_end is not None:
            filters.append("year <= $year_end")
            params["year_end"] = year_end

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        wrapped = f"""
            CALL {{ {union_query} }}
            WITH individual_id, name, surname, sex, event_type, year, date_raw, place
            {where_clause}
            RETURN individual_id, name, surname, sex, event_type, year, date_raw, place
            ORDER BY year
        """

        # Count
        count_query = f"""
            CALL {{ {union_query} }}
            WITH individual_id, name, surname, sex, event_type, year, date_raw, place
            {where_clause}
            RETURN count(*) AS total
        """
        count_row = self._read_single(count_query, **params)
        total = count_row["total"] if count_row else 0

        # Fetch page
        params["limit"] = limit
        params["offset"] = offset
        rows = self._read(f"{wrapped} SKIP $offset LIMIT $limit", **params)

        events = [TimelineEvent(**dict(r)) for r in rows]
        return events, total

    def get_filters(self) -> dict:
        surname_rows = self._read("""
            MATCH (i:Individual)
            WHERE i.surname IS NOT NULL AND i.birth_year IS NOT NULL
            RETURN DISTINCT i.surname AS surname, count(*) AS cnt
            ORDER BY cnt DESC
            LIMIT 50
        """)
        surnames = [r["surname"] for r in surname_rows]

        location_rows = self._read("""
            MATCH (p:Place)
            WHERE p.state IS NOT NULL
            RETURN DISTINCT p.state AS location, count(*) AS cnt
            ORDER BY cnt DESC
            LIMIT 30
        """)
        locations = [r["location"] for r in location_rows]

        year_row = self._read_single("""
            MATCH (i:Individual)
            WHERE i.birth_year IS NOT NULL
            RETURN min(i.birth_year) AS year_min, max(i.birth_year) AS year_max
        """)

        return {
            "surnames": surnames,
            "locations": locations,
            "year_min": year_row["year_min"] if year_row else 1500,
            "year_max": year_row["year_max"] if year_row else 2020,
        }
