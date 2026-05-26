from app.models.individual import Individual, IndividualDetail
from app.repositories.base import BaseRepository


class IndividualRepository(BaseRepository):

    def find_all(
        self,
        surname: str | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Individual], int]:
        where_clauses = []
        params: dict = {"limit": limit, "offset": offset}

        if surname:
            where_clauses.append("i.surname = $surname")
            params["surname"] = surname
        if search:
            where_clauses.append("toLower(i.name) CONTAINS toLower($search)")
            params["search"] = search

        where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        count_row = self._read_single(
            f"MATCH (i:Individual) {where} RETURN count(i) AS total", **params
        )
        total = count_row["total"] if count_row else 0

        rows = self._read(f"""
            MATCH (i:Individual)
            {where}
            RETURN i
            ORDER BY i.surname, i.birth_year
            SKIP $offset LIMIT $limit
        """, **params)

        individuals = [_to_individual(r["i"]) for r in rows]
        return individuals, total

    def find_by_id(self, indi_id: str) -> IndividualDetail | None:
        row = self._read_single("""
            MATCH (i:Individual {id: $id})
            OPTIONAL MATCH (i)-[:BORN_IN]->(bp:Place)
            OPTIONAL MATCH (i)-[:DIED_IN]->(dp:Place)
            OPTIONAL MATCH (i)-[:BURIED_IN]->(bup:Place)
            RETURN i, bp.normalized AS birth_place,
                   dp.normalized AS death_place,
                   bup.normalized AS burial_place
        """, id=indi_id)

        if not row:
            return None

        node = row["i"]
        detail = IndividualDetail(
            id=node["id"],
            name=node.get("name", "Unknown"),
            given_name=node.get("given_name"),
            surname=node.get("surname"),
            sex=node.get("sex"),
            birth_date_raw=node.get("birth_date_raw"),
            birth_date_iso=node.get("birth_date_iso"),
            birth_year=node.get("birth_year"),
            death_date_raw=node.get("death_date_raw"),
            death_date_iso=node.get("death_date_iso"),
            death_year=node.get("death_year"),
            birth_place=row.get("birth_place"),
            death_place=row.get("death_place"),
            burial_place=row.get("burial_place"),
        )

        # Parents
        parents = self._read("""
            MATCH (i:Individual {id: $id})-[:CHILD_OF]->(f:Family)<-[:SPOUSE_IN]-(p:Individual)
            RETURN p
        """, id=indi_id)
        detail.parents = [_to_individual(r["p"]) for r in parents]

        # Spouses
        spouses = self._read("""
            MATCH (i:Individual {id: $id})-[:SPOUSE_IN]->(f:Family)<-[:SPOUSE_IN]-(s:Individual)
            WHERE s.id <> $id
            RETURN s
        """, id=indi_id)
        detail.spouses = [_to_individual(r["s"]) for r in spouses]

        # Children
        children = self._read("""
            MATCH (i:Individual {id: $id})-[:SPOUSE_IN]->(f:Family)<-[:CHILD_OF]-(c:Individual)
            RETURN DISTINCT c
            ORDER BY c.birth_year
        """, id=indi_id)
        detail.children = [_to_individual(r["c"]) for r in children]

        # Sources
        sources = self._read("""
            MATCH (i:Individual {id: $id})-[:CITED_IN]->(s:Source)
            RETURN s.title AS title
        """, id=indi_id)
        detail.sources = [r["title"] for r in sources if r["title"]]

        # Residences
        residences = self._read("""
            MATCH (i:Individual {id: $id})-[r:RESIDED_IN]->(p:Place)
            RETURN p.normalized AS place, r.year AS year, r.date_raw AS date_raw
            ORDER BY r.year
        """, id=indi_id)
        detail.residences = [dict(r) for r in residences]

        return detail

    def find_ancestors(self, indi_id: str, depth: int = 10) -> list[Individual]:
        depth = min(max(depth, 1), 20)
        rows = self._read(f"""
            MATCH (i:Individual {{id: $id}})
            MATCH path = (i)-[:CHILD_OF|SPOUSE_IN*1..{depth}]->(fam_or_indi)
            WITH nodes(path) AS ns
            UNWIND ns AS n
            WITH DISTINCT n
            WHERE n:Individual
            RETURN n AS i
            ORDER BY n.birth_year
        """, id=indi_id)
        return [_to_individual(r["i"]) for r in rows]


def _to_individual(node) -> Individual:
    return Individual(
        id=node["id"],
        name=node.get("name", "Unknown"),
        given_name=node.get("given_name"),
        surname=node.get("surname"),
        sex=node.get("sex"),
        birth_date_raw=node.get("birth_date_raw"),
        birth_date_iso=node.get("birth_date_iso"),
        birth_year=node.get("birth_year"),
        death_date_raw=node.get("death_date_raw"),
        death_date_iso=node.get("death_date_iso"),
        death_year=node.get("death_year"),
    )
