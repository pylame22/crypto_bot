import asyncio
import logging
from collections.abc import Coroutine
from typing import Any


def create_safe_task(coro: Coroutine[Any, Any, Any], *, logger: logging.Logger) -> asyncio.Task:
    async def _wrapper() -> None:
        try:
            await coro
        except asyncio.CancelledError:
            logger.info("task %s was cancelled.", coro.__name__)
            raise
        except Exception:
            logger.exception("unhandled exception")
            raise

    return asyncio.create_task(_wrapper())
