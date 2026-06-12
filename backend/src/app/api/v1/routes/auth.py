from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models.user import User
from app.schemas.auth import LoginIn, SignupIn, SignupOut, TokenOut, UserOut, VerifyIn
from app.services import auth_service

router = APIRouter()


@router.post("/signup", status_code=201, response_model=SignupOut)
def signup(body: SignupIn, db: Session = Depends(get_db)) -> SignupOut:
    # NOTE: In production a real email would be sent and the verify_token
    # would NOT be returned here.  For this demo environment (no email
    # server) we return it directly so the caller can invoke /verify.
    user = auth_service.signup(db, body.email, body.password)
    token = user.verification_token or ""
    return SignupOut(
        message="Verify your email to activate your account.",
        verify_token=token,
    )


@router.post("/verify", response_model=dict[str, bool])
def verify(body: VerifyIn, db: Session = Depends(get_db)) -> dict[str, bool]:
    auth_service.verify_email(db, body.token)
    return {"verified": True}


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    user = auth_service.authenticate(db, body.email, body.password)
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified",
        )
    token = auth_service.create_access_token(user)
    return TokenOut(access_token=token)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(email=current_user.email, is_verified=current_user.is_verified)
