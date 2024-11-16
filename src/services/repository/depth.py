from datetime import datetime

from sqlalchemy import insert

from src.core.database.models import DepthTable
from src.core.enums import DepthTypeEnum

from .base import BaseRepository


class DepthRepository(BaseRepository):
    async def create_depth_snapshot(
        self,
        symbol: str,
        *,
        bids: dict[str, str],
        asks: dict[str, str],
        datetime_at: datetime,
    ) -> None:
        values = []
        for price, quantity in bids.items():
            values.append(
                {
                    "symbol": symbol,
                    "type": DepthTypeEnum.BID,
                    "price": price,
                    "quantity": quantity,
                    "datetime_at": datetime_at,
                },
            )
        for price, quantity in asks.items():
            values.append(
                {
                    "symbol": symbol,
                    "type": DepthTypeEnum.ASK,
                    "price": price,
                    "quantity": quantity,
                    "datetime_at": datetime_at,
                },
            )
        query = insert(DepthTable)
        await self._execute(query, values)
