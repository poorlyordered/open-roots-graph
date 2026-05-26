from pydantic import BaseModel


class ResearchPriorityItem(BaseModel):
    id: str
    name: str
    surname: str | None = None
    sex: str | None = None
    birth_year: int | None = None
    death_year: int | None = None
    generation: int = 0
    relationship: str = "direct"  # "direct" or "collateral"
    completeness_score: float = 0.0
    priority_score: float = 0.0
    missing_fields: list[str] = []
    has_conflicts: bool = False
    conflict_count: int = 0
    source_count: int = 0
    is_brick_wall: bool = False
    confidence_label: str = "low"  # verified, high, medium, low
    confidence_value: float = 0.0  # 0.0 to 1.0
    keystone_score: float = 0.0  # how many branches they'd unlock


class ResearchPrioritySummary(BaseModel):
    total_scored: int = 0
    brick_walls: int = 0
    avg_completeness: float = 0.0
    direct_line_count: int = 0
    collateral_count: int = 0
