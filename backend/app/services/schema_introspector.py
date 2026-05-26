from neo4j import Driver


class SchemaIntrospector:
    def __init__(self, driver: Driver):
        self._driver = driver
        self._cached_schema: str | None = None

    def get_schema_prompt(self) -> str:
        if self._cached_schema is not None:
            return self._cached_schema

        schema_parts = []

        with self._driver.session() as session:
            # Node labels and their properties
            result = session.run(
                "CALL db.schema.nodeTypeProperties() "
                "YIELD nodeLabels, propertyName, propertyTypes "
                "RETURN nodeLabels, collect({name: propertyName, types: propertyTypes}) as props"
            )
            schema_parts.append("## Node Types\n")
            for record in result:
                labels = ":".join(record["nodeLabels"])
                props = record["props"]
                prop_list = ", ".join(
                    f"{p['name']}: {'/'.join(p['types'])}" for p in props if p["name"]
                )
                schema_parts.append(f"(:{labels}) — {prop_list}")

            # Relationship types and their properties
            result = session.run(
                "CALL db.schema.relTypeProperties() "
                "YIELD relType, propertyName, propertyTypes "
                "RETURN relType, collect({name: propertyName, types: propertyTypes}) as props"
            )
            schema_parts.append("\n## Relationship Types\n")
            for record in result:
                rel_type = record["relType"]
                props = record["props"]
                prop_list = ", ".join(
                    f"{p['name']}: {'/'.join(p['types'])}" for p in props if p["name"]
                )
                suffix = f" — {prop_list}" if prop_list else ""
                schema_parts.append(f"[:{rel_type}]{suffix}")

            # Counts for context
            result = session.run(
                "MATCH (n) RETURN labels(n)[0] as label, count(n) as cnt ORDER BY cnt DESC"
            )
            schema_parts.append("\n## Node Counts\n")
            for record in result:
                schema_parts.append(f"{record['label']}: {record['cnt']}")

            result = session.run(
                "MATCH ()-[r]->() RETURN type(r) as rel, count(r) as cnt ORDER BY cnt DESC"
            )
            schema_parts.append("\n## Relationship Counts\n")
            for record in result:
                schema_parts.append(f"{record['rel']}: {record['cnt']}")

        self._cached_schema = "\n".join(schema_parts)
        return self._cached_schema

    def refresh(self) -> None:
        self._cached_schema = None
