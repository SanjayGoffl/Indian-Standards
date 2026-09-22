"""
Shared workflow state for Milestone 2 + Milestone 3.

Milestone 2 fields are preserved:
    query
    k
    query_analysis
    route
    route_reason
    retrieval_result
    response
    error

Milestone 3 fields:
    conversation_id
    memory_context
    clarification_required
    clarification_question
    clarification_answer
    original_query
    refined_query

Internal runtime field:
    _db
        SQLAlchemy session supplied by the API layer.
        This is used only by the Memory nodes.
"""

from __future__ import annotations

from typing import Any, TypedDict

from sqlalchemy.orm import Session

from app.agents.query_understanding.schemas import (
    QueryUnderstandingResult,
)


class WorkflowState(TypedDict, total=False):
    # ==============================================================
    # Milestone 2 - Core query
    # ==============================================================

    query: str
    k: int
    user_id: str

    # ==============================================================
    # Milestone 2 - Query Understanding
    # ==============================================================

    query_analysis: QueryUnderstandingResult

    # ==============================================================
    # Milestone 2 - Routing
    # ==============================================================

    route: str
    route_reason: str

    # ==============================================================
    # Milestone 2 - Retrieval
    # ==============================================================

    retrieval_result: dict[str, Any]

    # ==============================================================
    # Milestone 2 - Response Generation
    # ==============================================================

    response: dict[str, Any]

    # ==============================================================
    # Shared error state
    # ==============================================================

    error: str

    # ==============================================================
    # Milestone 3 - Conversation Memory
    # ==============================================================

    conversation_id: str
    memory_context: list[dict[str, Any]]

    # ==============================================================
    # Milestone 3 - Clarification
    # ==============================================================

    clarification_required: bool
    clarification_question: str
    clarification_answer: str

    # Query before clarification.
    original_query: str

    # Query after clarification.
    refined_query: str

    # ==============================================================
    # Internal runtime dependency
    # ==============================================================
    #
    # Supplied by FastAPI / run_workflow().
    # It should NOT be returned to the frontend.
    #

    _db: Session