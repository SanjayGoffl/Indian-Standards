"""
Milestone 3 - Query Routing.

Responsibilities:
    - Decide whether a query follows the retrieval path
      or the clarification path.
    - Remain deterministic.
    - Perform no LLM calls.

Milestone 3 routing:

    factual
        -> retrieval

    procedural
        -> retrieval

    comparative
        -> retrieval

    ambiguous
        -> clarification
"""

from __future__ import annotations
from typing import Literal
from app.agents.query_understanding.schemas import (
    QueryUnderstandingResult,
)

# Supported route names
RouteName = Literal[
    "retrieval",
    "general",
    "clarification",
]

# Query categories that use the Retrieval Agent
SUPPORTED_RETRIEVAL_TYPES = {
    "factual",
    "procedural",
    "comparative",
}

AMBIGUOUS_QUERY_TYPE = "ambiguous"

# Normalize query type
def normalize_query_type(
    query_type: str | None,
) -> str:
    """
    Normalize the query type returned by Query Understanding.

    Missing or invalid values safely fall back to "ambiguous".
    """
    if not isinstance(query_type, str):
        return AMBIGUOUS_QUERY_TYPE
    normalized = query_type.strip().lower()
    if not normalized:
        return AMBIGUOUS_QUERY_TYPE

    return normalized

# Main routing function
def route_query(
    query_analysis: QueryUnderstandingResult,
) -> RouteName:
    """
    Select the next resolution path.

    Milestone 3 behavior:

        factual       -> retrieval
        procedural    -> retrieval
        comparative   -> retrieval
        ambiguous     -> clarification

    Unknown query types safely fall back to retrieval so that
    unexpected classifier output does not break the existing
    Milestone 2 resolution path.
    """

    if not isinstance(
        query_analysis,
        QueryUnderstandingResult,
    ):
        raise TypeError(
            "query_analysis must be a "
            "QueryUnderstandingResult."
        )

    query_type = normalize_query_type(
        query_analysis.query_type
    )

    # Existing Milestone 2 retrieval path.
    if query_type in SUPPORTED_RETRIEVAL_TYPES:
        return "retrieval"

    # General-knowledge / conversational path.
    if query_type == "general":
        return "general"

    # New Milestone 3 clarification path.
    if query_type == AMBIGUOUS_QUERY_TYPE:
        return "clarification"

    # Safe fallback.
    return "retrieval"

# Human-readable route reason
def get_route_reason(
    query_analysis: QueryUnderstandingResult,
) -> str:
    """
    Return a human-readable explanation of the selected route.
    """

    query_type = normalize_query_type(
        query_analysis.query_type
    )

    if query_type == "factual":
        return (
            "Factual query routed to "
            "semantic/exact retrieval."
        )

    if query_type == "procedural":
        return (
            "Procedural query routed to "
            "semantic/exact retrieval."
        )

    if query_type == "comparative":
        return (
            "Comparative query routed to "
            "semantic/exact retrieval."
        )

    if query_type == "general":
        return (
            "General knowledge query routed directly "
            "to the LLM."
        )

    if query_type == "ambiguous":
        return (
            "Ambiguous query routed to the "
            "Clarification Agent."
        )

    return (
        "Unknown query type safely routed to retrieval."
    )

# Standalone test
if __name__ == "__main__":

    test_cases = [
        "factual",
        "procedural",
        "comparative",
        "general",
        "ambiguous",
    ]

    for query_type in test_cases:

        analysis = QueryUnderstandingResult(
            original_query="Test query",
            normalized_query="Test query",
            search_query="Test query",
            query_type=query_type,
            entities=[],
            keywords=["test"],
            exact_terms=[],
        )

        print(
            f"{query_type:12} -> "
            f"{route_query(analysis)}"
        )

        print(
            "Reason:",
            get_route_reason(analysis),
        )

        print()