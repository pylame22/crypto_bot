from typing import Any

type DictStrAny = dict[str, Any]


class ScaledPrice:
    __slots__ = ("_scale", "_value")

    def __init__(self, value: int, scale: int) -> None:
        self._value = value
        self._scale = scale

    def __str__(self) -> str:
        return str(self._value / self._scale)

    def __repr__(self) -> str:
        return self.__str__()

    def __hash__(self) -> int:
        return self._value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ScaledPrice):
            return NotImplemented
        return self._value == other.value

    @classmethod
    def from_price_and_tick(cls, price: str, tick_size: str) -> "ScaledPrice":
        scale = int(1 / float(tick_size))
        value = int(float(price) * scale)
        return ScaledPrice(value, scale)

    @property
    def value(self) -> int:
        return self._value

    def get_next(self, multiplier: int) -> "ScaledPrice":
        return ScaledPrice(self._value + multiplier, self._scale)

    def is_next_ask_for_bid(self, ask: "ScaledPrice") -> bool:
        return self._value + 1 == ask._value  # noqa: SLF001
