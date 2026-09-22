from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class SourceChunk(BaseModel):
    """
    Represents one source chunk retrieved from
    the knowledge base.
    """

    document: str = Field(
        default="Unknown source",
        description="Name of the source document",
    )

    page: Optional[int] = Field(
        default=None,
        description="Page number of the source document",
    )

    chunk_id: Optional[str] = Field(
        default=None,
        description="Unique identifier of the retrieved chunk",
    )

    content: str = Field(
        default="",
        description="Text content of the retrieved chunk",
    )

    relevance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Relevance score of the retrieved chunk",
    )

    citation: str = Field(
        default="Unknown source",
        description="Human-readable citation",
    )


class TransparencyResponse(BaseModel):
    """
    Response transparency information.

    This contains the evidence and confidence
    information associated with an AI response.
    """

    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall retrieval-based confidence",
    )

    confidence_level: str = Field(
        default="Low",
        description="High, Medium, or Low",
    )

    sources: List[SourceChunk] = Field(
        default_factory=list,
        description="Retrieved source chunks",
    )
