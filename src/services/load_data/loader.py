import asyncio
import logging
from dataclasses import dataclass, field

from src.core.enums import DataTypeEnum
from src.core.settings import Settings
from src.core.utils import create_safe_task
from src.schemas.load_data import AggTradeEventSchema, DepthEventSchema, DepthSchema, ExchangeInfoSchema, LoadDataQueue

from .exchange import BaseExchangeAPI


@dataclass(slots=True)
class DepthData:
    filtered_symbol_events_map: dict[str, bool] = field(default_factory=dict)
    prev_final_update_ids_map: dict[str, int] = field(default_factory=dict)
    depth_events: dict[str, dict[int, DepthEventSchema]] = field(default_factory=dict)
    depth_results: dict[str, DepthSchema] = field(default_factory=dict)

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
        return event.first_update_id <= self.depth_results[symbol].last_update_id <= event.final_update_id

    def set_prev_final_update_id(self, symbol: str, final_update_id: int) -> None:
        self.prev_final_update_ids_map[symbol] = final_update_id

    def update_depth_results(self, symbol: str, depth_limit: int) -> None:
        depth_result = self.depth_results[symbol]
        for depth_event in self.depth_events[symbol].values():
            first_bid = depth_event.first_bid or depth_result.first_bid
            first_ask = depth_event.first_ask or depth_result.first_ask
            if first_bid.is_next_ask_for_bid(first_ask):
                depth_result.first_bid = first_bid
                depth_result.first_ask = first_ask
            new_bids, new_asks = {}, {}
            for tick_number in range(depth_limit):
                next_bid = depth_result.first_bid.get_next(-tick_number)
                next_ask = depth_result.first_ask.get_next(tick_number)
                new_bids[next_bid] = depth_event.bids.get(next_bid, depth_result.bids.get(next_bid, "0"))
                new_asks[next_ask] = depth_event.asks.get(next_ask, depth_result.asks.get(next_ask, "0"))
            depth_result.bids = new_bids
            depth_result.asks = new_asks
        self.depth_events[symbol].clear()

    def filter_depth_events(self, symbol: str) -> None:
        last_update_id = self.depth_results[symbol].last_update_id
        self.depth_events[symbol] = {
            final_update_id: data
            for final_update_id, data in self.depth_events[symbol].items()
            if final_update_id >= last_update_id
        }

    def update_depth_events(self, data: DepthEventSchema) -> None:
        self.depth_events.setdefault(data.symbol, {})[data.final_update_id] = data

    def init_depth_results(self, depth_symbols: list[DepthSchema]) -> None:
        self.depth_results = {depth_symbol.symbol: depth_symbol for depth_symbol in depth_symbols}


class LoaderService:
    def __init__(
        self,
        *,
        api: BaseExchangeAPI,
        data_queue: LoadDataQueue,
        settings: Settings,
    ) -> None:
        self._logger = logging.getLogger()
        self._symbols = set(settings.loader.symbols)
        self._depth_limit = settings.loader.depth_limit
        self._api = api
        self._data_queue = data_queue
        self._settings = settings
        self._data = DepthData()

    def _calculate_depth(self, data: DepthEventSchema) -> None:
        if not self._data.filtered_symbol_events_map.get(data.symbol):
            self._data.filter_depth_events(data.symbol)
            self._data.filtered_symbol_events_map[data.symbol] = True
            if not self._data.is_valid_first_event(data.symbol):
                raise ValueError
        if not self._data.is_valid_final_id(data.symbol, data.last_final_update_id):
            raise ValueError
        self._data.set_prev_final_update_id(data.symbol, data.final_update_id)
        self._data.update_depth_results(data.symbol, self._depth_limit)
        self._data_queue.put(
            {
                "e": DataTypeEnum.DEPTH,
                "s": data.symbol,
                "t": data.time,
                "b": self._data.depth_results[data.symbol].bids.copy(),
                "a": self._data.depth_results[data.symbol].asks.copy(),
            },
        )

    def _calculate_agg_trade(self, data: AggTradeEventSchema) -> None:
        self._data_queue.put(
            {
                "e": DataTypeEnum.AGG_TRADE,
                "m": data.trade_type,
                "s": data.symbol,
                "t": data.time,
                "p": data.price,
                "q": data.quantity,
            },
        )

    async def _listen_data(self, exchange_info: dict[str, ExchangeInfoSchema], depth_available: asyncio.Event) -> None:
        async for data in self._api.listen_data(self._symbols, exchange_info=exchange_info):
            if isinstance(data, DepthEventSchema):
                self._data.update_depth_events(data)
                is_depth_available = depth_available.is_set()
                if is_depth_available and self._data.depth_results:
                    try:
                        self._calculate_depth(data)
                    except ValueError:
                        self._data.reset()
                        break
                elif not is_depth_available and self._data.depth_events.keys() == self._symbols:
                    depth_available.set()
            elif isinstance(data, AggTradeEventSchema):
                self._calculate_agg_trade(data)

    async def run(self) -> None:
        while True:
            try:
                self._logger.info("start task")
                depth_available = asyncio.Event()
                exchange_info = await self._api.get_info(self._symbols)
                task = create_safe_task(self._listen_data(exchange_info, depth_available), logger=self._logger)
                await asyncio.wait_for(depth_available.wait(), timeout=10)
                tasks = (
                    self._api.get_depth(symbol, self._depth_limit, exchange_info=exchange_info)
                    for symbol in self._symbols
                )
                depth_symbols = await asyncio.gather(*tasks)
                self._data.init_depth_results(depth_symbols)
                await task
            except TimeoutError:
                self._logger.error("depth_available is not available... restart", exc_info=False)
                self._logger.info("closing loader")
                self._data_queue.put(None)
                break
            except asyncio.CancelledError:
                self._logger.info("closing loader")
                self._data_queue.put(None)
                break
