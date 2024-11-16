from src.core.lifespan import lifespan_context
from src.services.depth import DepthParams, DepthService
from src.services.exchange.binance import BinanceAPI
from src.services.repository.depth import DepthRepository


async def main() -> None:
    async with lifespan_context() as context:
        symbols = ("SOLUSDT",)
        params = DepthParams(ws_speed=500, depth_limit=100)
        service = DepthService(symbols, params, api=BinanceAPI(context), repo=DepthRepository(context), context=context)
        await service.run()
