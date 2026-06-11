from __future__ import annotations

from pydantic import BaseModel

from app.domain.policy.findings import Finding


class FindingOut(BaseModel):
    code: str
    severity: str
    detail: str

    @classmethod
    def from_domain(cls, f: Finding) -> "FindingOut":
        return cls(code=f.code, severity=f.severity.value, detail=f.detail)
