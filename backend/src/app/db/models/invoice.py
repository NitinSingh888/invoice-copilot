from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy import DateTime, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(primary_key=True)
    source_file: Mapped[str | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(default="received")
    vendor: Mapped[str | None] = mapped_column(default=None)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    po_number: Mapped[str | None] = mapped_column(default=None)
    invoice_number: Mapped[str | None] = mapped_column(default=None)
    confidence: Mapped[str | None] = mapped_column(default=None)
    matched_po_id: Mapped[str | None] = mapped_column(default=None)
    verdict: Mapped[str | None] = mapped_column(default=None)
    route: Mapped[str | None] = mapped_column(default=None)
    owner: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), default=lambda: datetime.now(timezone.utc)
    )
