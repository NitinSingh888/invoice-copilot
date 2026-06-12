from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Correction(Base):
    __tablename__ = "corrections"

    __table_args__ = (
        Index("ix_corrections_invoice_id", "invoice_id"),
    )

    id: Mapped[str] = mapped_column(primary_key=True)
    invoice_id: Mapped[str] = mapped_column(
        ForeignKey("invoices.id", name="fk_corrections_invoice_id", ondelete="CASCADE"),
    )
    vendor: Mapped[str]
    finding_code: Mapped[str]
    user_action: Mapped[str]
    over_pct: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    reason: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
