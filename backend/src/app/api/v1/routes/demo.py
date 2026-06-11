"""Demo reset endpoint.

POST /demo/reset — wipe and re-seed the database with the demo dataset.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.seed import seed

router = APIRouter()


@router.post("/reset")
def demo_reset(db: Session = Depends(get_db)) -> dict[str, object]:
    """Force-reseed the database with the demo dataset and return the count."""
    n = seed(db, force=True)
    return {"status": "reseeded", "received": n}
