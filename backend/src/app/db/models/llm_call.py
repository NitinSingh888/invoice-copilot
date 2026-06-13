from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LlmCall(Base):
    """One LLM API call: what it was for, who triggered it, and what it cost.

    Cost is the actual token usage priced through ``domain.llm_pricing`` — never a
    hard-coded per-call number.
    """

    __tablename__ = "llm_calls"

    __table_args__ = (
        Index("ix_llm_calls_org_id", "org_id"),
        Index("ix_llm_calls_org_created", "org_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(primary_key=True)

    # Team (multi-tenancy) and the user who triggered the call ("by whom").
    org_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id", name="fk_llm_calls_org_id", ondelete="CASCADE"),
        default=None,
    )
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", name="fk_llm_calls_user_id", ondelete="SET NULL"),
        default=None,
    )

    # What the call was for.
    purpose: Mapped[str] = mapped_column(default="")  # extract_invoice|converse|parse_command|explain_rule
    reason: Mapped[str] = mapped_column(Text, default="")  # human-readable description
    entity_type: Mapped[str | None] = mapped_column(default=None)  # e.g. "invoice", "vendor"
    entity_id: Mapped[str | None] = mapped_column(default=None)

    # Provider + actual usage + cost.
    provider: Mapped[str] = mapped_column(default="")
    model: Mapped[str] = mapped_column(default="")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(14, 6), default=Decimal("0"))
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)

    status: Mapped[str] = mapped_column(default="ok")  # ok|error
    error: Mapped[str | None] = mapped_column(Text, default=None)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
