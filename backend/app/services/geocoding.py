"""
Geocoding service using OpenStreetMap Nominatim (free, no API key).

Implements aggressive caching and rate-limiting (1 req/sec per Nominatim policy).
Falls back through a hierarchy: full address -> county+state -> state -> manual override.
"""

import json
import os
import time

import httpx

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "RootsGraph-Genealogy/0.1 (local research tool)"
RATE_LIMIT_SECONDS = 1.1

# Manual overrides for places Nominatim struggles with
MANUAL_OVERRIDES = {
    # Kentucky counties (using county seats)
    "Elliott, Kentucky, USA": (38.1115, -83.1005),
    "Elliott County, Kentucky, USA": (38.1115, -83.1005),
    "Morgan, Kentucky, USA": (37.9715, -83.2774),
    "Morgan County, Kentucky, USA": (37.9715, -83.2774),
    "Rowan, Kentucky, USA": (38.1961, -83.4299),
    "Rowan County, Kentucky, USA": (38.1961, -83.4299),
    "Fleming, Kentucky, USA": (38.4218, -83.7377),
    "Fleming County, Kentucky, USA": (38.4218, -83.7377),
    "Fleming Co., Ky.": (38.4218, -83.7377),
    "Bath, Kentucky, USA": (38.1325, -83.7427),
    "Bath County, Kentucky, USA": (38.1325, -83.7427),
    "Carter, Kentucky, USA": (38.3308, -83.0479),
    "Carter County, Kentucky, USA": (38.3308, -83.0479),
    "Lawrence, Kentucky, USA": (38.0564, -82.6313),
    "Lawrence County, Kentucky, USA": (38.0564, -82.6313),
    "Jay, Indiana, USA": (40.4372, -85.0008),
    "Jay County, Indiana, USA": (40.4372, -85.0008),
    "Delaware, Indiana, USA": (40.2271, -85.3955),
    "Delaware County, Indiana, USA": (40.2271, -85.3955),
    # States only
    "Kentucky, USA": (37.8393, -84.2700),
    "Kentucky": (37.8393, -84.2700),
    "Virginia, USA": (37.4316, -78.6569),
    "Virginia": (37.4316, -78.6569),
    "North Carolina": (35.7596, -79.0193),
    "North Carolina, USA": (35.7596, -79.0193),
    "Indiana, USA": (40.2672, -86.1349),
    "Massachusetts, USA": (42.4072, -71.3824),
    "Massachusetts": (42.4072, -71.3824),
    "USA": (39.8283, -98.5795),
    # Historical / abbreviated
    "New England, USA": (42.5, -71.5),
    "Suffolk, England": (52.1872, 1.0514),
    "England": (52.3555, -1.1743),
    "Ipswich, Suffolk, England": (52.0567, 1.1482),
}

# State centroids as final fallback
STATE_CENTROIDS = {
    "Kentucky": (37.8393, -84.2700),
    "Virginia": (37.4316, -78.6569),
    "Indiana": (40.2672, -86.1349),
    "Massachusetts": (42.4072, -71.3824),
    "Wisconsin": (43.7844, -88.7879),
    "Ohio": (40.4173, -82.9071),
    "Illinois": (40.6331, -89.3985),
    "Missouri": (37.9643, -91.8318),
    "North Carolina": (35.7596, -79.0193),
    "Pennsylvania": (41.2033, -77.1945),
    "Tennessee": (35.5175, -86.5804),
    "New York": (42.1657, -74.9481),
    "West Virginia": (38.5976, -80.4549),
    "Maryland": (39.0458, -76.6413),
    "Connecticut": (41.5978, -72.7554),
}


class GeocodingService:
    def __init__(self, cache_path: str):
        self.cache_path = cache_path
        self.cache = self._load_cache()
        self._last_request_time = 0.0

    def _load_cache(self) -> dict:
        if os.path.exists(self.cache_path):
            with open(self.cache_path, "r") as f:
                return json.load(f)
        return {}

    def save_cache(self):
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        with open(self.cache_path, "w") as f:
            json.dump(self.cache, f, indent=2)

    def geocode(self, place_str: str) -> tuple[float, float] | None:
        """Geocode a place string. Returns (lat, lng) or None."""
        if not place_str:
            return None

        # Check cache first
        if place_str in self.cache:
            cached = self.cache[place_str]
            if cached is None:
                return None
            return (cached[0], cached[1])

        # Check manual overrides
        if place_str in MANUAL_OVERRIDES:
            result = MANUAL_OVERRIDES[place_str]
            self.cache[place_str] = list(result)
            return result

        # Try Nominatim with full string
        result = self._nominatim_query(place_str)
        if result:
            self.cache[place_str] = list(result)
            return result

        # Fallback: try without the first component (city)
        parts = [p.strip() for p in place_str.split(",") if p.strip()]
        if len(parts) > 2:
            fallback = ", ".join(parts[1:])
            if fallback in MANUAL_OVERRIDES:
                result = MANUAL_OVERRIDES[fallback]
                self.cache[place_str] = list(result)
                return result
            result = self._nominatim_query(fallback)
            if result:
                self.cache[place_str] = list(result)
                return result

        # Fallback: state centroid
        for part in parts:
            if part in STATE_CENTROIDS:
                result = STATE_CENTROIDS[part]
                self.cache[place_str] = list(result)
                return result

        # Give up
        self.cache[place_str] = None
        return None

    def _nominatim_query(self, query: str) -> tuple[float, float] | None:
        """Query Nominatim with rate limiting."""
        elapsed = time.time() - self._last_request_time
        if elapsed < RATE_LIMIT_SECONDS:
            time.sleep(RATE_LIMIT_SECONDS - elapsed)

        try:
            self._last_request_time = time.time()
            response = httpx.get(
                NOMINATIM_URL,
                params={"q": query, "format": "json", "limit": 1},
                headers={"User-Agent": USER_AGENT},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            if data:
                return (float(data[0]["lat"]), float(data[0]["lon"]))
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
            print(f"  Geocode failed for '{query}': {e}")

        return None
