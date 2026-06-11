from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[str] = mapped_column(primary_key=True)
    po_number: Mapped[str] = mapped_column(index=True)
    vendor: Mapped[str]
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(default="USD")
    remaining_balance: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), default=None
    )
    status: Mapped[str] = mapped_column(default="open")
