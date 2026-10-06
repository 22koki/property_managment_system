"""Add billing and payment metadata.

Revision ID: d9e31b7c4f52
Revises: b3f41d9e2a10
Create Date: 2026-10-06
"""
from alembic import op
import sqlalchemy as sa

revision = "d9e31b7c4f52"
down_revision = "b3f41d9e2a10"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("invoice", schema=None) as batch_op:
        batch_op.add_column(sa.Column("issued_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("due_date", sa.Date(), nullable=True))
    with op.batch_alter_table("maintenance_request", schema=None) as batch_op:
        batch_op.add_column(sa.Column("created_at", sa.DateTime(), nullable=True))
    with op.batch_alter_table("receipt", schema=None) as batch_op:
        batch_op.add_column(sa.Column("payment_method", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("transaction_reference", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("created_at", sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table("receipt", schema=None) as batch_op:
        batch_op.drop_column("created_at")
        batch_op.drop_column("transaction_reference")
        batch_op.drop_column("payment_method")
    with op.batch_alter_table("maintenance_request", schema=None) as batch_op:
        batch_op.drop_column("created_at")
    with op.batch_alter_table("invoice", schema=None) as batch_op:
        batch_op.drop_column("due_date")
        batch_op.drop_column("issued_at")
