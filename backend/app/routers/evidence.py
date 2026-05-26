from typing import Literal

from fastapi import APIRouter, Query

from app.dependencies import get_driver
from app.models.evidence import ClaimUpdate, ConflictUpdate, TaskUpdate
from app.repositories.evidence_repo import EvidenceRepository

router = APIRouter(prefix="/api/evidence", tags=["evidence"])


@router.get("/summary")
def get_evidence_summary():
    repo = EvidenceRepository(get_driver())
    summary = repo.get_summary()
    return {"success": True, "data": summary}


@router.get("/claims/{indi_id}")
def get_claims(indi_id: str):
    repo = EvidenceRepository(get_driver())
    claims = repo.get_claims_for_individual(indi_id)
    return {"success": True, "data": [c.model_dump() for c in claims]}


@router.patch("/claims/{claim_id}")
def update_claim(claim_id: str, body: ClaimUpdate):
    repo = EvidenceRepository(get_driver())
    repo.update_claim(claim_id, status=body.status, confidence=body.confidence)
    return {"success": True}


@router.get("/conflicts")
def get_conflicts(
    status: Literal["open", "resolved", "deferred"] | None = None,
    severity: Literal["critical", "high", "medium", "low"] | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
):
    repo = EvidenceRepository(get_driver())
    conflicts, total = repo.get_conflicts(
        status=status, severity=severity, limit=limit, offset=offset
    )
    return {
        "success": True,
        "data": [c.model_dump() for c in conflicts],
        "meta": {"total": total, "limit": limit, "offset": offset},
    }


@router.get("/conflicts/individual/{indi_id}")
def get_individual_conflicts(indi_id: str):
    repo = EvidenceRepository(get_driver())
    conflicts = repo.get_conflicts_for_individual(indi_id)
    return {"success": True, "data": [c.model_dump() for c in conflicts]}


@router.patch("/conflicts/{conflict_id}")
def update_conflict(conflict_id: str, body: ConflictUpdate):
    repo = EvidenceRepository(get_driver())
    repo.update_conflict(conflict_id, status=body.status, resolution=body.resolution)
    return {"success": True}


@router.get("/tasks")
def get_tasks(
    status: Literal["todo", "in_progress", "done"] | None = None,
    priority: Literal["critical", "high", "medium", "low"] | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
):
    repo = EvidenceRepository(get_driver())
    tasks, total = repo.get_tasks(
        status=status, priority=priority, limit=limit, offset=offset
    )
    return {
        "success": True,
        "data": [t.model_dump() for t in tasks],
        "meta": {"total": total, "limit": limit, "offset": offset},
    }


@router.patch("/tasks/{task_id}")
def update_task(task_id: str, body: TaskUpdate):
    repo = EvidenceRepository(get_driver())
    repo.update_task(task_id, status=body.status)
    return {"success": True}
