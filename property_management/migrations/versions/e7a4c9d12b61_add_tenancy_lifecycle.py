"""Add tenancy lifecycle and automatic billing fields.

Revision ID: e7a4c9d12b61
Revises: d9e31b7c4f52
Create Date: 2026-10-06
"""
from alembic import op
import sqlalchemy as sa

revision = "e7a4c9d12b61"
down_revision = "d9e31b7c4f52"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tenancy",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("unit_id", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("auto_invoice", sa.Boolean(), nullable=False),
        sa.Column("next_invoice_date", sa.Date(), nullable=True),
        sa.Column("last_invoice_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.ForeignKeyConstraint(["unit_id"], ["unit.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("invoice", schema=None) as batch_op:
        batch_op.add_column(sa.Column("tenancy_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("billing_period", sa.String(length=7), nullable=True))
        batch_op.add_column(sa.Column("invoice_type", sa.String(length=30), nullable=False, server_default="Monthly Rent"))
        batch_op.create_foreign_key("fk_invoice_tenancy", "tenancy", ["tenancy_id"], ["id"])


def downgrade():
    with op.batch_alter_table("invoice", schema=None) as batch_op:
        batch_op.drop_constraint("fk_invoice_tenancy", type_="foreignkey")
        batch_op.drop_column("invoice_type")
        batch_op.drop_column("billing_period")
        batch_op.drop_column("tenancy_id")
    op.drop_table("tenancy")
