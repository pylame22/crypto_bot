import asyncio
import logging
import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.core.lifespan import LifeSpanContext
from src.services.exchange.binance import BinanceAPI
from src.services.repository.depth import DepthRepository

if TYPE_CHECKING:
    from src.core.schemas import DepthChangeSchema, DepthSchema


@dataclass
class DepthParams:
    ws_speed: int
    depth_limit: int


class DepthService:
    __slots__ = (
        "_logger",
        "_symbols",
        "_params",
        "_loop",
        "_api",
        "_repo",
        "_filtered_symbol_events_map",
        "_prev_final_update_ids_map",
        "_depth_events",
        "_depth_results",
    )

    def __init__(self, symbols: Iterable[str], *, params: DepthParams, context: LifeSpanContext) -> None:
        self._logger = logging.getLogger(__name__)
        self._symbols = symbols
        self._params = params
        self._loop = asyncio.get_running_loop()
        self._api = BinanceAPI(context)
        self._repo = DepthRepository(context.database)

        self._filtered_symbol_events_map: dict[str, bool] = {}
        self._prev_final_update_ids_map: dict[str, int] = {}
        self._depth_events: dict[str, dict[int, DepthChangeSchema]] = {}
        self._depth_results: dict[str, DepthSchema] = {}

    def _reset(self) -> None:
        self._filtered_symbol_events_map.clear()
        self._prev_final_update_ids_map.clear()
        self._depth_events.clear()
        self._depth_results.clear()

    def _update_depth_results(self, symbol: str) -> None:
        bids = self._depth_results[symbol].bids
        asks = self._depth_results[symbol].asks
        for depth_event in self._depth_events[symbol].values():
            bids.update(depth_event.bids)
            asks.update(depth_event.asks)

        self._depth_results[symbol].bids = {price: qty for price, qty in bids.items() if qty not in ("0.0", "0")}
        self._depth_results[symbol].asks = {price: qty for price, qty in asks.items() if qty not in ("0.0", "0")}
        self._depth_events[symbol].clear()

    def _filter_depth_events(self, symbol: str) -> None:
        last_update_id = self._depth_results[symbol].last_update_id
        self._depth_events[symbol] = {
            final_update_id: data
            for final_update_id, data in self._depth_events[symbol].items()
            if final_update_id >= last_update_id
        }

    def _validate_final_id(self, symbol: str, last_final_update_id: int) -> bool:
        if prev_final_update_id := self._prev_final_update_ids_map.get(symbol):
            return prev_final_update_id == last_final_update_id
        return True

    def _validate_first_event(self, symbol: str) -> bool:
        first_event = next(iter(self._depth_events[symbol].values()))
        return first_event.first_update_id <= self._depth_results[symbol].last_update_id <= first_event.final_update_id

    async def _listen_depth(self, depth_available: asyncio.Event) -> None:
        async for data in self._api.listen_depth(self._symbols, self._params.ws_speed):
            start_time = time.time()
            self._depth_events.setdefault(data.symbol, {})[data.final_update_id] = data
            is_depth_available = depth_available.is_set()
            if is_depth_available and self._depth_results:
                if not self._filtered_symbol_events_map.get(data.symbol):
                    self._filter_depth_events(data.symbol)
                    self._filtered_symbol_events_map[data.symbol] = True
                    if not self._validate_first_event(data.symbol):
                        self._reset()
                        break
                if not self._validate_final_id(data.symbol, data.last_final_update_id):
                    self._reset()
                    break
                self._prev_final_update_ids_map[data.symbol] = data.final_update_id
                self._update_depth_results(data.symbol)
                await self._repo.create_depth_snapshot(self._depth_results[data.symbol], data.time)
            elif not is_depth_available and self._depth_events.keys() == set(self._symbols):
                depth_available.set()
            self._logger.info("listen_depth %s seconds", time.time() - start_time)

    async def run(self) -> None:
        while True:
            depth_available = asyncio.Event()
            task = self._loop.create_task(self._listen_depth(depth_available))
            await depth_available.wait()
            tasks = (self._api.get_depth(symbol, self._params.ws_speed) for symbol in self._symbols)
            depth_symbols: list[DepthSchema] = await asyncio.gather(*tasks)
            await asyncio.sleep(1)
            self._depth_results = {depth_symbol.symbol: depth_symbol for depth_symbol in depth_symbols}
            await task
