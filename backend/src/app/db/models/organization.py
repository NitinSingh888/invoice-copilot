from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
