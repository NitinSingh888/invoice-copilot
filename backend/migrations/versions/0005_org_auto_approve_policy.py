"""org auto-approve policy — editable default rule (threshold + on/off)

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-13 00:05:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column(
            "auto_approve_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.add_column(
        "organizations",
        sa.Column(
            "auto_approve_threshold",
            sa.Numeric(14, 2),
            nullable=False,
            server_default="100",
        ),
    )


def downgrade() -> None:
    op.drop_column("organizations", "auto_approve_threshold")
    op.drop_column("organizations", "auto_approve_enabled")
