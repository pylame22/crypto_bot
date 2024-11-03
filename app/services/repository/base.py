from collections.abc import Iterable
from typing import Any

from sqlalchemy import Executable, Row

from app.services.connection.database import DatabaseConnector


class BaseRepository:
    def __init__(self, database: DatabaseConnector) -> None:
        self._session = database.session

    async def _execute(self, query: Executable, params: Any = None) -> None:
        await self._session.execute(query, params)

    async def _fetch_all(self, query: Executable) -> Iterable[Row]:
        results = await self._session.execute(query)
        return results.fetchall()  # type: ignore[return-value]

    async def _fetch_one(self, query: Executable) -> Row | None:
        results = await self._session.execute(query)
        return results.fetchone()

    async def _fetch_val(self, query: Executable) -> Any:
        results = await self._session.execute(query)
        return results.scalar_one()
