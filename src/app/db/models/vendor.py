from __future__ import annotations

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[str] = mapped_column(primary_key=True)
    canonical_name: Mapped[str]
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(default="new")
    default_approver: Mapped[str | None] = mapped_column(default=None)
