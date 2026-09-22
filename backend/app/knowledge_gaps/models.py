from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    ForeignKey,
)
from sqlalchemy.sql import func

from app.core.database import Base


class KnowledgeGap(Base):
    """Stores queries that indicate missing knowledge for a user."""

    __tablename__ = "knowledge_gaps"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # User ownership.
    #
    # Nullable is intentional for compatibility with existing
    # historical knowledge-gap records created before user-specific
    # ownership was introduced.
    user_id = Column(
        String(36),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    query_text = Column(
        Text,
        nullable=False,
    )

    query_type = Column(
        String(100),
        nullable=True,
        index=True,
    )

    reason = Column(
        String(255),
        nullable=False,
    )

    confidence_score = Column(
        Float,
        nullable=True,
    )

    occurrence_count = Column(
        Integer,
        nullable=False,
        default=1,
    )

    status = Column(
        String(50),
        nullable=False,
        default="open",
        index=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        index=True,
    )