from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_org, get_db
from app.repositories import llm_call_repo

router = APIRouter()

_RECENT_LIMIT = 25


@router.get("")
def get_usage(
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org),
) -> dict[str, Any]:
    """AI usage and *actual* spend for the current team.

    Returns the running total cost, token counts, and call count for the
    organization, breakdowns by purpose / model / user, and the most recent
    individual calls (what each was for, who triggered it, and what it cost).
    """
    data = llm_call_repo.summary(db, org_id=org_id)
    recent = [
        {
            "id": c.id,
            "purpose": c.purpose,
            "reason": c.reason,
            "entity_type": c.entity_type,
            "entity_id": c.entity_id,
            "provider": c.provider,
            "model": c.model,
            "input_tokens": c.input_tokens,
            "output_tokens": c.output_tokens,
            "cost_usd": str(c.cost_usd),
            "latency_ms": c.latency_ms,
            "status": c.status,
            "user_id": c.user_id,
            "created_at": c.created_at.isoformat(),
        }
        for c in llm_call_repo.recent(db, org_id=org_id, limit=_RECENT_LIMIT)
    ]
    return {"currency": "USD", **data, "recent": recent}
