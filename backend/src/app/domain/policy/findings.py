from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from collections.abc import Iterable

class Severity(str, Enum):
    INFO = "info"
    WARN = "warn"
    HARD_STOP = "hard_stop"

_ORDER = {Severity.INFO: 0, Severity.WARN: 1, Severity.HARD_STOP: 2}

@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    detail: str = ""

def max_severity(findings: Iterable[Finding]) -> Severity:
    items = list(findings)
    if not items:
        return Severity.INFO
    return max((f.severity for f in items), key=lambda s: _ORDER[s])
