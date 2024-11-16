import asyncio
import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.core.enums import RunTypeEnum
from src.core.lifespan import LifeSpanContext
from src.core.schemas import DepthChangeSchema, DepthSchema
from src.core.utils import create_safe_task
from src.services.exchange.base import BaseExchangeAPI
from src.services.repository.depth import DepthRepository


@dataclass(slots=True)
class DepthParams:
    ws_speed: int
    depth_limit: int


@dataclass(slots=True)
class DepthData:
    filtered_symbol_events_map: dict[str, bool] = field(default_factory=dict)
    prev_final_update_ids_map: dict[str, int] = field(default_factory=dict)
    depth_events: dict[str, dict[int, DepthChangeSchema]] = field(default_factory=dict)
    depth_results: dict[str, DepthSchema] = field(default_factory=dict)

    def reset(self) -> None:
        self.filtered_symbol_events_map.clear()
        self.prev_final_update_ids_map.clear()
        self.depth_events.clear()
        self.depth_results.clear()

    def update_depth_events(self, data: DepthChangeSchema) -> None:
        self.depth_events.setdefault(data.symbol, {})[data.final_update_id] = data

    def set_prev_final_update_id(self, symbol: str, final_update_id: int) -> None:
        self.prev_final_update_ids_map[symbol] = final_update_id

    def update_depth_results(self, symbol: str) -> None:
        bids = self.depth_results[symbol].bids
        asks = self.depth_results[symbol].asks
        for depth_event in self.depth_events[symbol].values():
            bids.update(depth_event.bids)
            asks.update(depth_event.asks)

        self.depth_results[symbol].bids = {price: qty for price, qty in bids.items() if qty not in ("0.0", "0")}
        self.depth_results[symbol].asks = {price: qty for price, qty in asks.items() if qty not in ("0.0", "0")}
        self.depth_events[symbol].clear()

    def filter_depth_events(self, symbol: str) -> None:
        last_update_id = self.depth_results[symbol].last_update_id
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
        if self._context.settings.type == RunTypeEnum.PROD:
            datetime_at = datetime.fromtimestamp(time / 1000, UTC)
            repo_coro = self._repo.create_depth_snapshot(
                symbol,
                bids=self._data.depth_results[symbol].bids.copy(),
                asks=self._data.depth_results[symbol].asks.copy(),
                datetime_at=datetime_at,
            )
            create_safe_task(repo_coro, logger=self._logger)
        else:
            create_safe_task(asyncio.sleep(0.1), logger=self._logger)

    def _is_valid_final_id(self, symbol: str, last_final_update_id: int) -> bool:
        if prev_final_update_id := self._data.prev_final_update_ids_map.get(symbol):
            return prev_final_update_id == last_final_update_id
        return True

    def _is_valid_first_event(self, symbol: str) -> bool:
        first_event = next(iter(self._data.depth_events[symbol].values()))
        return (
            first_event.first_update_id
            <= self._data.depth_results[symbol].last_update_id
            <= first_event.final_update_id
        )

    async def _listen_depth(self, depth_available: asyncio.Event) -> None:
        async for data in self._api.listen_depth(self._symbols, self._params.ws_speed):
            self._logger.info("calculate depth")
            self._data.update_depth_events(data)
            is_depth_available = depth_available.is_set()
            if is_depth_available and self._data.depth_results:
                if not self._data.filtered_symbol_events_map.get(data.symbol):
                    self._data.filter_depth_events(data.symbol)
                    self._data.filtered_symbol_events_map[data.symbol] = True
                    if not self._is_valid_first_event(data.symbol):
                        self._data.reset()
                        break
                if not self._is_valid_final_id(data.symbol, data.last_final_update_id):
                    self._data.reset()
                    break
                self._data.set_prev_final_update_id(data.symbol, data.final_update_id)
                self._data.update_depth_results(data.symbol)
                self._save_to_db(data.symbol, data.time)
            elif not is_depth_available and self._data.depth_events.keys() == set(self._symbols):
                depth_available.set()

    async def run(self) -> None:
        while True:
            try:
                self._logger.info("start task")
                depth_available = asyncio.Event()
                task = create_safe_task(self._listen_depth(depth_available), logger=self._logger)
                await asyncio.wait_for(depth_available.wait(), timeout=10)
                tasks = (self._api.get_depth(symbol, self._params.ws_speed) for symbol in self._symbols)
                depth_symbols: list[DepthSchema] = await asyncio.gather(*tasks)
                self._data.depth_results = {depth_symbol.symbol: depth_symbol for depth_symbol in depth_symbols}
                await task
            except TimeoutError:
                self._logger.error("depth_available is not available... restart", exc_info=False)
                continue
            except asyncio.CancelledError:
                break
