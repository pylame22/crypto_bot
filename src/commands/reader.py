import logging

import msgpack  # type: ignore [import-untyped]

from src.core.enums import DataTypeEnum
from src.core.logging import setup_logging
from src.core.settings import get_settings  # type: ignore [import-untyped]


def main() -> None:
    logger = logging.getLogger()
    settings = get_settings()
    setup_logging(settings)
    for file in sorted((settings.data_dir / DataTypeEnum.DEPTH).iterdir()):
        with file.open("rb") as f:
            unpacker = msgpack.Unpacker(f, raw=False)
            for unpacked in unpacker:
                data = {
                    "s": unpacked["s"],
                    "t": unpacked["t"],
                    "b": len(unpacked["b"]),
                    "a": len(unpacked["a"]),
                }
                logger.info(data)

    for file in sorted((settings.data_dir / DataTypeEnum.AGG_TRADE).iterdir()):
        with file.open("rb") as f:
            unpacker = msgpack.Unpacker(f, raw=False)
            for unpacked in unpacker:
                logger.info(unpacked)


if __name__ == "__main__":
    main()
