from collections.abc import AsyncGenerator, Iterable
from typing import TYPE_CHECKING, Annotated

from aiohttp import WSMsgType

from src.core.enums import ExchangeEnum
from src.core.schemas import DepthChangeSchema, DepthSchema

from .base import BaseExchangeAPI

if TYPE_CHECKING:
    from src.core.types import DictStrAny


class BinanceAPI(BaseExchangeAPI):
    _EXCHANGE = ExchangeEnum.BINANCE
    _API_URL = "https://fapi.binance.com/fapi/v1/"
    _WS_URL = "wss://fstream.binance.com/stream"

    @staticmethod
    def _get_depth_data(data: list[Annotated[list[str], 2]]) -> dict[str, str]:
        return dict(data)

    async def get_depth(self, symbol: str, limit: int) -> DepthSchema:
        params = {"symbol": symbol, "limit": limit}
        response = await self._request("get", "depth", params=params)
        bids = self._get_depth_data(response["bids"])
        asks = self._get_depth_data(response["asks"])
        return DepthSchema(symbol=symbol, last_update_id=response["lastUpdateId"], bids=bids, asks=asks)

    async def listen_depth(self, symbols: Iterable[str], speed: int = 500) -> AsyncGenerator[DepthChangeSchema]:
        params = [f"{symbol.lower()}@depth@{speed}ms" for symbol in symbols]
        async with self._http.session.ws_connect(self._WS_URL) as ws:
            request_data = self._json_encoder.encode({"method": "SUBSCRIBE", "params": params})
            await ws._writer.send(request_data)  # noqa: SLF001
            async for msg in ws:
                if msg.type == WSMsgType.ERROR:
                    break
                response: DictStrAny = self._json_decoder.decode(msg.data)
                if response.get("stream") in params:
                    data = response["data"]
                    bids = self._get_depth_data(data["b"])
                    asks = self._get_depth_data(data["a"])
                    yield DepthChangeSchema(
                        symbol=data["s"],
                        time=data["T"],
                        first_update_id=data["U"],
                        final_update_id=data["u"],
                        last_final_update_id=data["pu"],
                        bids=bids,
                        asks=asks,
                    )
