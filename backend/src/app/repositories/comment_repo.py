from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models.comment import Comment


def add(s: Session, invoice_id: str, author: str, body: str) -> Comment:
    comment = Comment(
        id=f"cmt-{uuid4().hex[:8]}",
        invoice_id=invoice_id,
        author=author,
        body=body,
    )
    s.add(comment)
    s.flush()
    return comment


def list_for_invoice(s: Session, invoice_id: str) -> list[Comment]:
    """Return comments for the given invoice, oldest first."""
    return list(
        s.query(Comment)
        .filter(Comment.invoice_id == invoice_id)
        .order_by(Comment.created_at.asc())
        .all()
    )
