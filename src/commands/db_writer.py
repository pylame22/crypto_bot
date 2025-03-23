import asyncio
import logging
from datetime import UTC, datetime

import asyncpg  # type: ignore [import-untyped]
import msgpack  # type: ignore [import-untyped]

from src.core.enums import DataTypeEnum
from src.core.logging import setup_logging
from src.core.settings import get_settings


async def run_depth() -> None:
    logger = logging.getLogger()
    settings = get_settings()
    setup_logging(settings)
    conn: asyncpg.Connection = await asyncpg.connect(
        user=settings.postgres.user,
        password=settings.postgres.password,
        database=settings.postgres.database,
        host=settings.postgres.host,
    )
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS depth(
            ccy text,
            type text,
            timestamp timestamp,
            price numeric,
            quantity numeric
        )
    """)
    await conn.execute("truncate table depth")
    for file in sorted((settings.data_dir / DataTypeEnum.DEPTH).iterdir()):
        with file.open("rb") as f:
            unpacker = msgpack.Unpacker(f, raw=False)
            msg = f"Processing {file.name}"
            logger.info(msg)
            for idx, unpacked in enumerate(unpacker):
                ccy = unpacked["s"]
                timestamp = datetime.fromtimestamp(unpacked["t"] / 1000, tz=UTC)
                data = []
                for price, quantity in unpacked["b"].items():
                    data.append((ccy, "bid", timestamp, price, quantity))
                for price, quantity in unpacked["a"].items():
                    data.append((ccy, "ask", timestamp, price, quantity))
                await conn.executemany(
                    """
                    INSERT INTO depth(ccy, type, timestamp, price, quantity)
                    VALUES ($1, $2, $3, $4, $5)
                """,
                    data,
                )
                msg = f"Processed item {idx} for {timestamp}"
                logger.info(msg)
    await conn.close()


async def run_agg_trade() -> None:
    logger = logging.getLogger()
    settings = get_settings()
    setup_logging(settings)
    conn: asyncpg.Connection = await asyncpg.connect(
        user=settings.postgres.user,
        password=settings.postgres.password,
        database=settings.postgres.database,
        host=settings.postgres.host,
    )
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS agg_trade(
            ccy text,
            type text,
            timestamp timestamp,
            price numeric,
            quantity numeric
        )
    """)
    await conn.execute("truncate table agg_trade")
    for file in sorted((settings.data_dir / DataTypeEnum.AGG_TRADE).iterdir()):
        with file.open("rb") as f:
            unpacker = msgpack.Unpacker(f, raw=False)
            msg = f"Processing {file.name}"
            logger.info(msg)
            for idx, unpacked in enumerate(unpacker):
                timestamp = datetime.fromtimestamp(unpacked["t"] / 1000, tz=UTC)
                await conn.execute(
                    """
                    INSERT INTO agg_trade(ccy, type, timestamp, price, quantity)
                    VALUES ($1, $2, $3, $4, $5)
                """,
                    unpacked["s"],
                    unpacked["m"],
                    timestamp,
                    unpacked["p"],
                    unpacked["q"],
                )
                msg = f"Processed item {idx} for {timestamp}"
                logger.info(msg)
    await conn.close()


if __name__ == "__main__":
    asyncio.run(run_depth())
