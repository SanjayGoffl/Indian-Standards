"""
service.py

Voice module coordinator.

Connects:
- input.py  -> validates a voice transcript and converts it into
               normal query text
- output.py -> builds the VoiceQueryResponse sent back to the frontend

Note: this module does NOT do speech recognition or speech synthesis
itself - both happen in the browser via the Web Speech API (frontend
responsibility). This is the backend contract layer that sits between
the frontend's voice UI and the existing /query pipeline.

Expected flow:

    Frontend: mic -> Web Speech API -> transcript
        ↓
    handle_voice_request(transcript, conversation_id, language)
        [validate_voice_query + prepare_voice_query, from input.py]
        ↓
    existing /query pipeline
    (Query Understanding -> Retrieval -> Response Generation,
     or the M3 workflow if clarification is involved)
        ↓
    handle_voice_response(answer, ...)   [uses output.py]
        ↓
    Frontend: displays answer, reads it aloud via browser TTS
"""

from typing import Optional

from .input import validate_voice_query, prepare_voice_query, VoiceInputError
from .output import build_voice_response
from .schemas import VoiceQueryResponse


def handle_voice_request(
    transcript: str,
    conversation_id: Optional[str] = None,
    language: Optional[str] = "en-US",
) -> str:
    """
    Entry point for a voice-originated query, before it enters the
    normal /query pipeline.

    Args:
        transcript: The text already recognized by the browser's
                     Web Speech API (frontend has already done
                     speech-to-text by this point).
        conversation_id: Conversation identifier, for multi-turn memory.
        language: Speech recognition language used by the frontend.

    Returns:
        Cleaned query text, ready to pass into the existing
        Query Understanding -> Retrieval -> Response Generation
        pipeline exactly like a normal typed query.

    Raises:
        VoiceInputError: if the transcript is invalid/empty.
    """
    request = validate_voice_query(
        transcript=transcript,
        conversation_id=conversation_id,
        language=language,
    )
    return prepare_voice_query(request)


def handle_voice_response(
    answer: str,
    conversation_id: Optional[str] = None,
    sources: Optional[list] = None,
    confidence: Optional[float] = None,
    clarification_required: bool = False,
    clarification_question: Optional[str] = None,
) -> VoiceQueryResponse:
    """
    Prepares a generated answer for voice playback, after the normal
    /query pipeline has produced a response.

    Args: see build_voice_response() in output.py.

    Returns:
        A validated VoiceQueryResponse, ready for the frontend to
        display and read aloud.
    """
    return build_voice_response(
        answer=answer,
        conversation_id=conversation_id,
        sources=sources,
        confidence=confidence,
        clarification_required=clarification_required,
        clarification_question=clarification_question,
    )


if __name__ == "__main__":
    # Quick end-to-end style test
    try:
        query_text = handle_voice_request(
            transcript="  what is the leave policy  ",
            conversation_id="conv_123",
        )
        print("Prepared query text:", repr(query_text))
    except VoiceInputError as e:
        print("Voice input error:", e)

    sample_answer = "Employees are entitled to 12 days of paid leave per year [1]."
    response = handle_voice_response(
        answer=sample_answer,
        conversation_id="conv_123",
        sources=[{"chunk_id": "chunk_001", "reference": "[1]"}],
        confidence=0.9,
    )
    print(response.model_dump_json(indent=2))
