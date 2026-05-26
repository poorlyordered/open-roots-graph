from fastapi import APIRouter

from app.dependencies import get_driver
from app.models.place import PlaceListResponse
from app.repositories.place_repo import PlaceRepository

router = APIRouter(prefix="/api/places", tags=["places"])


@router.get("", response_model=PlaceListResponse)
def list_places(geocoded_only: bool = False, state: str | None = None):
    repo = PlaceRepository(get_driver())
    if state:
        places = repo.find_by_state(state)
    elif geocoded_only:
        places = repo.find_geocoded()
    else:
        places = repo.find_all()
    return PlaceListResponse(data=places)
