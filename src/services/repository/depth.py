import datetime

from sqlalchemy import insert

from src.core.database.models import DepthTable
from src.core.enums import DepthTypeEnum
from src.core.schemas import DepthSchema

from .base import BaseRepository


class DepthRepository(BaseRepository):
    async def create_depth_snapshot(self, depth_data: DepthSchema, time: int) -> None:
        values = []
        datetime_at = datetime.datetime.fromtimestamp(time / 1000, datetime.UTC)
        for price, quantity in depth_data.bids.items():
            values.append(
                {
                    "symbol": depth_data.symbol,
                    "type": DepthTypeEnum.BID,
                    "price": price,
                    "quantity": quantity,
                    "datetime_at": datetime_at,
                },
            )
        for price, quantity in depth_data.asks.items():
            values.append(
                {
                    "symbol": depth_data.symbol,
                    "type": DepthTypeEnum.ASK,
                    "price": price,
                    "quantity": quantity,
                    "datetime_at": datetime_at,
                },
            )
        query = insert(DepthTable)
        await self._execute(query, values)
