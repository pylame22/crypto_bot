import logging

from src.core.enums import AppEnvEnum
from src.core.settings import Settings


def setup_logging(settings: Settings) -> None:
    logging_level = logging.INFO if settings.env == AppEnvEnum.PROD else logging.DEBUG
    logging.basicConfig(level=logging_level, format="%(asctime)s %(levelname)-5s %(message)s")
