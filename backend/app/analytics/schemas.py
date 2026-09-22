"""
Pydantic schemas for Query Analytics.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class QueryAnalyticsCreate(BaseModel):
    """
    Data required to store analytics for a query.
    """

    user_id: str

    conversation_id: str | None = None

    query_text: str = Field(
        ...,
        min_length=1,
    )

    query_type: str | None = None

    response_status: str = "answered"

    confidence_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    response_time: float | None = Field(
        default=None,
        ge=0.0,
    )


class QueryAnalyticsResponse(BaseModel):
    """
    Response returned for a stored analytics record.
    """

    id: int
    user_id: str
    conversation_id: str | None
    query_text: str
    query_type: str | None
    response_status: str
    confidence_score: float | None
    response_time: float | None
    created_at: datetime

    class Config:
        from_attributes = True


class AnalyticsOverview(BaseModel):
    """
    Overall query analytics statistics.
    """

    total_queries: int
    answered_queries: int
    unanswered_queries: int
    average_confidence: float | None
    average_response_time: float | None

class QueryThemeResponse(BaseModel):
    """Semantic common-query theme and theme-level knowledge-gap metrics."""

    theme: str
    query_count: int
    query_share_pct: float
    unanswered_count: int
    low_confidence_count: int
    average_confidence: float | None
    gap_score: float
    knowledge_gap: bool
    representative_query: str
    queries: list[str]
