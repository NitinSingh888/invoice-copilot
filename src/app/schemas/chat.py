from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ChatMessageIn(BaseModel):
    role: str
    content: str


class ChatIn(BaseModel):
    message: str
    history: list[ChatMessageIn] = []


class ChatOut(BaseModel):
    reply: str
    intent: str
    result: dict[str, Any] | None = None
