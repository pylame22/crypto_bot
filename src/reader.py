import logging

import msgpack  # type: ignore [import-untyped]

from src.core.logging import setup_logging
from src.core.settings import get_settings  # type: ignore [import-untyped]


def main() -> None:
    logger = logging.getLogger()
    settings = get_settings()
    setup_logging(settings)
    for file in settings.data_dir.glob("*.msgpack"):
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


if __name__ == "__main__":
    main()
