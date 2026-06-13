from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

class ConfidenceBand(str, Enum):
    HIGH = "HIGH"
    MED = "MED"
    LOW = "LOW"

class Verdict(str, Enum):
    AUTO_CLEAR = "AUTO_CLEAR"
    ESCALATE = "ESCALATE"
    BLOCK = "BLOCK"

@dataclass(frozen=True)
class Thresholds:
    t_amount: Decimal = Decimal("10000")
    # When False, the auto-approve policy is off — nothing auto-clears.
    auto_clear_enabled: bool = True
