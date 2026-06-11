from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class RuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    vendor: str | None
    finding_code: str | None
    max_over_pct: Decimal | None
    route: str
    status: str
    min_amount: Decimal | None
    source_correction_ids: list[str]
    reasoning_note: str | None


class PatternOut(BaseModel):
    vendor: str | None
    finding_code: str
    action: str
    example_ids: list[str]
    over_pcts: list[Decimal]


class RuleProposalOut(BaseModel):
    candidate: PatternOut
    threshold_pct: Decimal
    route: str


class ActivateRuleIn(BaseModel):
    threshold_pct: Decimal
    route: str


class RuleStatusIn(BaseModel):
    status: Literal["active", "disabled"]
