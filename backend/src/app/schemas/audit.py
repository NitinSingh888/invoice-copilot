from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seq: int
    invoice_id: str | None
    actor: str
    module: str
    action: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    rationale: str | None
    model_meta: dict[str, Any] | None
    prev_hash: str
    hash: str
    ts: datetime


class AuditTrailOut(BaseModel):
    events: list[AuditEventOut]
    chain_verified: bool
