from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models.user import User


def add(s: Session, user: User) -> User:
    s.add(user)
    s.flush()
    return user


def get(s: Session, user_id: str) -> User | None:
    return s.get(User, user_id)


def get_by_email(s: Session, email: str) -> User | None:
    return s.query(User).filter(User.email == email).first()


def get_by_verification_token(s: Session, token: str) -> User | None:
    return s.query(User).filter(User.verification_token == token).first()


def list_by_org(s: Session, org_id: str) -> list[User]:
    """Return all users in an organization."""
    return list(s.query(User).filter(User.org_id == org_id).all())


def list_pending_by_org(s: Session, org_id: str) -> list[User]:
    """Return unverified (pending) users in an organization."""
    return list(
        s.query(User)
        .filter(User.org_id == org_id, User.is_verified.is_(False))
        .all()
    )
