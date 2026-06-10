from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from collections import defaultdict
from collections.abc import Sequence

@dataclass(frozen=True)
class Correction:
    invoice_id: str
    vendor: str
    finding_code: str
    user_action: str
    over_pct: Decimal

@dataclass(frozen=True)
class PatternCandidate:
    vendor: str
    finding_code: str
    action: str
    example_ids: tuple[str, ...]
    over_pcts: tuple[Decimal, ...]

    @property
    def max_over_pct(self) -> Decimal:
        return max(self.over_pcts)

def _shape(c: Correction) -> tuple[str, str, str]:
    return (c.vendor, c.finding_code, c.user_action)

def detect_pattern(corrections: Sequence[Correction], min_count: int = 3) -> PatternCandidate | None:
    groups: dict[tuple[str, str, str], list[Correction]] = defaultdict(list)
    for c in corrections:
        groups[_shape(c)].append(c)
    for (vendor, code, action), items in groups.items():
        if len(items) >= min_count:
            return PatternCandidate(
                vendor=vendor, finding_code=code, action=action,
                example_ids=tuple(c.invoice_id for c in items),
                over_pcts=tuple(c.over_pct for c in items),
            )
    return None
