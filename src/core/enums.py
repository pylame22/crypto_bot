from enum import StrEnum, auto
from typing import Any


class AutoStrEnum(StrEnum):
    @staticmethod
    def _generate_next_value_(name: str, _: int, __: int, ___: list[Any]) -> str:
        return name.lower()

    def next_value(self) -> "AutoStrEnum":
        list_values: list[AutoStrEnum] = list(self.__class__)
        current_index = list_values.index(self)
        next_index = (current_index + 1) % len(list_values)
        return list_values[next_index]


class ExchangeEnum(AutoStrEnum):
    BINANCE = auto()
    OKX = auto()


class DepthTypeEnum(AutoStrEnum):
    BID = auto()
    ASK = auto()
