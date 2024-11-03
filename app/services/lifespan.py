import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from app.core.settings import Settings, get_settings
from app.services.connection.database import DatabaseConnector
from app.services.database.models import BaseTable

from .connection import HttpConnector


@dataclass
class LifeSpanContext:
    settings: Settings
    http: HttpConnector
    database: DatabaseConnector


@asynccontextmanager
async def lifespan_context() -> AsyncIterator[LifeSpanContext]:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    http = HttpConnector()
    database = DatabaseConnector(settings)
    await database.init_tables(BaseTable.metadata)

    yield LifeSpanContext(settings=settings, http=http, database=database)

    await http.disconnect()
    await database.disconnect()
