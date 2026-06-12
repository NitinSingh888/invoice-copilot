from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    __table_args__ = (
        Index("ix_audit_events_org_id", "org_id"),
    )

    seq: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    invoice_id: Mapped[str | None] = mapped_column(
        ForeignKey("invoices.id", name="fk_audit_events_invoice_id", ondelete="SET NULL"),
        index=True,
        default=None,
    )
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
    actor: Mapped[str]
    module: Mapped[str]
    action: Mapped[str]
    inputs: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    outputs: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    rationale: Mapped[str | None] = mapped_column(default=None)
    model_meta: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    prev_hash: Mapped[str]
    hash: Mapped[str]
    org_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id", name="fk_audit_events_org_id", ondelete="SET NULL"),
        default=None,
    )
