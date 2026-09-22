"""add milestone 4 analytics and knowledge gaps

Revision ID: 7c91f9e3a2b4
Revises: 0f628c51b660
Create Date: 2026-09-09

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7c91f9e3a2b4"
down_revision: Union[str, Sequence[str], None] = "0f628c51b660"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Milestone 4 analytics and knowledge-gap tables."""

    # ------------------------------------------------------------
    # Query analytics
    # ------------------------------------------------------------
    op.create_table(
        "query_analytics",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "conversation_id",
            sa.String(length=36),
            nullable=True,
        ),
        sa.Column(
            "query_text",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "query_type",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "response_status",
            sa.String(length=50),
            nullable=False,
            server_default="answered",
        ),
        sa.Column(
            "confidence_score",
            sa.Float(),
            nullable=True,
        ),
        sa.Column(
            "response_time",
            sa.Float(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_query_analytics_user_id",
        "query_analytics",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_query_analytics_conversation_id",
        "query_analytics",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        "ix_query_analytics_query_type",
        "query_analytics",
        ["query_type"],
        unique=False,
    )
    op.create_index(
        "ix_query_analytics_response_status",
        "query_analytics",
        ["response_status"],
        unique=False,
    )
    op.create_index(
        "ix_query_analytics_created_at",
        "query_analytics",
        ["created_at"],
        unique=False,
    )

    # ------------------------------------------------------------
    # Knowledge gaps
    # ------------------------------------------------------------
    op.create_table(
        "knowledge_gaps",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "query_text",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "query_type",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "reason",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "confidence_score",
            sa.Float(),
            nullable=True,
        ),
        sa.Column(
            "occurrence_count",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="open",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_knowledge_gaps_query_type",
        "knowledge_gaps",
        ["query_type"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_gaps_status",
        "knowledge_gaps",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_gaps_created_at",
        "knowledge_gaps",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_knowledge_gaps_updated_at",
        "knowledge_gaps",
        ["updated_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop Milestone 4 analytics and knowledge-gap tables."""

    op.drop_index(
        "ix_knowledge_gaps_updated_at",
        table_name="knowledge_gaps",
    )
    op.drop_index(
        "ix_knowledge_gaps_created_at",
        table_name="knowledge_gaps",
    )
    op.drop_index(
        "ix_knowledge_gaps_status",
        table_name="knowledge_gaps",
    )
    op.drop_index(
        "ix_knowledge_gaps_query_type",
        table_name="knowledge_gaps",
    )
    op.drop_table("knowledge_gaps")

    op.drop_index(
        "ix_query_analytics_created_at",
        table_name="query_analytics",
    )
    op.drop_index(
        "ix_query_analytics_response_status",
        table_name="query_analytics",
    )
    op.drop_index(
        "ix_query_analytics_query_type",
        table_name="query_analytics",
    )
    op.drop_index(
        "ix_query_analytics_conversation_id",
        table_name="query_analytics",
    )
    op.drop_index(
        "ix_query_analytics_user_id",
        table_name="query_analytics",
    )
    op.drop_table("query_analytics")
