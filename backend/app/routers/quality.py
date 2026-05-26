from fastapi import APIRouter, Query
from typing import Literal

from app.dependencies import get_driver
from app.models.quality import QualityScoresResponse
from app.repositories.quality_repo import QualityRepository
from app.services.quality_scorer import QualityScorer

router = APIRouter(prefix="/api/quality", tags=["quality"])

# Cache scored data in memory (genealogy data changes infrequently)
_cached_result: tuple | None = None


def _invalidate_cache():
    global _cached_result
    _cached_result = None


def _get_scored():
    global _cached_result
    if _cached_result is not None:
        return _cached_result

    repo = QualityRepository(get_driver())
    scorer = QualityScorer()
    raw = repo.get_all_completeness_data()
    items, summary = scorer.score_all(raw)
    _cached_result = (items, summary)
    return items, summary


@router.get("/scores", response_model=QualityScoresResponse)
def get_quality_scores(
    sort_by: Literal[
        "completeness_pct", "priority_score", "name", "surname",
        "source_count", "conflict_count", "missing_count", "birth_year"
    ] = "priority_score",
    sort_dir: Literal["asc", "desc"] = "desc",
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
    max_missing: int | None = Query(default=None, ge=0, le=10),
    unsourced_only: bool = False,
    missing_field: str | None = None,
    search: str | None = None,
):
    items, summary = _get_scored()

    # Filter
    filtered = items
    if max_missing is not None:
        filtered = [i for i in filtered if i.missing_count == max_missing]
    if unsourced_only:
        filtered = [i for i in filtered if i.source_count == 0]
    if missing_field:
        filtered = [i for i in filtered if missing_field in i.missing_fields]
    if search:
        q = search.lower()
        filtered = [i for i in filtered if q in i.name.lower()]

    # Sort
    reverse = sort_dir == "desc"
    filtered.sort(
        key=lambda x: (getattr(x, sort_by) is None, getattr(x, sort_by, "")),
        reverse=reverse,
    )

    total = len(filtered)
    page = filtered[offset:offset + limit]

    return QualityScoresResponse(
        data=page,
        summary=summary,
        meta={"total": total, "limit": limit, "offset": offset},
    )


@router.post("/invalidate-cache")
def invalidate_cache():
    _invalidate_cache()
    return {"success": True}
