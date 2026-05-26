from pydantic import BaseModel


class QualityScoreItem(BaseModel):
    id: str
    name: str
    surname: str | None = None
    sex: str | None = None
    birth_year: int | None = None
    death_year: int | None = None
    completeness_pct: float
    missing_fields: list[str]
    missing_count: int
    source_count: int
    conflict_count: int
    priority_score: float
    is_brick_wall: bool


class QualitySummary(BaseModel):
    total_individuals: int
    avg_completeness: float
    fully_complete: int
    unsourced_count: int
    quick_win_count: int
    completeness_by_field: dict[str, float]


class QualityScoresResponse(BaseModel):
    success: bool = True
    data: list[QualityScoreItem] = []
    summary: QualitySummary | None = None
    meta: dict = {}
