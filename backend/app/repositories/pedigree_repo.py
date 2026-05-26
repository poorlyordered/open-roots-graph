from app.models.pedigree import PedigreeNode
from app.repositories.base import BaseRepository


class PedigreeRepository(BaseRepository):

    def get_pedigree(self, indi_id: str, max_depth: int = 5) -> PedigreeNode | None:
        max_depth = min(max(max_depth, 1), 10)

        # Fetch root individual
        root_row = self._read_single("""
            MATCH (i:Individual {id: $id})
            OPTIONAL MATCH (i)-[:BORN_IN]->(bp:Place)
            OPTIONAL MATCH (i)-[:DIED_IN]->(dp:Place)
            RETURN i, bp.normalized AS birth_place, dp.normalized AS death_place
        """, id=indi_id)

        if not root_row:
            return None

        # Fetch all ancestors in one query using variable-length paths
        path_depth = max_depth * 2  # Each generation is CHILD_OF->Family + SPOUSE_IN<-Individual
        rows = self._read(f"""
            MATCH (root:Individual {{id: $id}})
            MATCH path = (root)-[:CHILD_OF|SPOUSE_IN*1..{path_depth}]->(n)
            WHERE n:Individual AND n.id <> $id
            WITH n, path,
                 reduce(gen = 0, r IN relationships(path) |
                   CASE WHEN type(r) = 'CHILD_OF' THEN gen + 1 ELSE gen END
                 ) AS generation
            WITH n, min(generation) AS generation
            WHERE generation <= $max_depth
            OPTIONAL MATCH (n)-[:BORN_IN]->(bp:Place)
            OPTIONAL MATCH (n)-[:DIED_IN]->(dp:Place)
            // Find which child this ancestor connects through
            OPTIONAL MATCH (child:Individual)-[:CHILD_OF]->(f:Family)<-[:SPOUSE_IN]-(n)
            WHERE child.id <> n.id
            RETURN n AS i, bp.normalized AS birth_place, dp.normalized AS death_place,
                   generation, collect(DISTINCT child.id) AS child_ids
        """, id=indi_id, max_depth=max_depth)

        # Build lookup: id -> (node, generation, child_ids)
        nodes_by_id: dict[str, tuple[PedigreeNode, list[str]]] = {}
        root = _node_from_row(root_row, generation=0)
        nodes_by_id[root.id] = (root, [])

        for row in rows:
            node = _node_from_row(row, generation=row["generation"])
            child_ids = row["child_ids"] or []
            nodes_by_id[node.id] = (node, child_ids)

        # Wire up parent-child relationships
        for node_id, (node, child_ids) in nodes_by_id.items():
            for child_id in child_ids:
                if child_id in nodes_by_id:
                    child_node = nodes_by_id[child_id][0]
                    if node not in child_node.children:
                        child_node.children.append(node)

        return root


def _node_from_row(row: dict, generation: int) -> PedigreeNode:
    n = row["i"]
    return PedigreeNode(
        id=n["id"],
        name=n.get("name", "Unknown"),
        surname=n.get("surname"),
        sex=n.get("sex"),
        birth_year=n.get("birth_year"),
        death_year=n.get("death_year"),
        birth_place=row.get("birth_place"),
        death_place=row.get("death_place"),
        generation=generation,
    )
