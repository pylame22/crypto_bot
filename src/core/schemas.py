from dataclasses import dataclass


@dataclass(slots=True)
class DepthSchema:
    symbol: str
    last_update_id: int
    bids: dict[str, str]
    asks: dict[str, str]


@dataclass(slots=True)
class DepthEventSchema:
    symbol: str
    time: int
    first_update_id: int
    final_update_id: int
    last_final_update_id: int
    bids: dict[str, str]
    asks: dict[str, str]
