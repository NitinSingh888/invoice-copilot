"""Store conversation thread per user (server-side persistence).

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-14 12:00:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("thread_data", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "thread_data")
