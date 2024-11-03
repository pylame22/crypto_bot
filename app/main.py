from app.services.depth import DepthParams, DepthService
from app.services.lifespan import lifespan_context


async def main() -> None:
    async with lifespan_context() as context:
        symbols = ("SOLUSDT", "APTUSDT", "LINKUSDT")
        params = DepthParams(ws_speed=500, depth_limit=100)
        service = DepthService(symbols, params=params, context=context)
        await service.run()
