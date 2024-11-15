from aiohttp import ClientSession

from .base import BaseConnector


class HttpConnector(BaseConnector):
    def __init__(self) -> None:
        self.session = ClientSession()

    async def disconnect(self) -> None:
        await self.session.close()
