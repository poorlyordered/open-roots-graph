from fastapi import APIRouter, Query

from app.dependencies import get_driver
from app.models.individual import IndividualListResponse, IndividualDetailResponse
from app.repositories.individual_repo import IndividualRepository

router = APIRouter(prefix="/api/individuals", tags=["individuals"])


@router.get("", response_model=IndividualListResponse)
def list_individuals(
    surname: str | None = None,
    search: str | None = None,
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
):
    repo = IndividualRepository(get_driver())
    individuals, total = repo.find_all(
        surname=surname, search=search, limit=limit, offset=offset
    )
    return IndividualListResponse(
        data=individuals,
        meta={"total": total, "limit": limit, "offset": offset},
    )


@router.get("/{indi_id}", response_model=IndividualDetailResponse)
def get_individual(indi_id: str):
    repo = IndividualRepository(get_driver())
    detail = repo.find_by_id(indi_id)
    if not detail:
        return IndividualDetailResponse(success=False, error="Individual not found")
    return IndividualDetailResponse(data=detail)


@router.get("/{indi_id}/ancestors", response_model=IndividualListResponse)
def get_ancestors(indi_id: str, depth: int = Query(default=10, le=20)):
    repo = IndividualRepository(get_driver())
    ancestors = repo.find_ancestors(indi_id, depth=depth)
    return IndividualListResponse(
        data=ancestors,
        meta={"total": len(ancestors), "limit": len(ancestors), "offset": 0},
    )
