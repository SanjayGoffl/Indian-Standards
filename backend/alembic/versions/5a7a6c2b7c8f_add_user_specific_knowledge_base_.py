"""add user specific knowledge base documents

Revision ID: 5a7a6c2b7c8f
Revises: 7c91f9e3a2b4
Create Date: 2026-09-10 00:38:07.816531

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5a7a6c2b7c8f"
down_revision: Union[str, Sequence[str], None] = "7c91f9e3a2b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the user-specific knowledge base documents table."""

    op.create_table(
        "knowledge_base_documents",
        sa.Column(
            "id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "filename",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "original_filename",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "file_type",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column(
            "file_size",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="processing",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_knowledge_base_documents_user_id",
        "knowledge_base_documents",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the user-specific knowledge base documents table."""

    op.drop_index(
        "ix_knowledge_base_documents_user_id",
        table_name="knowledge_base_documents",
    )

    op.drop_table("knowledge_base_documents")