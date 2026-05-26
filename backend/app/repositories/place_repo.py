from app.models.place import Place
from app.repositories.base import BaseRepository


class PlaceRepository(BaseRepository):

    def find_all(self) -> list[Place]:
        rows = self._read("""
            MATCH (p:Place)
            RETURN p
            ORDER BY p.normalized
        """)
        return [_to_place(r["p"]) for r in rows]

    def find_geocoded(self) -> list[Place]:
        rows = self._read("""
            MATCH (p:Place)
            WHERE p.latitude IS NOT NULL AND p.longitude IS NOT NULL
            RETURN p
            ORDER BY p.normalized
        """)
        return [_to_place(r["p"]) for r in rows]

    def find_by_state(self, state: str) -> list[Place]:
        rows = self._read("""
            MATCH (p:Place)
            WHERE p.state = $state
            RETURN p
            ORDER BY p.normalized
        """, state=state)
        return [_to_place(r["p"]) for r in rows]

    def update_coordinates(self, normalized: str, lat: float, lng: float, source: str):
        self._write("""
            MATCH (p:Place {normalized: $normalized})
            SET p.latitude = $lat, p.longitude = $lng, p.geocode_source = $source
        """, normalized=normalized, lat=lat, lng=lng, source=source)


def _to_place(node) -> Place:
    return Place(
        normalized=node["normalized"],
        city=node.get("city"),
        county=node.get("county"),
        state=node.get("state"),
        country=node.get("country"),
        latitude=node.get("latitude"),
        longitude=node.get("longitude"),
    )
