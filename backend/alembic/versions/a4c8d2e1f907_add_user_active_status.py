"""add active status to users

Revision ID: a4c8d2e1f907
Revises: e9b7e767c397
Create Date: 2026-09-17 10:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a4c8d2e1f907"
down_revision: Union[str, Sequence[str], None] = "e9b7e767c397"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    # Existing rows are populated as active. New rows use the ORM default.
    op.alter_column("users", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "is_active")
