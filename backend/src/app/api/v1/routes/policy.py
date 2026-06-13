from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_org, get_current_user, get_db
from app.db.models.user import User
from app.repositories import org_repo

router = APIRouter()


class PolicyOut(BaseModel):
    auto_approve_enabled: bool
    auto_approve_threshold: Decimal


class PolicyPatch(BaseModel):
    auto_approve_enabled: bool | None = None
    auto_approve_threshold: Decimal | None = Field(default=None, ge=0)


def _policy_of(db: Session, org_id: str) -> PolicyOut:
    org = org_repo.get(db, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return PolicyOut(
        auto_approve_enabled=org.auto_approve_enabled,
        auto_approve_threshold=org.auto_approve_threshold,
    )


@router.get("", response_model=PolicyOut)
def get_policy(
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org),
) -> PolicyOut:
    """The team's auto-approve policy (the editable default rule)."""
    return _policy_of(db, org_id)


@router.patch("", response_model=PolicyOut)
def update_policy(
    body: PolicyPatch,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org),
) -> PolicyOut:
    """Update the auto-approve policy. Admins only."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an admin can change the auto-approve policy.",
        )
    org = org_repo.get(db, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    if body.auto_approve_enabled is not None:
        org.auto_approve_enabled = body.auto_approve_enabled
    if body.auto_approve_threshold is not None:
        org.auto_approve_threshold = body.auto_approve_threshold
    db.flush()
    return _policy_of(db, org_id)
