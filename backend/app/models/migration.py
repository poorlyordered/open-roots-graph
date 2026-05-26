from pydantic import BaseModel


class GeoPoint(BaseModel):
    lat: float
    lng: float
    place: str
    year: int | None = None


class MigrationEvent(BaseModel):
    individual_id: str
    name: str
    surname: str | None = None
    birth_year: int | None = None
    death_year: int | None = None
    sex: str | None = None
    points: list[GeoPoint] = []


class FamilyLine(BaseModel):
    surname: str
    count: int
    color: str | None = None


class MigrationResponse(BaseModel):
    success: bool = True
    data: list[MigrationEvent] = []
    family_lines: list[FamilyLine] = []
