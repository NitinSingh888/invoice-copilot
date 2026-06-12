from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Comment(Base):
    __tablename__ = "comments"

    __table_args__ = (
        Index("ix_comments_invoice_id", "invoice_id"),
        Index("ix_comments_org_id", "org_id"),
    )

    id: Mapped[str] = mapped_column(primary_key=True)
    invoice_id: Mapped[str] = mapped_column(
        ForeignKey("invoices.id", name="fk_comments_invoice_id", ondelete="CASCADE"),
    )
    author: Mapped[str]
    body: Mapped[str] = mapped_column(Text)
    org_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id", name="fk_comments_org_id", ondelete="SET NULL"),
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
