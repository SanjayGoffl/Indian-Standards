"""
SQLAlchemy model for Query Analytics.
"""

from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.core.database import Base


class QueryAnalytics(Base):
    """
    Stores analytics information for every user query.
    """

    __tablename__ = "query_analytics"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    user_id = Column(
        String(36),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    conversation_id = Column(
        String(36),
        ForeignKey(
            "conversations.id",
            ondelete="SET NULL",
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

    response_status = Column(
        String(50),
        nullable=False,
        default="answered",
        index=True,
    )

    confidence_score = Column(
        Float,
        nullable=True,
    )

    response_time = Column(
        Float,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        index=True,
    )