"""
Milestone 2 - Response Generation Agent.

Pipeline:

    Retrieved chunks
          ↓
    Grounded prompt construction
          ↓
    Shared Groq LLM
          ↓
    Citation extraction
          ↓
    Retrieval-aware confidence
          ↓
    Validated LLMResponse

The agent is domain-agnostic and works with any retrieved
knowledge-base chunks.
"""

from __future__ import annotations

import re
from typing import Any

from .llm_call_groq import GroqHandler
from .prompt_builder import build_prompt
from .schemas import (
    LLMResponse,
    Source,
)


# ---------------------------------------------------------------------
# Shared LLM handler
# ---------------------------------------------------------------------

_handler: GroqHandler | None = None


def _get_handler() -> GroqHandler:
    """
    Return the shared Groq handler.

    The handler is created once and reused across requests.
    """

    global _handler

    if _handler is None:
        _handler = GroqHandler()

    return _handler


# ---------------------------------------------------------------------
# Chunk helpers
# ---------------------------------------------------------------------

def _get_chunk_metadata(
    chunk: Any,
) -> dict[str, Any]:
    """
    Safely extract metadata from a retrieved chunk.
    """

    if not isinstance(chunk, dict):
        return {}

    metadata = chunk.get("metadata", {})

    if not isinstance(metadata, dict):
        return {}

    return metadata


def _get_chunk_id(
    chunk: Any,
    index: int,
) -> str:
    """
    Return a stable chunk ID.

    Canonical field:
        chunk_id

    Backward-compatible fallback:
        id
    """

    if isinstance(chunk, dict):

        chunk_id = chunk.get("chunk_id")

        if chunk_id:
            return str(chunk_id)

        # Backward compatibility with older retrieval output.
        legacy_id = chunk.get("id")

        if legacy_id:
            return str(legacy_id)

    return f"chunk_{index}"


def _get_source_name(
    chunk: Any,
    chunk_id: str,
) -> str:
    """
    Get a human-readable source name.
    """

    metadata = _get_chunk_metadata(chunk)

    filename = metadata.get("filename")

    if filename:
        return str(filename)

    source = metadata.get("source")

    if source:
        return str(source)

    return chunk_id


def _get_relevance_score(
    chunk: Any,
) -> float | None:
    """
    Safely read the Retrieval Agent relevance score.
    """

    if not isinstance(chunk, dict):
        return None

    value = chunk.get("relevance_score")

    if value is None:
        return None

    try:
        return max(
            0.0,
            min(
                1.0,
                float(value),
            ),
        )
    except (TypeError, ValueError):
        return None

# ---------------------------------------------------------------------
# Retrieval-refusal detection
# ---------------------------------------------------------------------

INSUFFICIENT_CONTEXT_PATTERNS = (
    # Full no-evidence responses. These intentionally require
    # "any information" / an explicit knowledge-base refusal so a
    # legitimate partial answer is not mistaken for a total refusal.
    "the retrieved documents do not contain any information",
    "retrieved documents do not contain any information",
    "the retrieved context does not contain any information",
    "retrieved context does not contain any information",
    "the available context does not contain any information",
    "the available context does not provide any information",
    "the context does not contain any information",
    "i don't have enough information in the available knowledge base",
    "i do not have enough information in the available knowledge base",
    "cannot answer from the available context",
    "can't answer from the available context",
    "no information is available in the retrieved context",
    "no information is available in the available context",
)


def is_insufficient_context_answer(answer: str) -> bool:
    """Return True when the model explicitly says the retrieved context lacks the answer."""

    if not isinstance(answer, str):
        return False

    normalized = answer.lower().strip()

    return any(
        pattern in normalized
        for pattern in INSUFFICIENT_CONTEXT_PATTERNS
    )


def _strip_citation_markers(answer: str) -> str:
    """Remove RAG citation markers from a no-evidence refusal response."""

    if not isinstance(answer, str):
        return answer

    cleaned = re.sub(
        r"(?:\[\d+\]|【\d+】)",
        "",
        answer,
    )

    # Remove excess whitespace left behind by stripped citations.
    return re.sub(r"[ \t]{2,}", " ", cleaned).strip()


# ---------------------------------------------------------------------
# Citation extraction
# ---------------------------------------------------------------------

def _extract_citation_numbers(
    answer: str,
    chunk_count: int,
) -> list[int]:
    """
    Extract valid citation numbers from the LLM answer.

    Supported formats:

        [1]
        [2]
        [3]

    and also:

        【1】
        【2】
        【3】

    The second form is handled defensively because some LLM outputs
    may use full-width Unicode brackets even when the prompt requests
    normal square brackets.

    Invalid citation numbers are ignored.
    """

    if not answer or chunk_count <= 0:
        return []

    matches = re.findall(
        r"(?:\[(\d+)\]|【(\d+)】)",
        answer,
    )

    numbers: set[int] = set()

    for normal_match, unicode_match in matches:

        value = (
            normal_match
            or unicode_match
        )

        try:
            number = int(value)
        except ValueError:
            continue

        if 1 <= number <= chunk_count:
            numbers.add(number)

    return sorted(numbers)


def _normalize_citation_markers(
    answer: str,
) -> str:
    """
    Normalize Unicode citation markers to the standard project format.

    Example:

        【1】 → [1]
        【2】 → [2]
    """

    if not answer:
        return answer

    return re.sub(
        r"【(\d+)】",
        r"[\1]",
        answer,
    )


# ---------------------------------------------------------------------
# Source construction
# ---------------------------------------------------------------------

def _build_sources(
    answer: str,
    chunks: list[dict[str, Any] | str],
) -> list[Source]:
    """
    Convert cited chunk numbers into Source objects.

    Each source preserves:

        - filename/source
        - reference number
        - chunk ID
        - relevance score
        - metadata
    """

    citation_numbers = _extract_citation_numbers(
        answer,
        len(chunks),
    )

    sources: list[Source] = []

    for number in citation_numbers:

        chunk = chunks[number - 1]

        chunk_id = _get_chunk_id(
            chunk,
            number,
        )

        metadata = _get_chunk_metadata(
            chunk,
        )

        source_name = _get_source_name(
            chunk,
            chunk_id,
        )

        relevance_score = _get_relevance_score(
            chunk,
        )

        sources.append(
            Source(
                source=source_name,
                reference=f"[{number}]",
                chunk_id=chunk_id,
                relevance_score=relevance_score,
                metadata=metadata,
            )
        )

    return sources


# ---------------------------------------------------------------------
# Confidence calculation
# ---------------------------------------------------------------------

def _calculate_citation_coverage(
    sources: list[Source],
    chunks: list[dict[str, Any] | str],
) -> float:
    """
    Measure how much of the supplied context was cited.

    This is a coverage signal, not a correctness probability.
    """

    if not chunks:
        return 0.0

    return min(
        1.0,
        len(sources) / len(chunks),
    )


def _calculate_retrieval_quality(
    sources: list[Source],
    chunks: list[dict[str, Any] | str] | None = None,
) -> float:
    """
    Calculate retrieval evidence quality without making citation parsing
    a hard prerequisite.

    When cited sources are available, their relevance remains the strongest
    evidence. When the LLM omits citations, fall back to the ranked retrieved
    candidates so a good retrieval result is not collapsed to a fixed 0.15.
    """

    cited_scores = [
        source.relevance_score
        for source in sources
        if source.relevance_score is not None
    ]

    if cited_scores:
        return sum(cited_scores) / len(cited_scores)

    if not chunks:
        return 0.0

    candidate_scores: list[float] = []

    for chunk in chunks:

        score = _get_relevance_score(
            chunk
        )

        if score is not None:
            candidate_scores.append(
                score
            )

    if not candidate_scores:
        return 0.0

    # Top-ranked evidence matters more than distant candidates.
    candidate_scores.sort(
        reverse=True
    )

    weights = (
        0.60,
        0.25,
        0.15,
    )

    weighted_total = 0.0
    weight_total = 0.0

    for index, score in enumerate(
        candidate_scores[:3]
    ):

        weight = weights[index]

        weighted_total += (
            score * weight
        )

        weight_total += weight

    return (
        weighted_total
        / weight_total
    )


def _estimate_confidence(
    sources: list[Source],
    chunks: list[dict[str, Any] | str],
) -> float:
    """
    Estimate grounded-answer confidence from:

        1. Retrieval evidence quality.
        2. Citation coverage.

    Missing citations reduce confidence, but no longer replace strong
    retrieval evidence with a hard-coded 0.15. This is a heuristic signal,
    not a calibrated probability of factual correctness.
    """

    if not chunks:
        return 0.0

    retrieval_quality = _calculate_retrieval_quality(
        sources,
        chunks,
    )

    citation_coverage = _calculate_citation_coverage(
        sources,
        chunks,
    )

    if sources:

        # Citations are useful evidence of grounding, but they should not
        # dominate retrieval quality because an otherwise good answer can
        # occasionally omit a marker.
        confidence = (
            retrieval_quality * 0.80
            + citation_coverage * 0.20
        )

    else:

        # No recognizable citation: retain retrieval evidence but apply a
        # meaningful 20% grounding penalty instead of a fixed 0.15 score.
        confidence = (
            retrieval_quality * 0.80
        )

    return round(
        max(
            0.0,
            min(
                1.0,
                confidence,
            ),
        ),
        2,
    )


# ---------------------------------------------------------------------
# Main response-generation entry point
# ---------------------------------------------------------------------

def generate_response(
    question: str,
    chunks: list[dict[str, Any] | str],
) -> LLMResponse:
    """
    Generate a grounded answer from Retrieval Agent results.

    Args:
        question:
            Original user question.

        chunks:
            Final filtered/ranked chunks returned by the Retrieval Agent.

    Returns:
        Validated LLMResponse.
    """

    # ---------------------------------------------------------------
    # Validate question
    # ---------------------------------------------------------------

    if (
        not isinstance(
            question,
            str,
        )
        or not question.strip()
    ):

        return LLMResponse(
            answer="",
            sources=[],
            confidence=0.0,
        )

    # ---------------------------------------------------------------
    # Validate retrieved context
    # ---------------------------------------------------------------

    valid_chunks = [
        chunk
        for chunk in (chunks or [])
        if (
            isinstance(
                chunk,
                dict,
            )
            and str(
                chunk.get(
                    "content",
                    "",
                )
            ).strip()
        )
        or (
            isinstance(
                chunk,
                str,
            )
            and chunk.strip()
        )
    ]

    if not valid_chunks:

        return LLMResponse(
            answer=(
                "I don't have enough information "
                "in the available knowledge base "
                "to answer that."
            ),
            sources=[],
            confidence=0.0,
        )

    prompt = build_prompt(
        question,
        valid_chunks,
    )

    handler = _get_handler()

    # ---------------------------------------------------------------
    # Generate answer
    # ---------------------------------------------------------------

    try:

        answer = handler.generate(
            prompt
        )

    except (
        RuntimeError,
        ValueError,
    ):

        return LLMResponse(
            answer=(
                "Sorry, I couldn't generate "
                "an answer right now."
            ),
            sources=[],
            confidence=0.0,
        )

    # ---------------------------------------------------------------
    # Normalize citation formatting
    # ---------------------------------------------------------------

    answer = _normalize_citation_markers(
        answer
    )

    # ---------------------------------------------------------------
    # No-evidence guard
    # ---------------------------------------------------------------
    # The retrieval path may return weak candidate chunks so the response
    # generator can inspect them. If the model explicitly concludes that
    # those chunks do not contain the answer, they are not evidence for the
    # response and must not be exposed as citations/sources.
    if is_insufficient_context_answer(answer):
        return LLMResponse(
            answer=_strip_citation_markers(answer),
            sources=[],
            confidence=0.0,
        )

    # ---------------------------------------------------------------
    # Extract sources
    # ---------------------------------------------------------------

    sources = _build_sources(
        answer,
        valid_chunks,
    )

    # ---------------------------------------------------------------
    # Estimate confidence
    # ---------------------------------------------------------------

    confidence = _estimate_confidence(
        sources,
        valid_chunks,
    )

    return LLMResponse(
        answer=answer,
        sources=sources,
        confidence=confidence,
    )


# ---------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------

if __name__ == "__main__":

    sample_chunks = [
        {
            "chunk_id": "chunk_001",
            "content": (
                "Employees are entitled to "
                "12 days of paid leave per year."
            ),
            "metadata": {
                "filename": "hr_policy.pdf",
                "chunk_index": 3,
            },
            "relevance_score": 0.92,
        },
        {
            "chunk_id": "chunk_002",
            "content": (
                "Sick leave longer than "
                "2 days requires a medical certificate."
            ),
            "metadata": {
                "filename": "hr_policy.pdf",
                "chunk_index": 4,
            },
            "relevance_score": 0.81,
        },
    ]

    result = generate_response(
        "How many leave days do employees get?",
        sample_chunks,
    )

    print(
        result.model_dump_json(
            indent=4
        )
    )