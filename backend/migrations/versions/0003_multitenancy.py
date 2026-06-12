"""multitenancy — add organizations table, org_id + role to users, org_id to all entity tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-12 00:02:00.000000

Strategy for existing data
--------------------------
1. Create the ``organizations`` table.
2. Insert the demo org row (id = 'org-demo', name = 'Zamp Demo').
3. Add ``org_id`` as nullable to users, vendors, purchase_orders, invoices,
   corrections, rules, audit_events, comments.
4. Backfill every existing row with 'org-demo'.
5. Set NOT NULL on those columns.
6. Add ``role`` column to users (nullable first, default 'member', then NOT NULL).
7. Add indexes.
8. Add FK constraints.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | None = None
depends_on: str | None = None

_DEMO_ORG_ID = "org-demo"
_DEMO_ORG_NAME = "Zamp Demo"

# Tables that get an org_id column (ordered so FKs can be added after backfill)
_ORG_TABLES = [
    "users",
    "vendors",
    "purchase_orders",
    "invoices",
    "corrections",
    "rules",
    "audit_events",
    "comments",
]


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Create organizations table
    # ------------------------------------------------------------------
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_organizations_name"), "organizations", ["name"], unique=True)

    # ------------------------------------------------------------------
    # 2. Insert the demo org so backfill FK references are valid
    # ------------------------------------------------------------------
    op.execute(
        sa.text(
            "INSERT INTO organizations (id, name) VALUES (:id, :name) "
            "ON CONFLICT (id) DO NOTHING"
        ).bindparams(id=_DEMO_ORG_ID, name=_DEMO_ORG_NAME)
    )

    # ------------------------------------------------------------------
    # 3. Add org_id (nullable, no FK yet) to each entity table
    # ------------------------------------------------------------------
    for table in _ORG_TABLES:
        op.add_column(table, sa.Column("org_id", sa.String(), nullable=True))

    # ------------------------------------------------------------------
    # 4. Backfill all existing rows with the demo org id
    # ------------------------------------------------------------------
    for table in _ORG_TABLES:
        op.execute(sa.text(f"UPDATE {table} SET org_id = :oid").bindparams(oid=_DEMO_ORG_ID))

    # ------------------------------------------------------------------
    # 5. Set NOT NULL on org_id for all tables except audit_events
    #    (audit_events org_id can remain nullable — global system events)
    # ------------------------------------------------------------------
    not_null_tables = [t for t in _ORG_TABLES if t != "audit_events"]
    for table in not_null_tables:
        op.alter_column(table, "org_id", nullable=False)

    # ------------------------------------------------------------------
    # 6. Add role column to users
    # ------------------------------------------------------------------
    op.add_column(
        "users",
        sa.Column("role", sa.String(), nullable=True),
    )
    op.execute(sa.text("UPDATE users SET role = 'admin' WHERE id = 'usr-demo0001'"))
    op.execute(sa.text("UPDATE users SET role = 'member' WHERE role IS NULL"))
    op.alter_column("users", "role", nullable=False)

    # ------------------------------------------------------------------
    # 7. Indexes
    # ------------------------------------------------------------------
    op.create_index("ix_users_org_id", "users", ["org_id"])
    op.create_index("ix_vendors_org_id", "vendors", ["org_id"])
    op.create_index("ix_purchase_orders_org_id", "purchase_orders", ["org_id"])
    op.create_index("ix_invoices_org_id", "invoices", ["org_id"])
    op.create_index("ix_corrections_org_id", "corrections", ["org_id"])
    op.create_index("ix_rules_org_id", "rules", ["org_id"])
    op.create_index("ix_audit_events_org_id", "audit_events", ["org_id"])
    op.create_index("ix_comments_org_id", "comments", ["org_id"])

    # ------------------------------------------------------------------
    # 8. FK constraints
    # ------------------------------------------------------------------
    op.create_foreign_key(
        "fk_users_org_id", "users", "organizations", ["org_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_vendors_org_id", "vendors", "organizations", ["org_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_purchase_orders_org_id",
        "purchase_orders",
        "organizations",
        ["org_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_invoices_org_id", "invoices", "organizations", ["org_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_corrections_org_id",
        "corrections",
        "organizations",
        ["org_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_rules_org_id", "rules", "organizations", ["org_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_audit_events_org_id",
        "audit_events",
        "organizations",
        ["org_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_comments_org_id",
        "comments",
        "organizations",
        ["org_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # Drop FKs
    for table, fk in [
        ("comments", "fk_comments_org_id"),
        ("audit_events", "fk_audit_events_org_id"),
        ("rules", "fk_rules_org_id"),
        ("corrections", "fk_corrections_org_id"),
        ("invoices", "fk_invoices_org_id"),
        ("purchase_orders", "fk_purchase_orders_org_id"),
        ("vendors", "fk_vendors_org_id"),
        ("users", "fk_users_org_id"),
    ]:
        op.drop_constraint(fk, table, type_="foreignkey")

    # Drop indexes
    for table in _ORG_TABLES:
        op.drop_index(f"ix_{table}_org_id", table_name=table)

    # Drop role from users
    op.drop_column("users", "role")

    # Drop org_id columns
    for table in _ORG_TABLES:
        op.drop_column(table, "org_id")

    # Drop organizations table
    op.drop_index(op.f("ix_organizations_name"), table_name="organizations")
    op.drop_table("organizations")
