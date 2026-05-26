from __future__ import annotations

from pydantic import BaseModel


class PedigreeNode(BaseModel):
    id: str
    name: str
    surname: str | None = None
    sex: str | None = None
    birth_year: int | None = None
    death_year: int | None = None
    birth_place: str | None = None
    death_place: str | None = None
    generation: int = 0
    children: list[PedigreeNode] = []  # "children" in D3 tree = ancestors
