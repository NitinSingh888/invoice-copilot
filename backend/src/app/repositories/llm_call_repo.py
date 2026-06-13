from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.llm_call import LlmCall
from app.db.models.user import User


def add(s: Session, **fields: Any) -> LlmCall:
    row = LlmCall(**fields)
    s.add(row)
    return row


def total_cost(s: Session, *, org_id: str) -> Decimal:
    val = s.execute(
        select(func.coalesce(func.sum(LlmCall.cost_usd), 0)).where(LlmCall.org_id == org_id)
    ).scalar_one()
    return Decimal(val)


def summary(s: Session, *, org_id: str) -> dict[str, Any]:
    """Aggregate LLM spend for one team: totals + breakdowns by purpose/model/user."""
    totals = s.execute(
        select(
            func.count(LlmCall.id),
            func.coalesce(func.sum(LlmCall.cost_usd), 0),
            func.coalesce(func.sum(LlmCall.input_tokens), 0),
            func.coalesce(func.sum(LlmCall.output_tokens), 0),
        ).where(LlmCall.org_id == org_id)
    ).one()

    by_purpose = [
        {"purpose": p, "calls": int(c), "cost_usd": str(Decimal(cost)), "tokens": int(tok)}
        for p, c, cost, tok in s.execute(
            select(
                LlmCall.purpose,
                func.count(LlmCall.id),
                func.coalesce(func.sum(LlmCall.cost_usd), 0),
                func.coalesce(func.sum(LlmCall.input_tokens + LlmCall.output_tokens), 0),
            )
            .where(LlmCall.org_id == org_id)
            .group_by(LlmCall.purpose)
            .order_by(func.coalesce(func.sum(LlmCall.cost_usd), 0).desc())
        ).all()
    ]

    by_model = [
        {"model": m or "—", "calls": int(c), "cost_usd": str(Decimal(cost))}
        for m, c, cost in s.execute(
            select(
                LlmCall.model,
                func.count(LlmCall.id),
                func.coalesce(func.sum(LlmCall.cost_usd), 0),
            )
            .where(LlmCall.org_id == org_id)
            .group_by(LlmCall.model)
            .order_by(func.coalesce(func.sum(LlmCall.cost_usd), 0).desc())
        ).all()
    ]

    by_user = [
        {"user": email or "—", "calls": int(c), "cost_usd": str(Decimal(cost))}
        for email, c, cost in s.execute(
            select(
                User.email,
                func.count(LlmCall.id),
                func.coalesce(func.sum(LlmCall.cost_usd), 0),
            )
            .select_from(LlmCall)
            .join(User, User.id == LlmCall.user_id, isouter=True)
            .where(LlmCall.org_id == org_id)
            .group_by(User.email)
            .order_by(func.coalesce(func.sum(LlmCall.cost_usd), 0).desc())
        ).all()
    ]

    return {
        "total_calls": int(totals[0]),
        "total_cost_usd": str(Decimal(totals[1])),
        "total_input_tokens": int(totals[2]),
        "total_output_tokens": int(totals[3]),
        "by_purpose": by_purpose,
        "by_model": by_model,
        "by_user": by_user,
    }


def recent(s: Session, *, org_id: str, limit: int = 20) -> list[LlmCall]:
    return list(
        s.execute(
            select(LlmCall)
            .where(LlmCall.org_id == org_id)
            .order_by(LlmCall.created_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
