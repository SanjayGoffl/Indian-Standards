"""
LangGraph orchestration nodes.

Milestone 2:
    - Query Understanding
    - Routing
    - Retrieval
    - Response Generation

Milestone 3:
    - Load Conversation Memory
    - Context-aware follow-up query resolution
    - Clarification
    - Save Conversation Memory

Important:
    Agent business logic remains inside app/agents/.
    This module coordinates the agents and updates workflow state.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.agents.query_understanding.agent import (
    QueryUnderstandingAgent,
)
from app.agents.query_understanding.schemas import (
    QueryUnderstandingResult,
)

from app.agents.retrieval.agent import (
    RetrievalAgent,
)

from app.agents.response_generation.agent import (
    generate_response,
    is_insufficient_context_answer,
)

from app.agents.clarification.agent import (
    ClarificationAgent,
)
from app.agents.clarification.schemas import (
    QueryRefinementRequest,
)

from app.agents.memory.agent import (
    ConversationMemoryAgent,
)

from app.core.llm import get_llm

from app.orchestration.query_router import (
    get_route_reason,
    route_query,
)

from app.orchestration.state import WorkflowState


# =====================================================================
# Shared agent instances
# =====================================================================

_llm = get_llm()

_query_understanding_agent = QueryUnderstandingAgent(
    _llm
)

_retrieval_agent = RetrievalAgent(
    default_k=5,
    semantic_candidate_multiplier=5,
    relevance_threshold=0.10,  # permissive — reranker already sorts by score desc
    enable_diversification=True,
)

_clarification_agent = ClarificationAgent(
    _llm
)

_memory_agent = ConversationMemoryAgent()


# =====================================================================
# Internal helpers
# =====================================================================

def _get_db(
    state: WorkflowState,
) -> Session:
    """
    Get the SQLAlchemy session attached to the workflow state.
    """

    db = state.get("_db")

    if db is None:
        raise RuntimeError(
            "Database session is missing from workflow state."
        )

    return db


def _has_error(
    state: WorkflowState,
) -> bool:
    """Return True when a previous node has failed."""

    return bool(
        state.get("error")
    )


def _memory_has_context(
    state: WorkflowState,
) -> bool:
    """
    Return True when useful conversation context exists.
    """

    context = state.get(
        "memory_context",
        [],
    )

    return bool(context)


# =====================================================================
# Milestone 3 - Contextual Follow-up Resolution
# =====================================================================

def _resolve_contextual_query(
    query: str,
    memory_context: list[dict[str, Any]],
) -> str:
    """
    Convert a context-dependent follow-up query into a
    standalone query using recent conversation history.

    Example:

        Previous:
            User: What does the Retrieval Agent do?
            Assistant: It performs semantic search...

        Current:
            What about its ranking?

        Possible result:
            What is the ranking performed by the Retrieval Agent?

    If no conversation context exists, the original query is returned.
    """

    if not query.strip():
        return query

    if not memory_context:
        return query

    # Use the most recent few conversation turns.
    recent_context = memory_context[-3:]

    conversation_lines: list[str] = []

    for turn in recent_context:

        if not isinstance(
            turn,
            dict,
        ):
            continue

        user_message = turn.get(
            "user"
        )

        assistant_message = turn.get(
            "assistant"
        )

        if user_message:
            conversation_lines.append(
                f"User: {user_message}"
            )

        if assistant_message:
            conversation_lines.append(
                f"Assistant: {assistant_message}"
            )

    if not conversation_lines:
        return query

    conversation_text = "\n".join(
        conversation_lines
    )

    prompt = f"""
You are a query reformulation component in a RAG system.

Rewrite the current user query into a standalone search query
that can be understood without the previous conversation.

Use the previous conversation only to resolve references such as:
- it
- its
- this
- that
- they
- them
- the above
- the previous answer
- follow-up references

Do not answer the question.
Do not add information that is not supported by the conversation.
Keep the user's actual intent unchanged.

Previous conversation:
{conversation_text}

Current user query:
{query}

Return ONLY the standalone query.
"""

    try:
        response = _llm.invoke(
            prompt
        )

        standalone_query = getattr(
            response,
            "content",
            "",
        )

        if isinstance(
            standalone_query,
            list,
        ):
            standalone_query = " ".join(
                str(item)
                for item in standalone_query
            )

        if not isinstance(
            standalone_query,
            str,
        ):
            return query

        standalone_query = standalone_query.strip()

        if not standalone_query:
            return query

        return standalone_query

    except Exception:
        # Memory must never make a normal query fail.
        # Fall back to the original user query.
        return query



# =====================================================================
# Milestone 3 - Memory Node
# =====================================================================

def memory_node(
    state: WorkflowState,
) -> WorkflowState:
    """
    Load previous conversation context.

    No conversation_id:
        continue exactly like Milestone 2.

    Existing conversation_id:
        retrieve persisted context from the database.
    """

    if _has_error(state):
        return state

    conversation_id = state.get(
        "conversation_id"
    )

    # Preserve M2 behavior when memory is not requested.
    if not conversation_id:
        return {
            **state,
            "memory_context": [],
        }

    try:
        db = _get_db(
            state
        )
        
        context = _memory_agent.get_context(
            db=db,
            conversation_id=conversation_id,
        )

        return {
            **state,
            "memory_context": context,
        }

    except Exception as error:
        return {
            **state,
            "error": (
                f"Conversation Memory load failed: {error}"
            ),
        }


# =====================================================================
# Milestone 2 - Query Understanding Node
# =====================================================================

def query_understanding_node(
    state: WorkflowState,
) -> WorkflowState:
    """
    Run Query Understanding.

    For a normal M2 query:
        query -> Query Understanding

    For a context-dependent M3 follow-up:
        memory + query
            -> standalone query
            -> Query Understanding
    """

    try:
        query = state.get(
            "query",
            "",
        ).strip()

        if not query:
            raise ValueError(
                "Query cannot be empty."
            )

        # Resolve conversation context only for a normal query.
        # A clarification-refined query is already standalone and
        # must not be rewritten by memory a second time.

        memory_context = state.get(
            "memory_context",
            [],
        )

        if state.get("refined_query"):
            resolved_query = query
        else:
            resolved_query = _resolve_contextual_query(
                query=query,
                memory_context=memory_context,
            )

        # Keep the resolved query in the workflow state.
        result: WorkflowState = {
            **state,
            "query": resolved_query,
        }

        # -------------------------------------------------------------
        # Existing Query Understanding Agent remains unchanged.
        # -------------------------------------------------------------

        analysis = _query_understanding_agent.run(
            resolved_query
        )

        return {
            **result,
            "query_analysis": analysis,
        }

    except Exception as error:
        return {
            **state,
            "error": (
                f"Query Understanding failed: {error}"
            ),
        }


# =====================================================================
# Milestone 2 - Routing Node
# =====================================================================

def routing_node(
    state: WorkflowState,
) -> WorkflowState:
    """
    Run the deterministic query router.

    Clear queries:
        -> retrieval

    Ambiguous queries:
        -> clarification
    """

    if _has_error(state):
        return state

    analysis = state.get(
        "query_analysis"
    )

    if not isinstance(
        analysis,
        QueryUnderstandingResult,
    ):
        return {
            **state,
            "error": (
                "Invalid QueryUnderstandingResult "
                "received by router."
            ),
        }

    try:
        route = route_query(
            analysis
        )

        reason = get_route_reason(
            analysis
        )

        return {
            **state,
            "route": route,
            "route_reason": reason,
        }

    except Exception as error:
        return {
            **state,
            "error": (
                f"Query routing failed: {error}"
            ),
        }


# =====================================================================
# Milestone 3 - Clarification Node
# =====================================================================

def clarification_node(
    state: WorkflowState,
) -> WorkflowState:
    """
    Generate a clarification question or refine a query.

    First pass:
        ambiguous query
            -> clarification question

    Second pass:
        clarification answer
            -> refined query
    """

    if _has_error(state):
        return state

    clarification_answer = state.get(
        "clarification_answer",
        "",
    ).strip()

    original_query = state.get(
        "original_query",
        "",
    ).strip()

    clarification_question = state.get(
        "clarification_question",
        "",
    ).strip()

    # ================================================================
    # Case 1 - User answered clarification
    # ================================================================

    if clarification_answer:

        if not original_query:
            return {
                **state,
                "error": (
                    "Original query is required "
                    "for clarification refinement."
                ),
            }

        if not clarification_question:
            return {
                **state,
                "error": (
                    "Clarification question is required "
                    "for clarification refinement."
                ),
            }

        try:
            request = QueryRefinementRequest(
                conversation_id=state.get(
                    "conversation_id",
                    "",
                ),
                original_query=original_query,
                clarification_question=(
                    clarification_question
                ),
                user_response=clarification_answer,
            )

            result = (
                _clarification_agent.refine_query(
                    request
                )
            )

            refined_query = (
                result.refined_query.strip()
            )

            if not refined_query:
                raise ValueError(
                    "Clarification Agent returned "
                    "an empty refined query."
                )

            return {
                **state,
                "query": refined_query,
                "refined_query": refined_query,
                "clarification_required": False,
                "clarification_answer": "",
            }

        except Exception as error:
            return {
                **state,
                "error": (
                    f"Query Refinement failed: {error}"
                ),
            }

    # ================================================================
    # Case 2 - Generate clarification question
    # ================================================================

    query = state.get(
        "query",
        "",
    ).strip()

    if not query:
        return {
            **state,
            "error": (
                "Cannot generate clarification "
                "for an empty query."
            ),
        }

    try:

        question = (
            _clarification_agent
            .generate_question(query)
        )

        if (
            not question
            or not question.strip()
        ):
            raise ValueError(
                "Clarification Agent returned "
                "an empty clarification question."
            )

        return {
            **state,
            "clarification_required": True,
            "clarification_question": (
                question.strip()
            ),
            "original_query": query,
        }

    except Exception as error:
        return {
            **state,
            "error": (
                f"Clarification Generation failed: {error}"
            ),
        }


# =====================================================================
# Milestone 2 - Retrieval Node
# =====================================================================

def retrieval_node(
    state: WorkflowState,
) -> WorkflowState:
    """
    Run the existing Retrieval Agent.

    When semantic search returns no results (e.g. the relevance threshold
    filtered everything out), fall back to a filename-based lookup so that
    queries like "tell me about flood.jpg" still work.
    """

    if _has_error(state):
        return state

    analysis = state.get(
        "query_analysis"
    )

    if not isinstance(
        analysis,
        QueryUnderstandingResult,
    ):
        return {
            **state,
            "error": (
                "Retrieval requires a valid "
                "QueryUnderstandingResult."
            ),
        }

    try:
        k = state.get(
            "k",
            3,
        )

        retrieval_result = (
            _retrieval_agent.run(
                analysis,
                k=k,
                user_id=state.get("user_id"),
            )
        )

        # ----------------------------------------------------------------
        # Filename-based fallback
        #
        # When semantic/lexical retrieval yields nothing (all candidates
        # were below the relevance threshold), try to find chunks whose
        # stored filename appears in the raw query.  This handles queries
        # like "can u tell about flood.jpg" where the semantic distance
        # between the query text and the OCR-extracted image text
        # is too large to pass the threshold.
        # ----------------------------------------------------------------

        print(f"\n[RETRIEVAL] Query: {state.get('query', '')}")
        print(f"[RETRIEVAL] User ID: {state.get('user_id')}")
        print(f"[RETRIEVAL] Primary results after threshold: {len(retrieval_result.get('results', []))}")

        # Backward-compat: if primary user-filtered retrieval returns nothing,
        # retry without user_id (for docs indexed before user_id was required).
        results = retrieval_result.get("results", [])
        user_id_used = state.get("user_id")

        if not results and user_id_used:
            print("[RETRIEVAL] Primary retrieval empty — retrying without user_id filter (backward-compat)")
            no_user_result = _retrieval_agent.run(
                analysis,
                k=k,
                user_id=None,
            )
            if no_user_result.get("results"):
                print(f"[RETRIEVAL] Backward-compat retry returned {len(no_user_result['results'])} results")
                retrieval_result = no_user_result

        results = retrieval_result.get("results", [])

        if not results:
            from app.rag.chromadb_service import search_by_filename

            raw_query = state.get("query", "")

            # Extract any word that looks like a filename (contains a dot)
            import re as _re
            filename_tokens = _re.findall(
                r"[\w\-]+\.(?:jpg|jpeg|png|pdf|docx|txt|csv)",
                raw_query,
                flags=_re.IGNORECASE,
            )

            fallback_chunks = []
            for fname in filename_tokens:
                fallback_chunks.extend(search_by_filename(fname, raw_query=raw_query))
            # NOTE: We intentionally do NOT fall back to search_by_filename(raw_query)
            # when no filename tokens are found. That would treat the entire question
            # as a filename filter and prevent normal semantic retrieval from working.

            if fallback_chunks:
                print(f"[RETRIEVAL] Filename fallback returned {len(fallback_chunks)} chunks")
                retrieval_result = {
                    **retrieval_result,
                    "results": fallback_chunks,
                    "fallback": "filename",
                }

        # ----------------------------------------------------------------
        # Pure-semantic fallback
        # ----------------------------------------------------------------

        results = retrieval_result.get("results", [])

        if not results:
            print("[RETRIEVAL] All thresholds filtered — running pure-semantic fallback (no threshold)")
            from app.agents.retrieval.semantic_search import search_semantic
            from app.agents.retrieval.reranker import rerank_results

            raw_query = state.get("query", "")
            user_id = state.get("user_id")

            semantic_candidates = search_semantic(
                query=raw_query,
                k=5,
                user_id=user_id if user_id else None,
            )
            print(f"[RETRIEVAL] Fallback semantic candidates (with user filter): {len(semantic_candidates)}")

            # Backward-compat: docs indexed before user_id was added have user_id=None.
            # If user-filtered search returns nothing, try without filter.
            if not semantic_candidates and user_id:
                print("[RETRIEVAL] Retrying fallback without user_id filter (backward-compat for old docs)")
                semantic_candidates = search_semantic(
                    query=raw_query,
                    k=5,
                    user_id=None,
                )
                print(f"[RETRIEVAL] Fallback candidates (no filter): {len(semantic_candidates)}")

            if semantic_candidates:
                # Rerank with NO threshold — always return the best we have
                no_threshold_results = rerank_results(
                    semantic_candidates,
                    exact_terms=[],
                    keywords=[],
                    query_type="factual",
                    exact_candidates_found=False,
                    search_query=raw_query,
                    relevance_threshold=None,
                )

                if no_threshold_results:
                    print(f"[RETRIEVAL] Fallback results: {len(no_threshold_results)} — using top 5")
                    retrieval_result = {
                        **retrieval_result,
                        "results": no_threshold_results[:5],
                        "fallback": "semantic_no_threshold",
                    }
                else:
                    print("[RETRIEVAL] Fallback reranker returned 0 results")
            else:
                print("[RETRIEVAL] Fallback semantic search returned 0 candidates — no documents indexed?")

        print(f"[RETRIEVAL] Final result count: {len(retrieval_result.get('results', []))}")
        print(f"[RETRIEVAL] Fallback used: {retrieval_result.get('fallback', 'none')}\n")

        # Debug: print relevance score for every final retrieved chunk
        results = retrieval_result.get("results", [])

        if results:
            print("[RETRIEVAL] --- Relevance Scores ---")

            for i, chunk in enumerate(results, start=1):
                if isinstance(chunk, dict):
                    raw_score = (
                        chunk.get("relevance_score")
                        if chunk.get("relevance_score") is not None
                        else chunk.get("score")
                    )

                    if raw_score is None:
                        raw_score = chunk.get("similarity")

                    try:
                        score = float(raw_score)
                        print(
                            f"[RETRIEVAL] Chunk {i} | "
                            f"Relevance: {score:.3f} ({score * 100:.1f}%)"
                        )
                    except (TypeError, ValueError):
                        print(
                            f"[RETRIEVAL] Chunk {i} | "
                            f"Relevance: unavailable"
                        )

            print("[RETRIEVAL] ----------------------\n")

        return {
            **state,
            "retrieval_result": retrieval_result,
        }

    except Exception as error:
        return {
            **state,
            "error": (
                f"Retrieval failed: {error}"
            ),
        }

# =====================================================================
# Milestone 2 - Response Generation Node
# =====================================================================

def response_generation_node(
    state: WorkflowState,
) -> WorkflowState:
    """
    Generate grounded response from retrieved chunks.
    """

    if _has_error(state):
        return state

    query = state.get(
        "query",
        "",
    ).strip()

    retrieval_result = state.get(
        "retrieval_result",
        {},
    )

    chunks = retrieval_result.get(
        "results",
        [],
    )

    try:
        response = generate_response(
            question=query,
            chunks=chunks,
        )

        response_data = response.model_dump()

        # ---------------------------------------------------------------
        # Debug: Answer confidence
        # ---------------------------------------------------------------
        print("\n[RESPONSE] --- Answer Metrics ---")
        print(f"[RESPONSE] Query: {query}")
        print(
            f"[RESPONSE] Answer Confidence: "
            f"{response.confidence:.2f} "
            f"({response.confidence * 100:.1f}%)"
        )

        # ---------------------------------------------------------------
        # Debug: Relevance of cited sources
        # ---------------------------------------------------------------
        if response.sources:
            print("[RESPONSE] --- Cited Source Relevance ---")

            for i, source in enumerate(response.sources, start=1):
                if source.relevance_score is not None:
                    print(
                        f"[RESPONSE] Source {i} | "
                        f"{source.source} | "
                        f"Relevance: "
                        f"{source.relevance_score:.3f} "
                        f"({source.relevance_score * 100:.1f}%)"
                    )
                else:
                    print(
                        f"[RESPONSE] Source {i} | "
                        f"{source.source} | "
                        f"Relevance: unavailable"
                    )

        print("[RESPONSE] --------------------------\n")

        # ---------------------------------------------------------------
        # Existing no-evidence/refusal protection
        # ---------------------------------------------------------------
        # A refusal means the retrieved candidates did not contain usable
        # evidence. Clear retrieval artifacts before the state is returned
        # so the live Context Inspector and persisted conversation metadata
        # do not present unrelated chunks as sources for that answer.
        if is_insufficient_context_answer(
            response_data.get("answer", "")
        ):
            retrieval_result = {
                "results": [],
            }

        return {
            **state,
            "retrieval_result": retrieval_result,
            "response": response_data,
        }

    except Exception as error:
        return {
            **state,
            "error": (
                f"Response Generation failed: {error}"
            ),
        }

# =====================================================================
# General Knowledge - Direct LLM Response
# =====================================================================

def general_response_node(
    state: WorkflowState,
) -> WorkflowState:
    """
    Generate a response for general-knowledge or conversational
    queries without using the knowledge-base retrieval path.
    """

    if _has_error(state):
        return state

    query = state.get(
        "query",
        "",
    ).strip()

    if not query:
        return {
            **state,
            "error": (
                "Cannot generate general response "
                "because query is empty."
            ),
        }

    prompt = f"""
You are the general-purpose AI assistant for QueryNest.

Answer the user's question clearly, naturally, and accurately
using your general knowledge.

This is a general-knowledge or conversational query.
Do not claim that the answer came from the user's knowledge base.
Do not invent document sources or citations.

User query:
{query}
"""

    try:
        response = _llm.invoke(
            prompt
        )

        answer = getattr(
            response,
            "content",
            "",
        )

        if isinstance(
            answer,
            list,
        ):
            answer = " ".join(
                str(item)
                for item in answer
            )

        if not isinstance(
            answer,
            str,
        ):
            answer = str(answer)

        answer = answer.strip()

        if not answer:
            raise ValueError(
                "General LLM returned an empty response."
            )

        return {
            **state,
            # General LLM responses are intentionally outside the RAG
            # confidence/retrieval pipeline. Explicitly clear retrieval
            # state so Context Inspector cannot display stale chunks.
            "retrieval_result": {
                "results": [],
            },
            "response": {
                "answer": answer,
                "sources": [],
                "confidence": None,
            },
        }

    except Exception as error:
        return {
            **state,
            "error": (
                f"General response generation failed: {error}"
            ),
        }

# =====================================================================
# Milestone 3 - Save Memory Node
# =====================================================================

def save_memory_node(
    state: WorkflowState,
) -> WorkflowState:
    """
    Save the completed user/assistant exchange.
    """

    if _has_error(state):
        return state

    conversation_id = state.get(
        "conversation_id"
    )

    # Preserve M2 behavior when no conversation is being used.
    if not conversation_id:
        return state

    response = state.get(
        "response",
        {},
    )

    if not response:
        return state

    query = state.get(
        "query",
        "",
    ).strip()

    answer = response.get(
        "answer"
    )

    if not query:
        return {
            **state,
            "error": (
                "Cannot save memory because query is empty."
            ),
        }

    if not answer:
        return {
            **state,
            "error": (
                "Cannot save memory because response "
                "answer is empty."
            ),
        }

    try:
        db = _get_db(
            state
        )
        response_metadata = {
            "sources": response.get(
                "sources",
                [],
            ),
            "confidence": response.get(
                "confidence",
                None,
            ),
            "speech_text": state.get(
                "speech_text"
            ),
            "retrieval_results": (
                state.get(
                    "retrieval_result",
                    {}
                ).get(
                    "results",
                    []
                )
            ),
        }

        _memory_agent.store_turn(
            db=db,
            conversation_id=conversation_id,
            user_query=query,
            ai_response=answer,
            response_metadata=response_metadata,
        )

        return state

    except Exception as error:
        return {
            **state,
            "error": (
                f"Conversation Memory save failed: {error}"
            ),
        }