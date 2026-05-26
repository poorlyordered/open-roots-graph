from neo4j import Driver


class BaseRepository:
    def __init__(self, driver: Driver):
        self._driver = driver

    def _read(self, query: str, **params):
        with self._driver.session() as session:
            result = session.execute_read(
                lambda tx: [dict(record) for record in tx.run(query, **params)]
            )
            return result

    def _read_single(self, query: str, **params):
        with self._driver.session() as session:
            result = session.execute_read(
                lambda tx: tx.run(query, **params).single()
            )
            return dict(result) if result else None

    def _write(self, query: str, **params):
        with self._driver.session() as session:
            return session.execute_write(
                lambda tx: tx.run(query, **params).consume()
            )
