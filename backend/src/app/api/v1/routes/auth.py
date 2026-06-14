from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.limiter import limiter
from app.db.models.user import User
from app.repositories import org_repo, user_repo
from app.schemas.auth import (
    LoginIn,
    MemberOut,
    SignupIn,
    SignupOut,
    TokenOut,
    UserOut,
    VerifyIn,
    VerifyUserIn,
)
from app.services import auth_service

router = APIRouter()


@router.post("/signup", status_code=201, response_model=SignupOut)
@limiter.limit("5/minute")
def signup(request: Request, body: SignupIn, db: Session = Depends(get_db)) -> SignupOut:
    """Sign up a new user.

    - If ``org_name`` does not exist: creates the org, makes the user admin + verified.
    - If ``org_name`` exists: creates a member account, ``status=pending`` (needs admin approval).
    """
    user, signup_status = auth_service.signup(db, body.email, body.password, body.org_name)
    if signup_status == "active":
        msg = "Account created. You can log in immediately."
    else:
        msg = "Account created. An admin must approve your account before you can log in."
    return SignupOut(message=msg, status=signup_status)


@router.post("/verify", response_model=dict[str, bool])
def verify(body: VerifyIn, db: Session = Depends(get_db)) -> dict[str, bool]:
    """Legacy email-token verification (kept for backward compatibility)."""
    auth_service.verify_email(db, body.token)
    return {"verified": True}


@router.post("/login", response_model=TokenOut)
@limiter.limit("5/minute")
def login(request: Request, body: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    user = auth_service.authenticate(db, body.email, body.password)
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is pending admin approval.",
        )
    token = auth_service.create_access_token(user)
    return TokenOut(access_token=token)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserOut:
    org_name: str | None = None
    if current_user.org_id:
        org = org_repo.get(db, current_user.org_id)
        org_name = org.name if org is not None else None
    return UserOut(
        email=current_user.email,
        is_verified=current_user.is_verified,
        org_id=current_user.org_id,
        org_name=org_name,
        role=current_user.role,
    )


# ---------------------------------------------------------------------------
# Admin endpoints — scoped to the admin's org
# ---------------------------------------------------------------------------


@router.get("/org/members", response_model=list[MemberOut])
def list_org_members(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MemberOut]:
    """List all users in the admin's org (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    if current_user.org_id is None:
        return []
    members = user_repo.list_by_org(db, current_user.org_id)
    return [
        MemberOut(
            id=u.id,
            email=u.email,
            role=u.role,
            is_verified=u.is_verified,
        )
        for u in members
    ]


@router.get("/org/pending", response_model=list[MemberOut])
def list_pending_members(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MemberOut]:
    """List unverified (pending) users in the admin's org (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    if current_user.org_id is None:
        return []
    pending = user_repo.list_pending_by_org(db, current_user.org_id)
    return [
        MemberOut(
            id=u.id,
            email=u.email,
            role=u.role,
            is_verified=u.is_verified,
        )
        for u in pending
    ]


@router.post("/org/verify-user", response_model=MemberOut)
def verify_org_user(
    body: VerifyUserIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MemberOut:
    """Verify (approve) a pending member. Admin-only; cross-org verification is forbidden."""
    target = auth_service.admin_verify_user(db, current_user, body.user_id)
    return MemberOut(
        id=target.id,
        email=target.email,
        role=target.role,
        is_verified=target.is_verified,
    )
