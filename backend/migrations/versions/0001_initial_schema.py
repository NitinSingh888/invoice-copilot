"""initial schema — baseline for all 7 tables as originally created by create_all

Revision ID: 0001
Revises:
Create Date: 2026-06-12 00:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # vendors                                                              #
    # ------------------------------------------------------------------ #
    op.create_table(
        "vendors",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("canonical_name", sa.String(), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("default_approver", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------ #
    # purchase_orders                                                      #
    # ------------------------------------------------------------------ #
    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("po_number", sa.String(), nullable=False),
        sa.Column("vendor", sa.String(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("remaining_balance", sa.Numeric(12, 2), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_purchase_orders_po_number"), "purchase_orders", ["po_number"], unique=False
    )

    # ------------------------------------------------------------------ #
    # invoices                                                             #
    # ------------------------------------------------------------------ #
    op.create_table(
        "invoices",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("source_file", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("vendor", sa.String(), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("po_number", sa.String(), nullable=True),
        sa.Column("invoice_number", sa.String(), nullable=True),
        sa.Column("confidence", sa.String(), nullable=True),
        sa.Column("matched_po_id", sa.String(), nullable=True),
        sa.Column("verdict", sa.String(), nullable=True),
        sa.Column("route", sa.String(), nullable=True),
        sa.Column("owner", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------ #
    # corrections                                                          #
    # ------------------------------------------------------------------ #
    op.create_table(
        "corrections",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("invoice_id", sa.String(), nullable=False),
        sa.Column("vendor", sa.String(), nullable=False),
        sa.Column("finding_code", sa.String(), nullable=False),
        sa.Column("user_action", sa.String(), nullable=False),
        sa.Column("over_pct", sa.Numeric(6, 4), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------ #
    # rules                                                                #
    # ------------------------------------------------------------------ #
    op.create_table(
        "rules",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("vendor", sa.String(), nullable=True),
        sa.Column("finding_code", sa.String(), nullable=True),
        sa.Column("max_over_pct", sa.Numeric(6, 4), nullable=True),
        sa.Column("route", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("min_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("source_correction_ids", sa.JSON(), nullable=False),
        sa.Column("reasoning_note", sa.String(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ------------------------------------------------------------------ #
    # audit_events                                                         #
    # ------------------------------------------------------------------ #
    op.create_table(
        "audit_events",
        sa.Column("seq", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("invoice_id", sa.String(), nullable=True),
        sa.Column(
            "ts",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("module", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("inputs", sa.JSON(), nullable=False),
        sa.Column("outputs", sa.JSON(), nullable=False),
        sa.Column("rationale", sa.String(), nullable=True),
        sa.Column("model_meta", sa.JSON(), nullable=True),
        sa.Column("prev_hash", sa.String(), nullable=False),
        sa.Column("hash", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("seq"),
    )
    op.create_index(
        op.f("ix_audit_events_invoice_id"), "audit_events", ["invoice_id"], unique=False
    )

    # ------------------------------------------------------------------ #
    # users                                                                #
    # ------------------------------------------------------------------ #
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("verification_token", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_audit_events_invoice_id"), table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_table("rules")
    op.drop_table("corrections")
    op.drop_table("invoices")
    op.drop_index(op.f("ix_purchase_orders_po_number"), table_name="purchase_orders")
    op.drop_table("purchase_orders")
    op.drop_table("vendors")
