import asyncio
import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TypedDict

from src.core.enums import AppEnvEnum
from src.core.lifespan import LifeSpanContext
from src.core.schemas import DepthEventSchema
from src.core.utils import check_speed, create_safe_task
from src.services.exchange.base import BaseExchangeAPI
from src.services.repository.depth import DepthRepository


class _DepthEvent(TypedDict):
    time: int
    first_update_id: int
    final_update_id: int
    bids: dict[str, str]
    asks: dict[str, str]


class _DepthResult(TypedDict):
    last_update_id: int
    bids: dict[str, str]
    asks: dict[str, str]


@dataclass(slots=True)
class DepthParams:
    ws_speed: int
    depth_limit: int


@dataclass(slots=True)
class DepthData:
    filtered_symbol_events_map: dict[str, bool] = field(default_factory=dict)
    prev_final_update_ids_map: dict[str, int] = field(default_factory=dict)
    depth_events: dict[str, dict[int, _DepthEvent]] = field(default_factory=dict)
    depth_results: dict[str, _DepthResult] = field(default_factory=dict)

    def _update_depth(self, depth: dict[str, str], new_depth: dict[str, str]) -> None:
        for price, qty in new_depth.items():
            if qty == "0":
                depth.pop(price, None)
            else:
                depth[price] = qty

    def reset(self) -> None:
        self.filtered_symbol_events_map.clear()
        self.prev_final_update_ids_map.clear()
        self.depth_events.clear()
        self.depth_results.clear()

    def is_valid_final_id(self, symbol: str, last_final_update_id: int) -> bool:
        if prev_final_update_id := self.prev_final_update_ids_map.get(symbol):
            return prev_final_update_id == last_final_update_id
        return True

    def is_valid_first_event(self, symbol: str) -> bool:
        event = next(iter(self.depth_events[symbol].values()))
        return event["first_update_id"] <= self.depth_results[symbol]["last_update_id"] <= event["final_update_id"]

    def update_depth_events(self, data: DepthEventSchema) -> None:
        self.depth_events.setdefault(data.symbol, {})[data.final_update_id] = {
            "time": data.time,
            "first_update_id": data.first_update_id,
            "final_update_id": data.final_update_id,
            "bids": data.bids,
            "asks": data.asks,
        }

    def set_prev_final_update_id(self, symbol: str, final_update_id: int) -> None:
        self.prev_final_update_ids_map[symbol] = final_update_id

    def update_depth_results(self, symbol: str) -> None:
        for depth_event in self.depth_events[symbol].values():
            self._update_depth(self.depth_results[symbol]["bids"], depth_event["bids"])
            self._update_depth(self.depth_results[symbol]["asks"], depth_event["asks"])
        self.depth_events[symbol].clear()

    def filter_depth_events(self, symbol: str) -> None:
        last_update_id = self.depth_results[symbol]["last_update_id"]
        self.depth_events[symbol] = {
            final_update_id: data
            for final_update_id, data in self.depth_events[symbol].items()
            if final_update_id >= last_update_id
        }


class DepthService:
    def __init__(
        self,
        symbols: Iterable[str],
        params: DepthParams,
        *,
        api: BaseExchangeAPI,
        repo: DepthRepository,
        context: LifeSpanContext,
    ) -> None:
        self._logger = logging.getLogger(__name__)
        self._symbols = symbols
        self._params = params
        self._loop = asyncio.get_running_loop()
        self._api = api
        self._repo = repo
        self._context = context
        self._data = DepthData()

    def _save_to_db(self, symbol: str, time: int) -> None:
        if self._context.settings.env == AppEnvEnum.PROD:
            datetime_at = datetime.fromtimestamp(time / 1000, UTC)
            repo_coro = self._repo.create_depth_snapshot(
                symbol,
                bids=self._data.depth_results[symbol]["bids"].copy(),
                asks=self._data.depth_results[symbol]["asks"].copy(),
                datetime_at=datetime_at,
            )
            create_safe_task(repo_coro, logger=self._logger)
        else:
            create_safe_task(asyncio.sleep(0.1), logger=self._logger)

    def _calculate_depth(self, data: DepthEventSchema) -> None:
        if not self._data.filtered_symbol_events_map.get(data.symbol):
            self._data.filter_depth_events(data.symbol)
            self._data.filtered_symbol_events_map[data.symbol] = True
            if not self._data.is_valid_first_event(data.symbol):
                raise ValueError
        if not self._data.is_valid_final_id(data.symbol, data.last_final_update_id):
            raise ValueError
        self._data.set_prev_final_update_id(data.symbol, data.final_update_id)
        self._data.update_depth_results(data.symbol)
        self._save_to_db(data.symbol, data.time)

        self._logger.debug(len(self._data.depth_results[data.symbol]["asks"]))
        self._logger.debug(len(self._data.depth_results[data.symbol]["bids"]))

    async def _listen_depth(self, depth_available: asyncio.Event) -> None:
        async for data in self._api.listen_depth(self._symbols, self._params.ws_speed):
            with check_speed("calculate depth", self._logger):
                self._data.update_depth_events(data)
                is_depth_available = depth_available.is_set()
                if is_depth_available and self._data.depth_results:
                    try:
                        self._calculate_depth(data)
                    except ValueError:
                        self._data.reset()
                        break
                elif not is_depth_available and self._data.depth_events.keys() == set(self._symbols):
                    depth_available.set()

    async def run(self) -> None:
        while True:
            try:
                self._logger.info("start task")
                depth_available = asyncio.Event()
                task = create_safe_task(self._listen_depth(depth_available), logger=self._logger)
                await asyncio.wait_for(depth_available.wait(), timeout=10)
                tasks = (self._api.get_depth(symbol, self._params.depth_limit) for symbol in self._symbols)
                depth_symbols = await asyncio.gather(*tasks)
                self._data.depth_results = {
                    depth_symbol.symbol: {
                        "last_update_id": depth_symbol.last_update_id,
                        "bids": depth_symbol.bids,
                        "asks": depth_symbol.asks,
                    }
                    for depth_symbol in depth_symbols
                }
                await task
            except TimeoutError:
                self._logger.error("depth_available is not available... restart", exc_info=False)
                continue
            except asyncio.CancelledError:
                break
