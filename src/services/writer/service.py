import logging
from queue import Empty

from src.core.enums import DataTypeEnum
from src.core.settings import Settings
from src.core.types import DataQueue
from src.services.writer.file_writer import FileWriter


class WriterService:
    def __init__(self, *, data_queue: DataQueue, settings: Settings) -> None:
        self._logger = logging.getLogger()
        self._data_queue = data_queue
        self._settings = settings

    def run(self) -> None:
        depth_writer = FileWriter.create(self._settings.data_dir / DataTypeEnum.DEPTH)
        agg_trade_writer = FileWriter.create(self._settings.data_dir / DataTypeEnum.AGG_TRADE)
        try:
            while True:
                try:
                    data = self._data_queue.get(timeout=1)
                    if data is None:
                        break
                    data_type = data.pop("e")
                    if data_type == DataTypeEnum.DEPTH:
                        depth_writer.write(data)
                    elif data_type == DataTypeEnum.AGG_TRADE:
                        agg_trade_writer.write(data)
                except Empty:
                    continue
                except KeyboardInterrupt:
                    pass
                except Exception as e:  # noqa: BLE001
                    msg = f"Error writing data: {e}"
                    self._logger.error(msg)
        finally:
            self._logger.info("Closing writer")
            depth_writer.close()
            agg_trade_writer.close()
