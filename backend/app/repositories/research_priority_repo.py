from app.repositories.base import BaseRepository


class ResearchPriorityRepository(BaseRepository):

    def get_direct_ancestors(self, root_id: str, max_generations: int = 20) -> dict[str, int]:
        """Return dict of {individual_id: generation_number} for direct ancestors."""
        max_generations = min(max(max_generations, 1), 30)
        # Walk CHILD_OF -> Family <- SPOUSE_IN chains
        rows = self._read(f"""
            MATCH (root:Individual {{id: $root_id}})
            MATCH path = (root)-[:CHILD_OF|SPOUSE_IN*1..{max_generations * 2}]->(n)
            WHERE n:Individual AND n.id <> $root_id
            WITH n, path,
                 reduce(gen = 0, r IN relationships(path) |
                   CASE WHEN type(r) = 'CHILD_OF' THEN gen + 1 ELSE gen END
                 ) AS generation
            RETURN DISTINCT n.id AS id, min(generation) AS generation
        """, root_id=root_id)

        result = {root_id: 0}
        for r in rows:
            result[r["id"]] = r["generation"]
        return result

    def get_collateral_relatives(self, direct_ids: list[str]) -> dict[str, dict]:
        """Find siblings and spouses of direct-line ancestors."""
        if not direct_ids:
            return {}

        # Siblings: share a Family via CHILD_OF
        sibling_rows = self._read("""
            UNWIND $ids AS did
            MATCH (d:Individual {id: did})-[:CHILD_OF]->(f:Family)<-[:CHILD_OF]-(sib:Individual)
            WHERE NOT sib.id IN $ids
            RETURN DISTINCT sib.id AS id, did AS related_to
        """, ids=direct_ids)

        # Spouses: share a Family via SPOUSE_IN
        spouse_rows = self._read("""
            UNWIND $ids AS did
            MATCH (d:Individual {id: did})-[:SPOUSE_IN]->(f:Family)<-[:SPOUSE_IN]-(sp:Individual)
            WHERE NOT sp.id IN $ids AND sp.id <> did
            RETURN DISTINCT sp.id AS id, did AS related_to
        """, ids=direct_ids)

        result = {}
        for r in sibling_rows:
            result[r["id"]] = {"related_to": r["related_to"], "relation": "sibling"}
        for r in spouse_rows:
            if r["id"] not in result:
                result[r["id"]] = {"related_to": r["related_to"], "relation": "spouse"}
        return result

    def get_completeness_data(self, individual_ids: list[str]) -> list[dict]:
        """Fetch completeness metadata for a batch of individuals."""
        if not individual_ids:
            return []

        return self._read("""
            UNWIND $ids AS pid
            MATCH (i:Individual {id: pid})
            OPTIONAL MATCH (i)-[:BORN_IN]->(bp:Place)
            OPTIONAL MATCH (i)-[:DIED_IN]->(dp:Place)
            OPTIONAL MATCH (i)-[:BURIED_IN]->(bup:Place)
            OPTIONAL MATCH (i)-[:CHILD_OF]->(parentFam:Family)
            WITH i, bp, dp, bup, parentFam
            OPTIONAL MATCH (i)-[:CITED_IN]->(src:Source)
            WITH i, bp, dp, bup, parentFam, count(DISTINCT src) AS source_count
            OPTIONAL MATCH (cf:Conflict)-[:REGARDING]->(i)
            RETURN i.id AS id, i.name AS name, i.surname AS surname, i.sex AS sex,
                   i.birth_year AS birth_year, i.birth_date_raw AS birth_date_raw,
                   i.death_year AS death_year, i.death_date_raw AS death_date_raw,
                   bp IS NOT NULL AS has_birth_place,
                   dp IS NOT NULL AS has_death_place,
                   bup IS NOT NULL AS has_burial_place,
                   parentFam IS NOT NULL AS has_parents,
                   source_count,
                   count(DISTINCT cf) AS conflict_count
        """, ids=individual_ids)

    def get_root_candidates(self, limit: int = 20) -> list[dict]:
        """Return individuals who make good root choices (most descendants)."""
        return self._read("""
            MATCH (i:Individual)-[:SPOUSE_IN]->(f:Family)<-[:CHILD_OF]-(child:Individual)
            WITH i, count(DISTINCT child) AS descendant_count
            WHERE descendant_count > 0
            RETURN i.id AS id, i.name AS name, i.surname AS surname,
                   i.birth_year AS birth_year, descendant_count
            ORDER BY descendant_count DESC
            LIMIT $limit
        """, limit=limit)
