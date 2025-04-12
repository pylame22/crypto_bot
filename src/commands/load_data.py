import asyncio
from collections.abc import Callable, Coroutine
from multiprocessing import Process, Queue
from typing import Any

from src.core.commands import BaseCommand
from src.core.connection.http import HttpConnector
from src.core.logging import setup_logging
from src.schemas.load_data import LoadDataQueue
from src.services.load_data import LoaderService, WriterService
from src.services.load_data.exchange import BinanceAPI


class LoadDataCommand(BaseCommand):
    def _run_async_process(
        self,
        async_func: Callable[[Queue], Coroutine[Any, Any, None]],
        data_queue: LoadDataQueue,
    ) -> None:
        asyncio.run(async_func(data_queue))

    async def _run_loader(self, data_queue: LoadDataQueue) -> None:
        setup_logging(self._settings)

        http = HttpConnector()
        api = BinanceAPI(http, settings=self._settings)
        service = LoaderService(api=api, data_queue=data_queue, settings=self._settings)
        await service.run()

        await http.disconnect()

    def _run_writer(self, data_queue: LoadDataQueue) -> None:
        setup_logging(self._settings)
        self._settings.data_dir.mkdir(parents=True, exist_ok=True)

        writer = WriterService(data_queue=data_queue, settings=self._settings)
        writer.run()

    def execute(self) -> None:
        data_queue: LoadDataQueue = Queue()
        writer_process = Process(target=self._run_writer, args=(data_queue,))
        loader_process = Process(target=self._run_async_process, args=(self._run_loader, data_queue))
        try:
            writer_process.start()
            loader_process.start()
            loader_process.join()
            writer_process.join()
        except KeyboardInterrupt:
            pass
