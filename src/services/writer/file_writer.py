from datetime import UTC, datetime
from io import BufferedWriter
from pathlib import Path
from typing import Self

import msgpack  # type: ignore [import-untyped]

from src.core.types import DictStrAny


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
