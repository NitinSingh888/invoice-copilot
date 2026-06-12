from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_serializer, model_validator

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
    updated_at: datetime | None = None
    decided_by: str | None = None
    decided_at: datetime | None = None
    decision_reason: str | None = None

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return value.isoformat()

    @field_serializer("updated_at")
    def serialize_updated_at(self, value: datetime | None) -> str | None:
        return value.isoformat() if value is not None else None

    @field_serializer("decided_at")
    def serialize_decided_at(self, value: datetime | None) -> str | None:
        return value.isoformat() if value is not None else None

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
    action: Literal["approve", "hold", "edit", "route", "reject"]
    amount: Decimal | None = None
    route: str | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def reject_requires_reason(self) -> "ActionIn":
        if self.action == "reject" and not self.reason:
            raise ValueError("reason is required when action is 'reject'")
        return self


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
