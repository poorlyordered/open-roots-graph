from app.models.migration import MigrationEvent, GeoPoint, FamilyLine
from app.repositories.base import BaseRepository


# Colors for the top family lines
FAMILY_COLORS = [
    "#4488ff", "#ff6688", "#44cc88", "#ffaa44", "#aa66ff",
    "#ff4444", "#44dddd", "#dddd44", "#ff88cc", "#88ff88",
    "#6688ff", "#ff8844", "#44ff88", "#dd44dd", "#88ccff",
]


class MigrationRepository(BaseRepository):

    def get_migration_events(
        self,
        surname: str | None = None,
        decade_start: int | None = None,
        decade_end: int | None = None,
    ) -> list[MigrationEvent]:
        where_clauses = []
        params: dict = {}

        if surname:
            where_clauses.append("i.surname = $surname")
            params["surname"] = surname
        if decade_start:
            where_clauses.append("i.birth_year >= $decade_start")
            params["decade_start"] = decade_start
        if decade_end:
            where_clauses.append("(i.birth_year <= $decade_end OR i.birth_year IS NULL)")
            params["decade_end"] = decade_end

        where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        rows = self._read(f"""
            MATCH (i:Individual)
            {where}
            OPTIONAL MATCH (i)-[:BORN_IN]->(bp:Place)
            WHERE bp.latitude IS NOT NULL
            OPTIONAL MATCH (i)-[res:RESIDED_IN]->(rp:Place)
            WHERE rp.latitude IS NOT NULL
            OPTIONAL MATCH (i)-[:DIED_IN]->(dp:Place)
            WHERE dp.latitude IS NOT NULL
            WITH i, bp, dp,
                 collect(DISTINCT {{
                     lat: rp.latitude, lng: rp.longitude,
                     place: rp.normalized, year: res.year
                 }}) AS residences
            WHERE bp IS NOT NULL OR dp IS NOT NULL OR size(residences) > 0
            RETURN i.id AS id, i.name AS name, i.surname AS surname,
                   i.birth_year AS birth_year, i.death_year AS death_year,
                   i.sex AS sex,
                   bp.latitude AS birth_lat, bp.longitude AS birth_lng,
                   bp.normalized AS birth_place, i.birth_year AS bp_year,
                   dp.latitude AS death_lat, dp.longitude AS death_lng,
                   dp.normalized AS death_place, i.death_year AS dp_year,
                   residences
            ORDER BY i.birth_year
        """, **params)

        events = []
        for r in rows:
            points = []

            if r["birth_lat"] is not None:
                points.append(GeoPoint(
                    lat=r["birth_lat"], lng=r["birth_lng"],
                    place=r["birth_place"], year=r["bp_year"],
                ))

            for res in r["residences"]:
                if res["lat"] is not None and res["lat"] != r.get("birth_lat"):
                    points.append(GeoPoint(
                        lat=res["lat"], lng=res["lng"],
                        place=res["place"], year=res["year"],
                    ))

            if r["death_lat"] is not None:
                points.append(GeoPoint(
                    lat=r["death_lat"], lng=r["death_lng"],
                    place=r["death_place"], year=r["dp_year"],
                ))

            # Sort by year
            points.sort(key=lambda p: p.year or 9999)

            if points:
                events.append(MigrationEvent(
                    individual_id=r["id"],
                    name=r["name"],
                    surname=r["surname"],
                    birth_year=r["birth_year"],
                    death_year=r["death_year"],
                    sex=r["sex"],
                    points=points,
                ))

        return events

    def get_family_lines(self) -> list[FamilyLine]:
        rows = self._read("""
            MATCH (i:Individual)-[:BORN_IN]->(p:Place)
            WHERE i.surname IS NOT NULL AND i.surname <> ''
              AND p.latitude IS NOT NULL
            RETURN i.surname AS surname, count(DISTINCT i) AS count
            ORDER BY count DESC
            LIMIT 20
        """)

        lines = []
        for idx, r in enumerate(rows):
            lines.append(FamilyLine(
                surname=r["surname"],
                count=r["count"],
                color=FAMILY_COLORS[idx % len(FAMILY_COLORS)],
            ))
        return lines
