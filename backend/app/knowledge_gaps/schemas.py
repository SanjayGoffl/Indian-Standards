from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgeGapCreate(BaseModel):
    query_text: str = Field(
        ...,
        min_length=1,
    )

    query_type: str | None = None

    reason: str

    confidence_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )


class KnowledgeGapResponse(BaseModel):
    id: int
    query_text: str
    query_type: str | None
    reason: str
    confidence_score: float | None
    occurrence_count: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KnowledgeGapStatistics(BaseModel):
    total_gaps: int
    open_gaps: int
    resolved_gaps: int
    most_common_reason: str | None