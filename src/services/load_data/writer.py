import logging
from datetime import UTC, datetime
from io import BufferedWriter
from pathlib import Path
from queue import Empty
from typing import Self

import msgpack  # type: ignore [import-untyped]

from src.core.enums import DataTypeEnum
from src.core.settings import Settings
from src.core.types import DictStrAny
from src.schemas.load_data import LoadDataQueue


class FileWriter:
    @staticmethod
    def _get_utc_hour() -> str:
        utc_now = datetime.now(UTC)
        return utc_now.strftime("%Y-%m-%dT%H")

    @classmethod
    def _create_file(cls, data_dir: Path, current_hour: str) -> BufferedWriter:
        file_path = data_dir / f"{current_hour}.msgpack"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        return file_path.open("ab")

    @classmethod
    def create(cls, data_dir: Path) -> Self:
        current_hour = cls._get_utc_hour()
        file = cls._create_file(data_dir, current_hour)
        return cls(file, data_dir=data_dir, current_hour=current_hour)

    def __init__(self, file: BufferedWriter, *, data_dir: Path, current_hour: str) -> None:
        self._file = file
        self._data_dir = data_dir
        self._current_hour = current_hour

    def _check_rotation(self) -> None:
        current_hour = self._get_utc_hour()
        if current_hour != self._current_hour:
            self._file.close()
            self._current_hour = current_hour
            self._file = self._create_file(self._data_dir, current_hour)

    def write(self, data: DictStrAny) -> None:
        self._check_rotation()
        packed = msgpack.packb(data, default=str)
        self._file.write(packed)
        self._file.flush()

    def close(self) -> None:
        self._file.close()


class WriterService:
    def __init__(self, *, data_queue: LoadDataQueue, settings: Settings) -> None:
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
                    msg = f"Writing data: {data_type}"
                    self._logger.info(msg)
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
