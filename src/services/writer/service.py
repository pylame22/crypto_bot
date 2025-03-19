import logging
from datetime import UTC, datetime
from io import BufferedWriter
from queue import Empty

import msgpack  # type: ignore [import-untyped]

from src.core.settings import Settings
from src.core.types import DataQueue, DictStrAny


class WriterService:
    def __init__(self, *, data_queue: DataQueue, settings: Settings) -> None:
        self._logger = logging.getLogger()
        self._data_queue = data_queue
        self._settings = settings
        self._current_hour = self._get_utc_hour()
        self._file = self._create_file()

    @staticmethod
    def _get_utc_hour() -> str:
        utc_now = datetime.now(UTC)
        return utc_now.strftime("%Y-%m-%dT%H")

    def _create_file(self) -> BufferedWriter:
        file_name = f"{self._current_hour}.msgpack"
        file_path = self._settings.data_dir / file_name
        return file_path.open("ab")

    def _check_rotation(self) -> None:
        current_hour = self._get_utc_hour()
        if current_hour != self._current_hour:
            self._file.close()
            self._current_hour = current_hour
            self._file = self._create_file()

    def _write(self, data: DictStrAny) -> None:
        self._check_rotation()
        packed = msgpack.packb(data, default=str)
        self._file.write(packed)
        self._file.flush()

    def _close(self) -> None:
        self._file.close()

    def run(self) -> None:
        try:
            while True:
                try:
                    data = self._data_queue.get(timeout=1)
                    if data is None:
                        break
                    self._write(data)
                except Empty:
                    continue
                except KeyboardInterrupt:
                    pass
                except Exception as e:  # noqa: BLE001
                    msg = f"Error writing data: {e}"
                    self._logger.error(msg)
        finally:
            self._logger.info("closing writer")
            self._close()
