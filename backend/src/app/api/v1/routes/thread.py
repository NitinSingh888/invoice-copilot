"""Conversation thread persistence — stored per user, synced across browsers."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models.user import User

router = APIRouter()


class ThreadBody(BaseModel):
    thread: list[dict[str, object]]


@router.get("")
def get_thread(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, list[dict[str, object]]]:
    """Return the user's saved conversation thread."""
    import json

    if user.thread_data:
        try:
            return {"thread": json.loads(user.thread_data)}
        except (json.JSONDecodeError, TypeError):
            return {"thread": []}
    return {"thread": []}


@router.put("", status_code=204)
def save_thread(
    body: ThreadBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Save the conversation thread for the current user."""
    import json

    user.thread_data = json.dumps(body.thread)
    db.flush()
