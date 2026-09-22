"""
Pydantic request models for the FastAPI API layer.

Milestone 2:
    - query
    - k

Milestone 3:
    - conversation_id
    - clarification_answer
    - clarification_question
    - original_query
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """
    Request model for the /query endpoint.

    The Milestone 2 fields remain unchanged for backward compatibility.
    Milestone 3 fields are optional so existing single-query requests
    continue to work.
    """

    # ------------------------------------------------------------------
    # Milestone 2
    # ------------------------------------------------------------------

    query: str = Field(
        min_length=1,
        description="User's natural-language query.",
    )

    k: int = Field(
        default=3,
        ge=1,
        description="Maximum number of retrieval chunks.",
    )

    # ------------------------------------------------------------------
    # Milestone 3 - Conversation Memory
    # ------------------------------------------------------------------

    conversation_id: str | None = Field(
        default=None,
        min_length=1,
        description=(
            "Identifier of the conversation used to load and "
            "persist conversation history."
        ),
    )

    # ------------------------------------------------------------------
    # Milestone 3 - Clarification
    # ------------------------------------------------------------------

    clarification_answer: str | None = Field(
        default=None,
        min_length=1,
        description=(
            "User's answer to a previously generated clarification question."
        ),
    )

    clarification_question: str | None = Field(
        default=None,
        min_length=1,
        description=(
            "Previously generated clarification question associated "
            "with the original ambiguous query."
        ),
    )

    original_query: str | None = Field(
        default=None,
        min_length=1,
        description=(
            "Original query that required clarification."
        ),
    )