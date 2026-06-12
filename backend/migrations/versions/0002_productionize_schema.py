"""productionize schema — add comments table, decision fields, soft-delete,
updated_at, FKs, indexes, check constraints

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-12 00:01:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # invoices — new columns                                               #
    # ------------------------------------------------------------------ #
    op.add_column(
        "invoices",
        sa.Column("decided_by", sa.String(), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column("decision_reason", sa.String(), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column("vendor_id", sa.String(), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "invoices",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Migrate created_at to timezone-aware (TIMESTAMP WITH TIME ZONE)
    op.alter_column(
        "invoices",
        "created_at",
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )

    # invoices — indexes
    op.create_index("ix_invoices_status", "invoices", ["status"])
    op.create_index("ix_invoices_vendor", "invoices", ["vendor"])
    op.create_index("ix_invoices_created_at", "invoices", ["created_at"])
    op.create_index("ix_invoices_is_deleted", "invoices", ["is_deleted"])

    # Data fix: matched_po_id was historically stored as po_number, not the PK.
    # Resolve to actual PO id where possible; set NULL otherwise.
    op.execute(
        sa.text(
            """
            UPDATE invoices i
            SET matched_po_id = po.id
            FROM purchase_orders po
            WHERE po.po_number = i.matched_po_id
              AND i.matched_po_id IS NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE invoices
            SET matched_po_id = NULL
            WHERE matched_po_id IS NOT NULL
              AND matched_po_id NOT IN (SELECT id FROM purchase_orders)
            """
        )
    )

    # invoices — FKs
    op.create_foreign_key(
        "fk_invoices_matched_po_id",
        "invoices",
        "purchase_orders",
        ["matched_po_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_invoices_vendor_id",
        "invoices",
        "vendors",
        ["vendor_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # invoices — check constraints
    op.create_check_constraint(
        "ck_invoices_status",
        "invoices",
        "status IN ('received','queued','needs','blocked','cleared','routed','held','rejected')",
    )
    op.create_check_constraint(
        "ck_invoices_verdict",
        "invoices",
        "verdict IS NULL OR verdict IN ('AUTO_CLEAR','ESCALATE','BLOCK')",
    )

    # ------------------------------------------------------------------ #
    # corrections — index + FK                                             #
    # ------------------------------------------------------------------ #
    op.alter_column(
        "corrections",
        "created_at",
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.create_index("ix_corrections_invoice_id", "corrections", ["invoice_id"])
    op.create_foreign_key(
        "fk_corrections_invoice_id",
        "corrections",
        "invoices",
        ["invoice_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # ------------------------------------------------------------------ #
    # audit_events — FK (invoice_id already indexed in migration 0001)     #
    # ------------------------------------------------------------------ #
    op.alter_column(
        "audit_events",
        "ts",
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.create_foreign_key(
        "fk_audit_events_invoice_id",
        "audit_events",
        "invoices",
        ["invoice_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ------------------------------------------------------------------ #
    # comments — new table                                                 #
    # ------------------------------------------------------------------ #
    op.create_table(
        "comments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("invoice_id", sa.String(), nullable=False),
        sa.Column("author", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoices.id"],
            name="fk_comments_invoice_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comments_invoice_id", "comments", ["invoice_id"])


def downgrade() -> None:
    # comments
    op.drop_index("ix_comments_invoice_id", table_name="comments")
    op.drop_table("comments")

    # audit_events
    op.drop_constraint("fk_audit_events_invoice_id", "audit_events", type_="foreignkey")
    op.alter_column(
        "audit_events",
        "ts",
        type_=sa.DateTime(timezone=False),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )

    # corrections
    op.drop_constraint("fk_corrections_invoice_id", "corrections", type_="foreignkey")
    op.drop_index("ix_corrections_invoice_id", table_name="corrections")
    op.alter_column(
        "corrections",
        "created_at",
        type_=sa.DateTime(timezone=False),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )

    # invoices
    op.drop_constraint("ck_invoices_verdict", "invoices", type_="check")
    op.drop_constraint("ck_invoices_status", "invoices", type_="check")
    op.drop_constraint("fk_invoices_vendor_id", "invoices", type_="foreignkey")
    op.drop_constraint("fk_invoices_matched_po_id", "invoices", type_="foreignkey")
    op.drop_index("ix_invoices_is_deleted", table_name="invoices")
    op.drop_index("ix_invoices_created_at", table_name="invoices")
    op.drop_index("ix_invoices_vendor", table_name="invoices")
    op.drop_index("ix_invoices_status", table_name="invoices")
    op.alter_column(
        "invoices",
        "created_at",
        type_=sa.DateTime(timezone=False),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.drop_column("invoices", "updated_at")
    op.drop_column("invoices", "is_deleted")
    op.drop_column("invoices", "vendor_id")
    op.drop_column("invoices", "decision_reason")
    op.drop_column("invoices", "decided_at")
    op.drop_column("invoices", "decided_by")
