from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models.comment import Comment


def add(
    s: Session,
    invoice_id: str,
    author: str,
    body: str,
    *,
    org_id: str | None = None,
) -> Comment:
    comment = Comment(
        id=f"cmt-{uuid4().hex[:8]}",
        invoice_id=invoice_id,
        author=author,
        body=body,
        org_id=org_id,
    )
    s.add(comment)
    s.flush()
    return comment


def list_for_invoice(
    s: Session, invoice_id: str, *, org_id: str | None = None
) -> list[Comment]:
    """Return comments for the given invoice, oldest first."""
    q = s.query(Comment).filter(Comment.invoice_id == invoice_id)
    if org_id is not None:
        q = q.filter(Comment.org_id == org_id)
    return list(q.order_by(Comment.created_at.asc()).all())
