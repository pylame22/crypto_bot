import os
import re
from pathlib import Path

from dotenv import load_dotenv
from msgspec import Struct, yaml

from src.core.enums import AppEnvEnum

BASE_DIR = Path(__file__).parents[2]


class _OKXExchange(Struct):
    api_key: str
    secret_key: str
    passphraze: str


class _Exchanges(Struct):
    okx: _OKXExchange | None


class _Loader(Struct):
    ws_speed: int
    depth_limit: int
    symbols: list[str]


class Settings(Struct):
    env: AppEnvEnum
    loader: _Loader
    exchanges: _Exchanges
    base_dir: Path = BASE_DIR
    data_dir: Path = BASE_DIR / "data"


def get_settings() -> Settings:
    load_dotenv()
    with Path(f"{BASE_DIR}/config.yml").open() as stream:
        data = stream.read()
    for match in re.finditer(r"\${(?P<env_value>.*)}", data):
        data = data.replace(match.group(), os.environ[match.group("env_value")])
    return yaml.decode(data, type=Settings)
