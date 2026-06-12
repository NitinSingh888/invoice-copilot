from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Valid status values — keep in sync with the DB check constraint.
INVOICE_STATUSES = ("received", "queued", "needs", "blocked", "cleared", "routed", "held", "rejected")
# Valid verdict values (nullable).
INVOICE_VERDICTS = ("AUTO_CLEAR", "ESCALATE", "BLOCK")


class Invoice(Base):
    __tablename__ = "invoices"

    __table_args__ = (
        CheckConstraint(
            "status IN ('received','queued','needs','blocked','cleared','routed','held','rejected')",
            name="ck_invoices_status",
        ),
        CheckConstraint(
            "verdict IS NULL OR verdict IN ('AUTO_CLEAR','ESCALATE','BLOCK')",
            name="ck_invoices_verdict",
        ),
        Index("ix_invoices_status", "status"),
        Index("ix_invoices_vendor", "vendor"),
        Index("ix_invoices_created_at", "created_at"),
        Index("ix_invoices_is_deleted", "is_deleted"),
        Index("ix_invoices_org_id", "org_id"),
    )

    id: Mapped[str] = mapped_column(primary_key=True)
    source_file: Mapped[str | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(default="received")
    vendor: Mapped[str | None] = mapped_column(default=None)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    po_number: Mapped[str | None] = mapped_column(default=None)
    invoice_number: Mapped[str | None] = mapped_column(default=None)
    confidence: Mapped[str | None] = mapped_column(default=None)
    matched_po_id: Mapped[str | None] = mapped_column(
        ForeignKey("purchase_orders.id", name="fk_invoices_matched_po_id", ondelete="SET NULL"),
        default=None,
    )
    verdict: Mapped[str | None] = mapped_column(default=None)
    route: Mapped[str | None] = mapped_column(default=None)
    owner: Mapped[str | None] = mapped_column(default=None)

    # Decision / human-action tracking
    decided_by: Mapped[str | None] = mapped_column(default=None)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    decision_reason: Mapped[str | None] = mapped_column(default=None)

    # FK to vendors table (optional; vendor name string kept for denorm)
    vendor_id: Mapped[str | None] = mapped_column(
        ForeignKey("vendors.id", name="fk_invoices_vendor_id", ondelete="SET NULL"),
        default=None,
    )

    # Organization FK
    org_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id", name="fk_invoices_org_id", ondelete="SET NULL"),
        default=None,
    )

    # Soft-delete
    is_deleted: Mapped[bool] = mapped_column(default=False, server_default="false")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
