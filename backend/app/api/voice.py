"""
Milestone 3 - Voice Query API.

The frontend performs:
    Microphone
        ↓
    Browser Web Speech API
        ↓
    Transcript

The backend performs:
    Voice validation
        ↓
    Query preparation
        ↓
    Existing Milestone 3 workflow
        ↓
    Voice response preparation

Actual speech recognition and speech synthesis are handled by
the frontend browser.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.voice.input import (
    VoiceInputError,
    prepare_voice_query,
    validate_voice_query,
)
from app.voice.output import (
    build_voice_response,
    prepare_speech_text,
)
from app.voice.schemas import (
    VoiceQueryRequest,
)
from app.core.database import get_db
from app.orchestration.workflow import run_workflow


router = APIRouter(
    prefix="/voice",
    tags=["Voice"],
)


@router.post(
    "/query",
    summary="Process Voice Query",
    description=(
        "Process a browser Web Speech API transcript through "
        "the existing Milestone 3 RAG workflow."
    ),
)
def voice_query(
    request: VoiceQueryRequest,
    db: Session = Depends(get_db),
):
    """
    Process one voice-originated query.

    The frontend sends text, not an audio file.
    """

    try:
        # -------------------------------------------------------------
        # 1. Validate the voice request
        # -------------------------------------------------------------

        validated_request = validate_voice_query(
            transcript=request.transcript,
            conversation_id=request.conversation_id,
            language=request.language,
        )

        # -------------------------------------------------------------
        # 2. Prepare normal RAG query text
        # -------------------------------------------------------------

        query_text = prepare_voice_query(
            validated_request
        )

        # -------------------------------------------------------------
        # 3. Run the existing M3 workflow
        # -------------------------------------------------------------

        result = run_workflow(
            query=query_text,
            k=3,
            conversation_id=(
                validated_request.conversation_id
            ),
            db=db,
        )

        # -------------------------------------------------------------
        # 4. Handle workflow errors
        # -------------------------------------------------------------

        if result.get("error"):
            raise HTTPException(
                status_code=500,
                detail=result["error"],
            )

        # -------------------------------------------------------------
        # 5. Extract workflow response
        # -------------------------------------------------------------

        workflow_response = (
            result.get("response")
            or {}
        )

        answer = workflow_response.get(
            "answer",
            "",
        )

        sources = workflow_response.get(
            "sources",
            [],
        )

        confidence = workflow_response.get(
            "confidence",
        )

        clarification_required = result.get(
            "clarification_required",
            False,
        )

        clarification_question = result.get(
            "clarification_question",
        )

        # -------------------------------------------------------------
        # 6. Handle clarification
        # -------------------------------------------------------------

        if clarification_required:

            answer = (
                clarification_question
                or (
                    "Please provide some "
                    "clarification."
                )
            )

            sources = []
            confidence = None

        # -------------------------------------------------------------
        # 7. Build voice response
        # -------------------------------------------------------------

        voice_response = build_voice_response(
            answer=answer,
            conversation_id=(
                result.get(
                    "conversation_id"
                )
                or validated_request.conversation_id
            ),
            sources=sources,
            confidence=confidence,
            clarification_required=(
                clarification_required
            ),
            clarification_question=(
                clarification_question
            ),
        )

        # -------------------------------------------------------------
        # 8. Add clean speech text
        # -------------------------------------------------------------

        response_data = (
            voice_response.model_dump()
        )

        response_data["speech_text"] = (
            prepare_speech_text(
                answer
            )
        )

        return response_data

    except VoiceInputError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

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
                f"Voice query processing failed: {error}"
            ),
        ) from error