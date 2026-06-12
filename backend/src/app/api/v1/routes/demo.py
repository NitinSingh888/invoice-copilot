"""Demo reset endpoint.

POST /demo/reset — wipe and re-seed the database with the demo dataset.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_org, get_db
from app.db.models.organization import Organization
from app.seed import seed_org

router = APIRouter()


@router.post("/reset")
def demo_reset(
    db: Session = Depends(get_db),
    org_id: str = Depends(get_current_org),
) -> dict[str, object]:
    """Force-reseed the database with the demo dataset for the current org and return the count."""
    # Ensure org row exists (may not exist in test environments).
    if db.get(Organization, org_id) is None:
        db.add(Organization(id=org_id, name=org_id))
        db.flush()
    n = seed_org(db, org_id, force=True)
    return {"status": "reseeded", "received": n}
