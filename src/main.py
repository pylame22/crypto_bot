from src.core.lifespan import lifespan_context
from src.services.depth import DepthParams, DepthService


async def main() -> None:
    async with lifespan_context() as context:
        symbols = ("SOLUSDT", "APTUSDT", "LINKUSDT")
        params = DepthParams(ws_speed=500, depth_limit=100)
        service = DepthService(symbols, params=params, context=context)
        await service.run()
