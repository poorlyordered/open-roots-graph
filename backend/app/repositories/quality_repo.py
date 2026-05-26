from app.repositories.base import BaseRepository


class QualityRepository(BaseRepository):

    def get_all_completeness_data(self) -> list[dict]:
        """Fetch completeness metadata for ALL individuals."""
        return self._read("""
            MATCH (i:Individual)
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
        """)
