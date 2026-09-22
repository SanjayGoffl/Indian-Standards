"""
Schemas used by the Response Generation Agent.

The schemas preserve:

- grounded answer
- source citation
- source/chunk identity
- retrieval relevance
- source metadata
- confidence score
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Source(BaseModel):
    """
    A source referenced by the generated answer.
    """

    source: str = Field(
        description=(
            "Human-readable source name, "
            "usually the uploaded filename."
        )
    )

    reference: str = Field(
        description=(
            "Citation marker used in the answer, "
            "for example [1]."
        )
    )

    chunk_id: str | None = Field(
        default=None,
        description=(
            "Unique identifier of the retrieved chunk."
        )
    )

    relevance_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Retrieval relevance score of the cited chunk."
        )
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Metadata associated with the cited chunk."
        )
    )


class LLMResponse(BaseModel):
    """
    Final response returned by the Response Generation Agent.
    """

    answer: str = Field(
        description=(
            "Grounded answer generated only from "
            "the retrieved context."
        )
    )

    sources: list[Source] = Field(
        default_factory=list,
        description=(
            "Retrieved chunks explicitly cited "
            "by the generated answer."
        )
    )

    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Heuristic confidence based on retrieved evidence "
            "quality and citation coverage. Null for responses "
            "that do not use knowledge-base retrieval."
        )
    )


if __name__ == "__main__":

    response = LLMResponse(
        answer=(
            "The Retrieval Agent performs semantic "
            "search and ranks retrieved chunks "
            "by relevance. [1]"
        ),
        sources=[
            Source(
                source="project.pdf",
                reference="[1]",
                chunk_id="chunk_001",
                relevance_score=0.91,
                metadata={
                    "filename": "project.pdf",
                    "chunk_index": 2,
                },
            )
        ],
        confidence=0.91,
    )

    print(
        "Schema validation successful!"
    )

    print()

    print(
        response.model_dump_json(
            indent=4
        )
    )