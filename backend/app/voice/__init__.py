"""
Voice module for the RAG application.

The frontend is responsible for:
    - Microphone access
    - Speech-to-text using the Web Speech API
    - Text-to-speech using browser Speech Synthesis API

The backend is responsible for:
    - Accepting the resulting transcript as text
    - Validating voice-query data
    - Preserving conversation context
    - Passing the transcript through the normal query workflow
"""

from .schemas import VoiceQueryRequest, VoiceQueryResponse
from .input import validate_voice_query, prepare_voice_query

__all__ = [
    "VoiceQueryRequest",
    "VoiceQueryResponse",
    "validate_voice_query",
    "prepare_voice_query",
]