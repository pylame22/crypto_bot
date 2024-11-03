from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.settings import Settings

from .base import BaseConnector


class DatabaseConnector(BaseConnector):
    def __init__(self, settings: Settings) -> None:
        default_session_kwargs: dict[str, Any] = {"expire_on_commit": False}
        self._transactional_engine = create_async_engine(settings.postgres.dsn, echo=settings.postgres.echo)
        self._autocommit_engine = self._transactional_engine.execution_options(isolation_level="AUTOCOMMIT")
        self._transactional_session_maker = async_sessionmaker(self._transactional_engine, **default_session_kwargs)
        self._autocommit_session_maker = async_sessionmaker(self._autocommit_engine, **default_session_kwargs)
        self.session: AsyncSession = self._autocommit_session_maker()

    async def init_tables(self, metadata: MetaData) -> None:
        async with self._transactional_engine.begin() as conn:
            await conn.run_sync(metadata.drop_all)
            await conn.run_sync(metadata.create_all)

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[AsyncSession]:
        async with self._transactional_session_maker.begin() as session:
            yield session

    async def disconnect(self) -> None:
        await self.session.close()
        await self._transactional_engine.dispose()
        await self._autocommit_engine.dispose()
