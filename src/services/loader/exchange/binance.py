from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Annotated

from aiohttp import WSMsgType

from src.core.enums import ExchangeEnum
from src.services.loader.schemas import DepthEventSchema, DepthSchema, ExchangeInfoSchema
from src.services.loader.types import ScaledPrice

from .base import BaseExchangeAPI, ExchangeError

if TYPE_CHECKING:
    from src.core.types import DictStrAny


class BinanceAPI(BaseExchangeAPI):
    _EXCHANGE = ExchangeEnum.BINANCE
    _API_URL = "https://fapi.binance.com/fapi/v1/"
    _WS_URL = "wss://fstream.binance.com/stream"

    @staticmethod
    def _get_depth_data(
        data: list[Annotated[list[str], 2]],
        tick_size: str,
        *,
        is_reverse: bool = False,
    ) -> tuple[dict[ScaledPrice, str], ScaledPrice]:
        depth_data = {}
        first_price = None
        iterator = reversed(data) if is_reverse else data

        for price, qty in iterator:
            scaled_price = ScaledPrice.from_price_and_tick(price, tick_size)
            depth_data[scaled_price] = qty
            if not first_price and qty != "0":
                first_price = scaled_price

        if not first_price:
            msg = "can not find first_price"
            raise ExchangeError(msg)
        return depth_data, first_price

    async def get_info(self, symbols: set[str]) -> dict[str, ExchangeInfoSchema]:
        response = await self._request(self._GET, "exchangeInfo")
        result: dict[str, ExchangeInfoSchema] = {}
        for data in response["symbols"]:
            if data["symbol"] in symbols and data["status"] == "TRADING" and data["contractType"] == "PERPETUAL":
                price_filter = next(f for f in data["filters"] if f["filterType"] == "PRICE_FILTER")
                result[data["symbol"]] = ExchangeInfoSchema(
                    symbol=data["symbol"],
                    tick_size=price_filter["tickSize"],
                )
        if result.keys() != symbols:
            msg = f"can not get all symbols: {symbols}"
            raise ExchangeError(msg)
        return result

    async def get_depth(self, symbol: str, limit: int, *, exchange_info: dict[str, ExchangeInfoSchema]) -> DepthSchema:
        params = {"symbol": symbol, "limit": limit}
        response = await self._request(self._GET, "depth", params=params)
        tick_size = exchange_info[symbol].tick_size
        bids, first_bid = self._get_depth_data(response["bids"], tick_size)
        asks, first_ask = self._get_depth_data(response["asks"], tick_size)
        return DepthSchema(
            symbol=symbol,
            last_update_id=response["lastUpdateId"],
            bids=bids,
            asks=asks,
            first_bid=first_bid,
            first_ask=first_ask,
        )

    async def listen_depth(
        self,
        symbols: set[str],
        speed: int,
        *,
        exchange_info: dict[str, ExchangeInfoSchema],
    ) -> AsyncGenerator[DepthEventSchema]:
        params = [f"{symbol.lower()}@depth@{speed}ms" for symbol in symbols]
        async with self._http.session.ws_connect(self._WS_URL) as ws:
            request_data = self._json_encoder.encode({"method": "SUBSCRIBE", "params": params})
            await ws.send_frame(request_data, WSMsgType.TEXT)
            async for msg in ws:
                if msg.type == WSMsgType.ERROR:
                    break
                response: DictStrAny = self._json_decoder.decode(msg.data)
                if response.get("stream") in params:
                    data = response["data"]
                    tick_size = exchange_info[data["s"]].tick_size
                    bids, first_bid = self._get_depth_data(data["b"], tick_size, is_reverse=True)
                    asks, first_ask = self._get_depth_data(data["a"], tick_size)
                    yield DepthEventSchema(
                        symbol=data["s"],
                        time=data["T"],
                        first_update_id=data["U"],
                        final_update_id=data["u"],
                        last_final_update_id=data["pu"],
                        bids=bids,
                        asks=asks,
                        first_bid=first_bid,
                        first_ask=first_ask,
                    )
