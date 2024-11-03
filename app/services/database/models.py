from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class BaseTable(DeclarativeBase):
    pass


class DepthTable(BaseTable):
    __tablename__ = "depth"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))
    symbol: Mapped[str]
    type: Mapped[str]
    price: Mapped[Decimal]
    quantity: Mapped[Decimal]
    datetime_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
