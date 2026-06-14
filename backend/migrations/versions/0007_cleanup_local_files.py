"""Clean up invoices with local file references (no S3).

When S3 is enabled, old invoices that reference local files (not s3://)
can't be previewed on Render's ephemeral disk. This migration nullifies
those stale source_file references so they show "No document" instead of
broken preview errors.

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-14 18:00:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Null out source_file for invoices that don't have S3 paths.
    # These referenced local files that don't exist on Render.
    op.execute(
        sa.text(
            "UPDATE invoices SET source_file = NULL "
            "WHERE source_file IS NOT NULL AND source_file NOT LIKE 's3://%'"
        )
    )


def downgrade() -> None:
    # Can't restore the original local paths — they were stale anyway.
    pass
