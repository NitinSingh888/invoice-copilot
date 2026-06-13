from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, Header, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.clients.llm.base import LLMClient
from app.clients.llm.factory import build_llm_client
from app.clients.llm.metered import MeteredLLMClient
from app.core.config import get_settings
from app.core.security import current_role
from app.db.models.user import User
from app.db.session import SessionLocal
from app.repositories import user_repo
from app.services import auth_service

# Module-level cache — one real client per process lifetime.
_llm_client: LLMClient | None = None

_bearer = HTTPBearer(auto_error=False)


def _real_llm() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = build_llm_client(get_settings())
    return _llm_client


def get_db() -> Iterator[Session]:
    s: Session = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def get_role(x_role: str | None = Header(default=None)) -> str:
    return current_role(x_role)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> User:
    # Prefer the Authorization header; fall back to a ?token= query param so that
    # browser-native requests that can't set headers (an <iframe>/<img> document
    # preview) can still authenticate. The org check still applies downstream.
    raw = credentials.credentials if credentials is not None else token
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = auth_service.decode_token(raw)
    user = user_repo.get(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is pending admin approval.",
        )
    return user


def get_current_org(user: User = Depends(get_current_user)) -> str:
    """Return the org_id of the authenticated user."""
    if user.org_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to an organization",
        )
    return user.org_id


def get_llm(user: User = Depends(get_current_user)) -> LLMClient:
    """A per-request LLM client that meters every call — recording its purpose,
    the triggering user/team, token usage, actual cost, and latency to the
    ``llm_calls`` table. Wraps the process-wide real client."""
    return MeteredLLMClient(_real_llm(), org_id=user.org_id, user_id=user.id)
