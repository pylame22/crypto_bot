import asyncio
import logging
import time
from collections.abc import Coroutine, Iterator
from contextlib import contextmanager
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


@contextmanager
def check_speed(name: str, logger: logging.Logger) -> Iterator[None]:
    start_time = time.perf_counter()
    try:
        yield
    finally:
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        logger.info("%s: %.3e seconds", name, elapsed_time)
