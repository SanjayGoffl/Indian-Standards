"""
Milestone 3 - LangGraph orchestration workflow.

Milestone 2 path:

    Query
      ↓
    Query Understanding
      ↓
    Query Router
      ↓
    Retrieval
      ↓
    Response Generation
      ↓
    Final Result

Milestone 3 additions:

    Conversation Memory
      ↓
    Clarification Agent
      ↓
    Query refinement
      ↓
    Retrieval
      ↓
    Response Generation
      ↓
    Conversation Memory

Important:
    Existing Milestone 2 retrieval and response-generation logic
    is preserved. Milestone 3 adds memory and clarification
    around the existing path.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session
from langgraph.graph import END, START, StateGraph

from app.orchestration.state import WorkflowState

from app.orchestration.nodes import (
    memory_node,
    query_understanding_node,
    routing_node,
    clarification_node,
    retrieval_node,
    response_generation_node,
    general_response_node,
    save_memory_node,
)

# Conditional decisions
def route_after_memory(
    state: WorkflowState,
) -> str:
    """
    Decide what happens after loading conversation memory.

    New query:
        -> Query Understanding

    Query that contains a clarification answer:
        -> Clarification refinement
    """

    if state.get("error"):
        return "end"

    clarification_answer = state.get(
        "clarification_answer",
        "",
    )

    original_query = state.get(
        "original_query",
        "",
    )

    clarification_question = state.get(
        "clarification_question",
        "",
    )

    # A clarification answer means this is the second
    # part of a previous ambiguous-query interaction.
    if (
        clarification_answer
        and original_query
        and clarification_question
    ):
        return "clarification"

    return "query_understanding"

def route_after_routing(
    state: WorkflowState,
) -> str:
    """
    Decide whether the query should go to Retrieval
    or Clarification.
    """

    if state.get("error"):
        return "end"

    route = state.get(
        "route",
        "retrieval",
    )

    if route == "clarification":
        return "clarification"

    if route == "retrieval":
        return "retrieval"

    if route == "general":
        return "general_response"
    
    # Safe fallback.
    return "retrieval"

def route_after_clarification(
    state: WorkflowState,
) -> str:
    """
    Decide whether clarification is complete.

    First clarification pass:
        clarification_required = True
        no refined_query
            -> END

    Clarification response/refinement:
        refined_query exists
            -> Query Understanding again
    """

    if state.get("error"):
        return "end"

    refined_query = state.get(
        "refined_query",
        "",
    )

    if refined_query:
        return "query_understanding"

    if state.get(
        "clarification_required"
    ):
        return "end"

    return "end"

def route_after_response(
    state: WorkflowState,
) -> str:
    """
    Decide whether the completed response should be
    persisted in conversation memory.
    """

    if state.get("error"):
        return "end"

    if state.get("conversation_id"):
        return "save_memory"

    return "end"

def route_after_save_memory(
    state: WorkflowState,
) -> str:
    """
    Final workflow transition after memory persistence.
    """

    return "end"

# Graph construction
def build_workflow():
    """
    Build and compile the Milestone 3 LangGraph workflow.
    """
    graph = StateGraph(
        WorkflowState
    )

    # Nodes
    graph.add_node(
        "memory",
        memory_node,
    )

    graph.add_node(
        "query_understanding",
        query_understanding_node,
    )

    graph.add_node(
        "routing",
        routing_node,
    )

    graph.add_node(
        "clarification",
        clarification_node,
    )

    graph.add_node(
        "retrieval",
        retrieval_node,
    )

    graph.add_node(
        "response_generation",
        response_generation_node,
    )

    graph.add_node(
    "general_response",
    general_response_node,
    )

    graph.add_node(
        "save_memory",
        save_memory_node,
    )

    # START → Memory
    graph.add_edge(
        START,
        "memory",
    )

    # Memory → New Query OR Clarification Refinement
    graph.add_conditional_edges(
        "memory",
        route_after_memory,
        {
            "query_understanding": (
                "query_understanding"
            ),
            "clarification": "clarification",
            "end": END,
        },
    )

    # Query Understanding → Routing
    graph.add_edge(
        "query_understanding",
        "routing",
    )

    # Routing → Retrieval OR Clarification
    graph.add_conditional_edges(
        "routing",
        route_after_routing,
        {
            "retrieval": "retrieval",
            "general_response": "general_response",
            "clarification": "clarification",
            "end": END,
        },
    )

    # Clarification → END OR Query Understanding
    graph.add_conditional_edges(
        "clarification",
        route_after_clarification,
        {
            "query_understanding": (
                "query_understanding"
            ),
            "end": END,
        },
    )

    # Retrieval → Response Generation
    graph.add_edge(
        "retrieval",
        "response_generation",
    )

    # General Response → Save Memory OR END
    graph.add_conditional_edges(
        "general_response",
        route_after_response,
        {
            "save_memory": "save_memory",
            "end": END,
        },
    )

    # Response Generation → Save Memory OR END
    graph.add_conditional_edges(
        "response_generation",
        route_after_response,
        {
            "save_memory": "save_memory",
            "end": END,
        },
    )

    # Save Memory → END
    graph.add_conditional_edges(
        "save_memory",
        route_after_save_memory,
        {
            "end": END,
        },
    )

    return graph.compile()

# Compile once and reuse
workflow = build_workflow()

# Public workflow API
def run_workflow(
    query: str,
    k: int = 3,
    conversation_id: str | None = None,
    clarification_answer: str | None = None,
    clarification_question: str | None = None,
    original_query: str | None = None,
    user_id: str | None = None,
    db: Session | None = None,
) -> dict[str, Any]:
    """
    Run the Milestone 3 workflow.

    Parameters
    ----------
    query:
        Current user query.

    k:
        Maximum number of chunks retrieved.

    conversation_id:
        Conversation identifier used by the Memory Agent.

    clarification_answer:
        User's answer to a previous clarification question.

    clarification_question:
        Previously generated clarification question.

    original_query:
        Original ambiguous query.

    db:
        SQLAlchemy database session used by the Memory Agent.

        It is optional to preserve backward compatibility with
        the existing Milestone 2 workflow.

    Returns
    -------
    dict[str, Any]
        Final LangGraph workflow state.
    """

    # Validate query
    if not isinstance(
        query,
        str,
    ) or not query.strip():

        raise ValueError(
            "Query cannot be empty."
        )

    # Validate k
    if (
        not isinstance(k, int)
        or isinstance(k, bool)
    ):
        raise ValueError(
            "k must be an integer."
        )

    if k < 1:
        raise ValueError(
            "k must be at least 1."
        )
    
    # Initial workflow state
    initial_state: WorkflowState = {
        "query": query.strip(),
        "k": k,
        "user_id": user_id if user_id else "",
    }

    # Optional Milestone 3 values
    if conversation_id:
        initial_state[
            "conversation_id"
        ] = conversation_id.strip()

    if clarification_answer:
        initial_state[
            "clarification_answer"
        ] = clarification_answer.strip()

    if clarification_question:
        initial_state[
            "clarification_question"
        ] = clarification_question.strip()

    if original_query:
        initial_state[
            "original_query"
        ] = original_query.strip()

    # Internal database session.
    # This is consumed by memory_node/save_memory_node.
    # It is not intended for the frontend response.
    if db is not None:
        initial_state["_db"] = db

    # Execute graph
    result = workflow.invoke(
        initial_state
    )

    return dict(result)

# Standalone tests
if __name__ == "__main__":

    print("=" * 70)
    print("MILESTONE 3 WORKFLOW TEST")
    print("=" * 70)

    # Test 1: Existing M2 clear query
    print(
        "\nTEST 1 - Clear factual query"
    )

    result = run_workflow(
        "What does the Retrieval Agent do?",
        k=3,
    )

    print(
        "Route:",
        result.get("route"),
    )

    print(
        "Route Reason:",
        result.get("route_reason"),
    )

    print(
        "\nRetrieval Results:"
    )

    retrieval = result.get(
        "retrieval_result",
        {}
    )

    print(
        retrieval.get(
            "results",
            []
        )
    )
    
    print(
        "Response:",
        result.get("response"),
    )

    if result.get("error"):
        print(
            "ERROR:",
            result["error"],
        )

    # Test 2: Ambiguous query
    print(
        "\nTEST 2 - Ambiguous query"
    )

    result = run_workflow(
        "Tell me more about that.",
        k=3,
    )

    print(
        "Route:",
        result.get("route"),
    )

    print(
        "Clarification Required:",
        result.get(
            "clarification_required"
        ),
    )

    print(
        "Clarification Question:",
        result.get(
            "clarification_question"
        ),
    )

    if result.get("error"):
        print(
            "ERROR:",
            result["error"],
        )