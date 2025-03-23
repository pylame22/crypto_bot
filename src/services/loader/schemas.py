from dataclasses import dataclass

from src.core.enums import TradeTypeEnum
from src.core.types import ScaledPrice


@dataclass(slots=True)
class ExchangeInfoSchema:
    symbol: str
    tick_size: str


@dataclass(slots=True)
class DepthSchema:
    symbol: str
    last_update_id: int
    bids: dict[ScaledPrice, str]
    asks: dict[ScaledPrice, str]
    first_bid: ScaledPrice
    first_ask: ScaledPrice


@dataclass(slots=True)
class DepthEventSchema:
    symbol: str
    time: int
    first_update_id: int
    final_update_id: int
    last_final_update_id: int
    bids: dict[ScaledPrice, str]
    asks: dict[ScaledPrice, str]
    first_bid: ScaledPrice | None
    first_ask: ScaledPrice | None


@dataclass(slots=True)
class AggTradeEventSchema:
    symbol: str
    trade_type: TradeTypeEnum
    trade_id: int
    time: int
    price: ScaledPrice
    quantity: str
