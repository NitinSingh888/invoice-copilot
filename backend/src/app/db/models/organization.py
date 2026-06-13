from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, index=True)

    # Editable auto-approve policy (the "default rule"). When enabled, a clean
    # invoice (approved vendor, matched PO, no flags, high confidence, cold-start
    # met) under the threshold is auto-approved; above it, or with any flag, it
    # escalates. Disabling sends everything to a human regardless of amount.
    auto_approve_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_approve_threshold: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("100")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
