import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from .connection import HttpConnector
from .connection.database import DatabaseConnector
from .database.models import BaseTable
from .enums import RunTypeEnum
from .settings import Settings, get_settings


@dataclass
class LifeSpanContext:
    settings: Settings
    http: HttpConnector
    database: DatabaseConnector


@asynccontextmanager
async def lifespan_context() -> AsyncIterator[LifeSpanContext]:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(message)s")
    settings = get_settings()
    http = HttpConnector()
    database = DatabaseConnector(settings)
    if settings.type == RunTypeEnum.PROD:
        await database.init_tables(BaseTable.metadata)

    yield LifeSpanContext(settings=settings, http=http, database=database)

    await http.disconnect()
    await database.disconnect()
