from collections.abc import Sequence
from typing import Any

from sqlalchemy import Executable, Row

from src.core.lifespan import LifeSpanContext


class BaseRepository:
    def __init__(self, context: LifeSpanContext) -> None:
        self._session = context.database.session

    async def _execute(self, query: Executable, params: Any = None) -> None:
        await self._session.execute(query, params)

    async def _fetch_all(self, query: Executable) -> Sequence[Row]:
        results = await self._session.execute(query)
        return results.fetchall()

    async def _fetch_one(self, query: Executable) -> Row | None:
        results = await self._session.execute(query)
        return results.fetchone()

    async def _fetch_val(self, query: Executable) -> Any:
        results = await self._session.execute(query)
        return results.scalar_one()
