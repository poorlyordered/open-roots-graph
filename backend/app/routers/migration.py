from fastapi import APIRouter, Query

from app.dependencies import get_driver
from app.models.migration import MigrationResponse, FamilyLine
from app.repositories.migration_repo import MigrationRepository

router = APIRouter(prefix="/api/migration", tags=["migration"])


@router.get("/events", response_model=MigrationResponse)
def get_migration_events(
    surname: str | None = None,
    decade_start: int | None = Query(default=None),
    decade_end: int | None = Query(default=None),
):
    repo = MigrationRepository(get_driver())
    events = repo.get_migration_events(
        surname=surname, decade_start=decade_start, decade_end=decade_end
    )
    family_lines = repo.get_family_lines()
    return MigrationResponse(data=events, family_lines=family_lines)


@router.get("/family-lines", response_model=dict)
def get_family_lines():
    repo = MigrationRepository(get_driver())
    lines = repo.get_family_lines()
    return {"success": True, "data": lines}
