"""
Milestone 3 - Query API with authentication.

Flow:

    FastAPI
        ↓
    Authentication
        ↓
    Conversation ownership validation
        ↓
    Database Session
        ↓
    LangGraph Workflow
        ↓
    Conversation Memory
        ↓
    Query Understanding
        ↓
    Conditional Routing
        ├── Retrieval
        │     ↓
        │  Response Generation
        │
        └── Clarification
              ↓
          Refined Query
              ↓
           Retrieval
              ↓
        Response Generation
              ↓
        Save Conversation
              ↓
        Response Transparency
              ↓
        Final JSON Response
"""

from __future__ import annotations

import time

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy.orm import Session

from app.analytics.schemas import QueryAnalyticsCreate
from app.analytics.service import log_query
from app.core.database import get_db
from app.core.models import (
    Conversation,
    User,
)
from app.dependencies.auth import get_current_user
from app.knowledge_gaps.schemas import KnowledgeGapCreate
from app.knowledge_gaps.service import (
    create_knowledge_gap,
    detect_knowledge_gap,
)
from app.models.request_models import QueryRequest
from app.orchestration.workflow import run_workflow
from app.transparency.service import build_transparency
from app.voice.output import prepare_speech_text


router = APIRouter(
    tags=["Query"],
)


@router.post(
    "/query",
    summary="Query Documents",
    description=(
        "Run the Milestone 2 + Milestone 3 "
        "LangGraph workflow with authentication, "
        "conversation memory, clarification, "
        "voice support, and response transparency."
    ),
)
def query_documents(
    request: QueryRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    """
    Execute the complete authenticated M3 workflow.

    Conversation IDs are checked before entering
    the existing LangGraph workflow.
    """

    analytics_start = time.perf_counter()
    print(f"[CHAT] Received question: {request.query}")

    # Validate retrieval count.
    if request.k < 1:
        raise HTTPException(
            status_code=400,
            detail="k must be at least 1.",
        )

    # -------------------------------------------------------------
    # Validate conversation ownership.
    # -------------------------------------------------------------
    if request.conversation_id:

        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.id
                == request.conversation_id,
                Conversation.user_id
                == current_user.id,
            )
            .first()
        )

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found.",
            )

    try:
        # ---------------------------------------------------------
        # Execute the existing M3 LangGraph workflow.
        #
        # Authentication is handled outside the workflow.
        # ---------------------------------------------------------
        result = run_workflow(
            query=request.query,
            k=request.k,
            conversation_id=request.conversation_id,
            clarification_answer=(
                request.clarification_answer
            ),
            clarification_question=(
                request.clarification_question
            ),
            original_query=(
                request.original_query
            ),
            user_id=str(current_user.id),
            db=db,
        )

        # ---------------------------------------------------------
        # Workflow-level failures.
        # ---------------------------------------------------------
        if result.get("error"):
            raise HTTPException(
                status_code=500,
                detail=result["error"],
            )

        # ---------------------------------------------------------
        # Query Understanding result.
        # ---------------------------------------------------------
        query_analysis = result.get(
            "query_analysis"
        )

        query_understanding = None

        if query_analysis is not None:
            query_understanding = (
                query_analysis.model_dump()
            )

        # ---------------------------------------------------------
        # Clarification information.
        # ---------------------------------------------------------
        clarification_required = result.get(
            "clarification_required",
            False,
        )

        clarification_question = result.get(
            "clarification_question"
        )

        # ---------------------------------------------------------
        # Retrieval and generated response.
        # ---------------------------------------------------------
        retrieval_result = result.get(
            "retrieval_result"
        )

        response_result = result.get(
            "response"
        )

        # ---------------------------------------------------------
        # Response transparency.
        # ---------------------------------------------------------
        transparency = build_transparency(
            retrieval_result
        )

        # ---------------------------------------------------------
        # Prepare clean text for browser TTS.
        # ---------------------------------------------------------
        speech_text = (
            prepare_speech_text(
                response_result.get(
                    "answer",
                    "",
                )
            )
            if response_result
            else None
        )

        # ---------------------------------------------------------
        # Milestone 4 - Query Analytics + Knowledge Gap Detection.
        #
        # These values are derived from the existing M3 workflow.
        # Analytics failures are intentionally isolated so that a
        # problem in reporting never breaks the user's query.
        # ---------------------------------------------------------
        response_time = time.perf_counter() - analytics_start

        route = result.get("route")

        query_type = None

        if query_analysis is not None:
            query_type = getattr(
                query_analysis,
                "query_type",
                None,
            )

        # Retrieval results are only meaningful for retrieval routes.
        retrieval_count = 0

        if (
            route == "retrieval"
            and isinstance(retrieval_result, dict)
        ):
            retrieval_items = retrieval_result.get(
                "results",
                [],
            )

            if isinstance(retrieval_items, list):
                retrieval_count = len(retrieval_items)

        confidence_score = None

        if isinstance(response_result, dict):
            raw_confidence = response_result.get(
                "confidence"
            )

            if isinstance(raw_confidence, (int, float)):
                confidence_score = float(raw_confidence)

        answer_text = ""

        if isinstance(response_result, dict):
            answer_text = str(
                response_result.get(
                    "answer",
                    "",
                )
                or ""
            ).strip()

        # ---------------------------------------------------------
        # Detect retrieval answers that explicitly state that the
        # knowledge base does not contain enough information.
        #
        # IMPORTANT:
        # This applies only to retrieval queries.
        # General LLM queries must remain:
        #     confidence = NULL
        #     response_status = "answered"
        # ---------------------------------------------------------
        retrieval_refusal = False

        if route == "retrieval" and answer_text:
            answer_lower = answer_text.lower()

            refusal_patterns = (
                "the retrieved documents do not contain",
                "retrieved documents do not contain",
                "the retrieved context does not contain",
                "retrieved context does not contain",
                "i don't have enough information",
                "i do not have enough information",
                "no information is available",
                "no information is provided",
                "the available context does not contain",
                "the available context does not provide",
                "the context does not contain",
                "cannot answer from the available context",
                "can't answer from the available context",
                "not enough information in the available knowledge base",
            )

            retrieval_refusal = any(
                pattern in answer_lower
                for pattern in refusal_patterns
            )

        # A clarification request is not a resolved answer.
        if clarification_required:
            response_status = "unanswered"

        elif retrieval_refusal:
            # RAG query could not be answered from retrieved evidence.
            response_status = "unanswered"
            confidence_score = 0.0

            if isinstance(response_result, dict):
                response_result["confidence"] = 0.0

        elif answer_text:
            response_status = "answered"

        else:
            response_status = "unanswered"

        try:
            analytics_data = QueryAnalyticsCreate(
                user_id=str(current_user.id),
                conversation_id=(
                    result.get("conversation_id")
                ),
                query_text=request.query,
                query_type=query_type,
                response_status=response_status,
                confidence_score=confidence_score,
                response_time=response_time,
            )

            log_query(
                db=db,
                data=analytics_data,
            )

            # Do not classify general-LLM queries as knowledge gaps.
            # In the current workflow those queries intentionally have
            # no retrieval results and may expose confidence=0.0.
            if route == "retrieval":
                is_gap, gap_reason = detect_knowledge_gap(
                    response_status=response_status,
                    confidence_score=confidence_score,
                    retrieval_count=retrieval_count,
                )

                if is_gap and gap_reason:
                    gap_data = KnowledgeGapCreate(
                        query_text=request.query,
                        query_type=query_type,
                        reason=gap_reason,
                        confidence_score=confidence_score,
                    )

                    create_knowledge_gap(
                        db=db,
                        data=gap_data,
                        user_id=str(current_user.id),
                    )

        except Exception:
            # Milestone 4 analytics must never take down the core M3
            # query path. Roll back any failed analytics transaction.
            db.rollback()

        # General and clarification routes must never expose retrieval
        # artifacts. The workflow already avoids retrieval for these routes,
        # but normalize the API payload here as an explicit contract.
        api_retrieval = retrieval_result
        if route != "retrieval":
            api_retrieval = {"results": []}

        return {
            "success": True,

            # Preserve original user input.
            "query": request.query,

            "conversation_id": result.get(
                "conversation_id"
            ),

            "user_id": str(
                current_user.id
            ),

            "query_understanding": (
                query_understanding
            ),

            "route": result.get(
                "route"
            ),

            "route_reason": result.get(
                "route_reason"
            ),

            "clarification_required": (
                clarification_required
            ),

            "clarification_question": (
                clarification_question
            ),

            "retrieval": api_retrieval,

            "response": response_result,

            "speech_text": speech_text,

            "transparency": transparency,
        }

    except HTTPException:
        raise

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Query processing failed: {error}"
            ),
        ) from error