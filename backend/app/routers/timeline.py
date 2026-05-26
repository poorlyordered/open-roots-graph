from fastapi import APIRouter, Query

from app.dependencies import get_driver
from app.repositories.timeline_repo import TimelineRepository

router = APIRouter(prefix="/api/timeline", tags=["timeline"])


@router.get("/events")
def get_events(
    surname: str | None = None,
    location: str | None = None,
    year_start: int | None = None,
    year_end: int | None = None,
    event_types: str | None = None,
    limit: int = Query(default=500, le=2000),
    offset: int = Query(default=0, ge=0),
):
    repo = TimelineRepository(get_driver())
    types = event_types.split(",") if event_types else None
    events, total = repo.get_events(
        surname=surname, location=location,
        year_start=year_start, year_end=year_end,
        event_types=types, limit=limit, offset=offset,
    )
    return {
        "success": True,
        "data": [e.model_dump() for e in events],
        "meta": {"total": total, "limit": limit, "offset": offset},
    }


@router.get("/filters")
def get_filters():
    repo = TimelineRepository(get_driver())
    return {"success": True, "data": repo.get_filters()}
