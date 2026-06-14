from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.organization import Organization
from app.db.models.user import User
from app.repositories import org_repo, user_repo


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def signup(db: Session, email: str, password: str, org_name: str) -> tuple[User, str]:
    """Create a new user, creating or joining an org.

    Returns (user, status) where status is 'active' or 'pending'.

    - If the org does not exist: create it, make the user admin + verified (founder).
      Also seeds the org's demo dataset.
    - If the org exists: create the user as member, is_verified=False (pending admin
      approval). No verification token.
    """
    email = email.lower()
    if user_repo.get_by_email(db, email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    existing_org = org_repo.get_by_name(db, org_name)
    uid = "usr-" + secrets.token_hex(4)

    if existing_org is None:
        # Found a new org — founder flow
        org_id = "org-" + secrets.token_hex(4)
        org = Organization(id=org_id, name=org_name)
        org_repo.add(db, org)

        user = User(
            id=uid,
            email=email,
            password_hash=hash_password(password),
            is_verified=True,
            verification_token=None,
            org_id=org_id,
            role="admin",
        )
        user_repo.add(db, user)

        return user, "active"
    else:
        # Existing org — member flow, pending admin approval
        user = User(
            id=uid,
            email=email,
            password_hash=hash_password(password),
            is_verified=False,
            verification_token=None,
            org_id=existing_org.id,
            role="member",
        )
        user_repo.add(db, user)
        return user, "pending"


def _seed_org(db: Session, org_id: str) -> None:
    """Seed the demo dataset for a given org inside a savepoint.

    If seeding fails the savepoint is rolled back (session stays usable)
    and the error is logged — the user + org already written by the outer
    transaction are unaffected.
    """
    import logging

    try:
        from app.seed import seed_org

        # Use a nested savepoint so that a seeding error does not poison
        # the outer session (which already has the new user + org).
        with db.begin_nested():
            seed_org(db, org_id)
    except Exception:
        logging.getLogger(__name__).exception("Failed to seed org %s", org_id)


def verify_email(db: Session, token: str) -> User:
    """Legacy email-token verification — kept for backward compatibility."""
    user = user_repo.get_by_verification_token(db, token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )
    user.is_verified = True
    user.verification_token = None
    db.flush()
    return user


def admin_verify_user(db: Session, admin: User, target_user_id: str) -> User:
    """Allow an admin to verify a pending member in the same org."""
    if admin.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    target = user_repo.get(db, target_user_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if target.org_id != admin.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot verify a user from a different organization",
        )
    target.is_verified = True
    target.verification_token = None
    db.flush()
    return target


def authenticate(db: Session, email: str, password: str) -> User:
    email = email.lower()
    user = user_repo.get_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return user


def create_access_token(user: User) -> str:
    settings = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": user.id, "exp": exp}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> str:
    """Decode a JWT and return the user_id (sub claim). Raises HTTPException on failure."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    sub = payload.get("sub")
    if not isinstance(sub, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    return sub
