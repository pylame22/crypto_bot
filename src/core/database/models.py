from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class BaseTable(DeclarativeBase):
    pass


class DepthTable(BaseTable):
    __tablename__ = "depth"

    symbol: Mapped[str]
    type: Mapped[str]
    price: Mapped[Decimal]
    quantity: Mapped[Decimal]
    datetime_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
