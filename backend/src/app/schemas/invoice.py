from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_serializer

from app.schemas.common import FindingOut


class InvoiceIn(BaseModel):
    vendor: str
    amount: Decimal
    invoice_number: str
    po_number: str | None = None
    id: str | None = None
    source_file: str | None = None
    confidence: str = "HIGH"


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    vendor: str | None
    amount: Decimal | None
    po_number: str | None
    invoice_number: str | None
    status: str
    verdict: str | None
    route: str | None
    source_file: str | None = None
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return value.isoformat()

    @property
    def has_file(self) -> bool:
        return self.source_file is not None


class ProcessResultOut(BaseModel):
    invoice_id: str
    verdict: str
    route: str | None
    reason: str
    status: str
    findings: list[FindingOut]


class ActionIn(BaseModel):
    action: Literal["approve", "hold", "edit", "route"]
    amount: Decimal | None = None
    route: str | None = None
    reason: str | None = None


class BulkActionIn(BaseModel):
    ids: list[str]
    action: Literal["approve", "hold", "route"]
    route: str | None = None


class BulkActionResultItem(BaseModel):
    id: str
    status: str


class BulkActionOut(BaseModel):
    applied: int
    results: list[BulkActionResultItem]
