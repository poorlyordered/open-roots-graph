from fastapi import APIRouter, Query

from app.dependencies import get_driver
from app.repositories.pedigree_repo import PedigreeRepository

router = APIRouter(prefix="/api/pedigree", tags=["pedigree"])


@router.get("/{indi_id}")
def get_pedigree(
    indi_id: str,
    depth: int = Query(default=5, ge=1, le=10),
):
    repo = PedigreeRepository(get_driver())
    tree = repo.get_pedigree(indi_id, max_depth=depth)
    if tree is None:
        return {"success": False, "error": "Individual not found"}

    max_gen = _max_generation(tree)
    return {"success": True, "data": tree.model_dump(), "max_generation": max_gen}


def _max_generation(node) -> int:
    if not node.children:
        return node.generation
    return max(_max_generation(c) for c in node.children)
