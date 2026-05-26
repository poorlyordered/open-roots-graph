from fastapi import APIRouter

from app.dependencies import get_driver
from app.repositories.base import BaseRepository

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("")
def get_graph_data():
    """Return full graph data for the D3 network visualization."""
    repo = BaseRepository(get_driver())

    nodes = []
    links = []

    # Individuals
    rows = repo._read("""
        MATCH (i:Individual)
        RETURN i.id AS id, i.name AS name, i.surname AS surname,
               i.sex AS sex, i.birth_year AS birth_year,
               i.death_year AS death_year, i.birth_date_raw AS birth_date,
               i.death_date_raw AS death_date
    """)
    for r in rows:
        sex = r["sex"] or "U"
        nodes.append({
            "id": r["id"],
            "name": r["name"] or "Unknown",
            "surname": r["surname"] or "",
            "sex": sex,
            "birth_year": r["birth_year"],
            "death_year": r["death_year"],
            "birth_date": r["birth_date"] or "",
            "death_date": r["death_date"] or "",
            "type": "individual",
            "group": 1 if sex == "M" else 2 if sex == "F" else 3,
        })

    node_ids = {n["id"] for n in nodes}

    # Families
    rows = repo._read("""
        MATCH (f:Family)
        RETURN f.id AS id, f.marriage_year AS marriage_year,
               f.marriage_place AS marriage_place
    """)
    for r in rows:
        label = "Marriage"
        if r["marriage_year"]:
            label += f" ({r['marriage_year']})"
        nodes.append({
            "id": r["id"],
            "label": label,
            "marriage_year": r["marriage_year"],
            "marriage_place": r["marriage_place"] or "",
            "type": "family",
            "group": 4,
        })
        node_ids.add(r["id"])

    # Spouse relationships
    rows = repo._read("""
        MATCH (i:Individual)-[r:SPOUSE_IN]->(f:Family)
        RETURN i.id AS source, f.id AS target, r.role AS role
    """)
    for r in rows:
        if r["source"] in node_ids and r["target"] in node_ids:
            links.append({
                "source": r["source"],
                "target": r["target"],
                "type": "SPOUSE_IN",
                "role": r["role"],
            })

    # Child relationships
    rows = repo._read("""
        MATCH (i:Individual)-[:CHILD_OF]->(f:Family)
        RETURN i.id AS source, f.id AS target
    """)
    for r in rows:
        if r["source"] in node_ids and r["target"] in node_ids:
            links.append({
                "source": r["source"],
                "target": r["target"],
                "type": "CHILD_OF",
            })

    return {"success": True, "nodes": nodes, "links": links}
