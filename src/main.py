import asyncio
from collections.abc import Callable, Coroutine
from multiprocessing import Process, Queue
from typing import Any

from src.core.connection.http import HttpConnector
from src.core.logging import setup_logging
from src.core.settings import get_settings
from src.core.types import DataQueue
from src.services.loader.exchange.binance import BinanceAPI
from src.services.loader.service import LoaderService
from src.services.writer.service import WriterService


def run_async_process(async_func: Callable[[Queue], Coroutine[Any, Any, None]], data_queue: DataQueue) -> None:
    asyncio.run(async_func(data_queue))


async def run_loader(data_queue: DataQueue) -> None:
    settings = get_settings()
    setup_logging(settings)

    http = HttpConnector()
    api = BinanceAPI(http, settings=settings)
    service = LoaderService(api=api, data_queue=data_queue, settings=settings)
    await service.run()

    await http.disconnect()


def run_writer(data_queue: DataQueue) -> None:
    settings = get_settings()
    setup_logging(settings)

    writer = WriterService(data_queue=data_queue, settings=settings)
    writer.run()


def main() -> None:
    data_queue: DataQueue = Queue()
    writer_process = Process(target=run_writer, args=(data_queue,))
    loader_process = Process(target=run_async_process, args=(run_loader, data_queue))
    try:
        writer_process.start()
        loader_process.start()
        loader_process.join()
        writer_process.join()
    except KeyboardInterrupt:
        pass
