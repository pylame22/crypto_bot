import os
import re
from pathlib import Path

from dotenv import load_dotenv
from msgspec import Struct, yaml

BASE_DIR = Path(__file__).parents[2]


class _Postgres(Struct):
    host: str
    user: str
    name: str
    password: str
    echo: bool

    @property
    def dsn(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}/{self.name}"


class _OKXExchange(Struct):
    api_key: str
    secret_key: str
    passphraze: str


class _Exchanges(Struct):
    okx: _OKXExchange | None


class Settings(Struct):
    exchanges: _Exchanges
    postgres: _Postgres
    base_dir: Path = BASE_DIR


def get_settings() -> Settings:
    load_dotenv()
    with Path(f"{BASE_DIR}/config.yml").open() as stream:
        data = stream.read()
    for match in re.finditer(r"\${(?P<env_value>.*)}", data):
        data = data.replace(match.group(), os.environ[match.group("env_value")])
    return yaml.decode(data, type=Settings)
