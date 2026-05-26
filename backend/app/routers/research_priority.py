from fastapi import APIRouter, Query

from app.dependencies import get_driver
from app.repositories.research_priority_repo import ResearchPriorityRepository
from app.services.priority_scorer import PriorityScorer

router = APIRouter(prefix="/api/research-priorities", tags=["research-priorities"])


@router.get("")
def get_priorities(
    root_id: str = Query(..., description="GEDCOM individual ID to start from"),
    max_generations: int = Query(default=20, ge=1, le=30),
    relationship: str = Query(default="all", pattern="^(all|direct|collateral)$"),
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
):
    repo = ResearchPriorityRepository(get_driver())
    scorer = PriorityScorer()

    # Get direct ancestors with generation numbers
    generation_map = repo.get_direct_ancestors(root_id, max_generations)
    direct_ids = list(generation_map.keys())

    # Get collateral relatives (siblings + spouses of direct line)
    collateral_map = repo.get_collateral_relatives(direct_ids)

    # Fetch completeness data for all individuals
    all_ids = direct_ids + list(collateral_map.keys())
    completeness_data = repo.get_completeness_data(all_ids)

    # Score everyone
    items, summary = scorer.score(completeness_data, generation_map, collateral_map)

    # Filter by relationship
    if relationship == "direct":
        items = [i for i in items if i.relationship == "direct"]
    elif relationship == "collateral":
        items = [i for i in items if i.relationship == "collateral"]

    total = len(items)
    page = items[offset : offset + limit]

    return {
        "success": True,
        "data": [i.model_dump() for i in page],
        "summary": summary.model_dump(),
        "meta": {"total": total, "limit": limit, "offset": offset},
    }


@router.get("/root-candidates")
def get_root_candidates(
    limit: int = Query(default=20, le=50),
):
    repo = ResearchPriorityRepository(get_driver())
    candidates = repo.get_root_candidates(limit)
    return {"success": True, "data": [dict(r) for r in candidates]}
