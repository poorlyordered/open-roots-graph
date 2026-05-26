from typing import Literal

from pydantic import BaseModel


class Claim(BaseModel):
    id: str
    claim_type: str
    value: str
    confidence: float
    status: str
    extracted_by: str | None = None
    individual_id: str | None = None
    individual_name: str | None = None
    record_title: str | None = None


class Conflict(BaseModel):
    id: str
    description: str
    field: str
    severity: str
    status: str
    resolution: str | None = None
    individuals: list[dict] = []


class ResearchTask(BaseModel):
    id: str
    title: str
    description: str
    priority: str
    status: str
    target_name: str | None = None
    target_id: str | None = None


class EvidenceSummary(BaseModel):
    total_claims: int
    total_conflicts: int
    open_conflicts: int
    total_tasks: int
    open_tasks: int
    claims_by_type: dict[str, int] = {}
    conflicts_by_severity: dict[str, int] = {}
    completeness: dict[str, float] = {}


class ConflictUpdate(BaseModel):
    status: Literal["open", "resolved", "deferred"]
    resolution: str | None = None


class ClaimUpdate(BaseModel):
    status: Literal["pending", "accepted", "rejected", "conflicted"] | None = None
    confidence: float | None = None


class TaskUpdate(BaseModel):
    status: Literal["todo", "in_progress", "done"]
