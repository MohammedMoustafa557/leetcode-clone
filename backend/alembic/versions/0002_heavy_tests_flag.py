"""flag problems with unusually heavy test suites

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-25 23:40:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("problems") as batch_op:
        batch_op.add_column(sa.Column("heavy_tests", sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("problems") as batch_op:
        batch_op.drop_column("heavy_tests")
