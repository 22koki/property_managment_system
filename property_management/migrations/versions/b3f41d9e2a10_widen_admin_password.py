"""Widen admin password column for secure hashes.

Revision ID: b3f41d9e2a10
Revises: 62372b905f6f
Create Date: 2026-10-06
"""
from alembic import op
import sqlalchemy as sa

revision = "b3f41d9e2a10"
down_revision = "62372b905f6f"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("admin", schema=None) as batch_op:
        batch_op.alter_column(
            "password",
            existing_type=sa.String(length=100),
            type_=sa.String(length=255),
            existing_nullable=False,
        )


def downgrade():
    with op.batch_alter_table("admin", schema=None) as batch_op:
        batch_op.alter_column(
            "password",
            existing_type=sa.String(length=255),
            type_=sa.String(length=100),
            existing_nullable=False,
        )
