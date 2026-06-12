from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_serializer


class CommentIn(BaseModel):
    body: str


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    invoice_id: str
    author: str
    body: str
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return value.isoformat()
