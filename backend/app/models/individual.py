from pydantic import BaseModel


class Individual(BaseModel):
    id: str
    name: str
    given_name: str | None = None
    surname: str | None = None
    sex: str | None = None
    birth_date_raw: str | None = None
    birth_date_iso: str | None = None
    birth_year: int | None = None
    death_date_raw: str | None = None
    death_date_iso: str | None = None
    death_year: int | None = None


class IndividualDetail(Individual):
    birth_place: str | None = None
    death_place: str | None = None
    burial_place: str | None = None
    parents: list["Individual"] = []
    spouses: list["Individual"] = []
    children: list["Individual"] = []
    sources: list[str] = []
    residences: list[dict] = []


class IndividualListResponse(BaseModel):
    success: bool = True
    data: list[Individual] = []
    meta: dict | None = None


class IndividualDetailResponse(BaseModel):
    success: bool = True
    data: IndividualDetail | None = None
    error: str | None = None
