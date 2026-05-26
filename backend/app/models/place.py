from pydantic import BaseModel


class Place(BaseModel):
    normalized: str
    city: str | None = None
    county: str | None = None
    state: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class PlaceListResponse(BaseModel):
    success: bool = True
    data: list[Place] = []
