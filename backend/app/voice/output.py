"""
output.py

Text-to-Speech (TTS) output contract for the Voice module.

Important: actual speech synthesis happens in the BROWSER using the
Web Speech API (frontend responsibility, per the Milestone 3 task
split). This file's job is just to prepare the answer text so it
reads naturally out loud, and to build the VoiceQueryResponse
(schemas.py) that gets sent back to the frontend.

Responsibilities:
- Take the final response from the existing /query pipeline
  (response_generation's LLMResponse, or the M3 workflow's output
  if clarification is involved)
- Strip citation markers (e.g. [1], [2]) for a clean spoken version
- Build a VoiceQueryResponse with both the display text and the
  speech-ready text
"""

import re
from typing import Optional

from .schemas import VoiceQueryResponse


def prepare_speech_text(answer: str) -> str:
    """
    Convert an answer string into a version safe/natural for
    text-to-speech playback.

    Args:
        answer: The final answer text, possibly containing citation
                 markers like [1], [2] (from response_generation).

    Returns:
        A cleaned string with citation markers removed, suitable
        for passing to the browser's speech synthesis.
    """
    if not answer:
        return ""

    # Remove citation markers like [1], [2], [12]
    speech_text = re.sub(r"\s*\[\d+\]", "", answer)

    # Collapse any double spaces left behind after removal
    speech_text = re.sub(r"\s{2,}", " ", speech_text).strip()

    return speech_text


def build_voice_response(
    answer: str,
    conversation_id: Optional[str] = None,
    sources: Optional[list] = None,
    confidence: Optional[float] = None,
    clarification_required: bool = False,
    clarification_question: Optional[str] = None,
) -> VoiceQueryResponse:
    """
    Build the VoiceQueryResponse to send back to the frontend after
    the /query pipeline has produced a result.

    Args:
        answer: The final answer text (display version, with citations).
        conversation_id: Conversation identifier, for multi-turn memory.
        sources: Sources returned by the retrieval pipeline.
        confidence: Confidence score for the generated response.
        clarification_required: Whether the workflow needs clarification
                                  instead of a direct answer.
        clarification_question: The clarification question to ask, if any.

    Returns:
        A validated VoiceQueryResponse. The frontend uses `answer` for
        display, and can request the cleaned speech_text separately
        via prepare_speech_text() for text-to-speech playback.
    """
    return VoiceQueryResponse(
        answer=answer,
        conversation_id=conversation_id,
        sources=sources or [],
        confidence=confidence,
        clarification_required=clarification_required,
        clarification_question=clarification_question,
    )


if __name__ == "__main__":
    sample_answer = "Employees are entitled to 12 days of paid leave per year [1]."

    speech_ready = prepare_speech_text(sample_answer)
    print("Speech text:", speech_ready)

    response = build_voice_response(
        answer=sample_answer,
        conversation_id="conv_123",
        sources=[{"chunk_id": "chunk_001", "reference": "[1]"}],
        confidence=0.9,
    )
    print(response.model_dump_json(indent=2))
