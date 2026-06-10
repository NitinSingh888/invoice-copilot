from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy import DateTime, JSON, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[str] = mapped_column(primary_key=True)
    vendor: Mapped[str | None] = mapped_column(default=None)
    max_over_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), default=None)
    route: Mapped[str]
    status: Mapped[str] = mapped_column(default="active")
    min_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    source_correction_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    reasoning_note: Mapped[str | None] = mapped_column(default=None)
    created_by: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), default=lambda: datetime.now(timezone.utc)
    )
