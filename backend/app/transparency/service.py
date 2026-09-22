from __future__ import annotations

from typing import Any


def get_value(
    item: Any,
    key: str,
    default=None,
):
    """
    Get a value from either a dictionary
    or an object.
    """

    if isinstance(item, dict):
        return item.get(key, default)

    return getattr(item, key, default)


def get_metadata(
    item: Any,
) -> dict:
    """
    Extract metadata from a retrieved chunk.
    """

    metadata = get_value(
        item,
        "metadata",
        {},
    )

    if isinstance(metadata, dict):
        return metadata

    return {}


def extract_content(
    item: Any,
) -> str:
    """
    Extract text content from a retrieved chunk.

    Supports common RAG document formats.
    """

    content = get_value(
        item,
        "page_content",
    )

    if content is not None:
        return str(content)

    content = get_value(
        item,
        "content",
    )

    if content is not None:
        return str(content)

    content = get_value(
        item,
        "text",
    )

    if content is not None:
        return str(content)

    return ""


def extract_score(
    item: Any,
) -> float:
    """
    Extract the relevance score from a retrieved chunk.
    """

    score = get_value(
        item,
        "score",
    )

    if score is None:
        score = get_value(
            item,
            "relevance_score",
        )

    if score is None:
        score = get_value(
            item,
            "similarity",
        )

    try:
        score = float(score)
    except (
        TypeError,
        ValueError,
    ):
        score = 0.0

    # Keep score between 0 and 1.
    return max(
        0.0,
        min(
            1.0,
            score,
        ),
    )


def extract_source(
    item: Any,
    metadata: dict,
) -> str:
    """
    Extract the source document name.
    """

    source = (
        metadata.get("source")
        or metadata.get("file_name")
        or metadata.get("filename")
        or metadata.get("document")
        or get_value(
            item,
            "source",
        )
        or get_value(
            item,
            "document",
        )
        or "Unknown source"
    )

    return str(source)


def extract_page(
    item: Any,
    metadata: dict,
):
    """
    Extract page number from metadata.
    """

    page = (
        metadata.get("page")
        or metadata.get("page_number")
        or metadata.get("page_num")
        or get_value(
            item,
            "page",
        )
    )

    if page is None:
        return None

    try:
        return int(page)
    except (
        TypeError,
        ValueError,
    ):
        return None


def extract_chunk_id(
    item: Any,
    metadata: dict,
    index: int,
) -> str:
    """
    Extract chunk ID.

    If no ID exists, generate a fallback ID.
    """

    chunk_id = (
        metadata.get("chunk_id")
        or metadata.get("id")
        or get_value(
            item,
            "chunk_id",
        )
        or get_value(
            item,
            "id",
        )
    )

    if chunk_id is None:
        chunk_id = f"chunk_{index + 1}"

    return str(chunk_id)


def extract_chunks(
    retrieval_result: Any,
) -> list:
    """
    Extract chunks from the retrieval result.

    Supports common retrieval response structures.
    """

    if retrieval_result is None:
        return []

    # Retrieval result is already a list.
    if isinstance(
        retrieval_result,
        list,
    ):
        return retrieval_result

    # Retrieval result is a dictionary.
    if isinstance(
        retrieval_result,
        dict,
    ):
        chunks = (
            retrieval_result.get("results")
            or retrieval_result.get("chunks")
            or retrieval_result.get("documents")
            or retrieval_result.get("sources")
            or []
        )

        return chunks

    return []


def calculate_confidence(
    scores: list[float],
) -> float:
    """
    Calculate overall confidence using the
    average relevance score.
    """

    if not scores:
        return 0.0

    confidence = sum(scores) / len(scores)

    confidence = max(
        0.0,
        min(
            1.0,
            confidence,
        ),
    )

    return round(
        confidence,
        2,
    )


def get_confidence_level(
    confidence: float,
) -> str:
    """
    Convert numerical confidence into a
    human-readable confidence level.
    """

    if confidence >= 0.80:
        return "High"

    if confidence >= 0.60:
        return "Medium"

    return "Low"


def build_transparency(
    retrieval_result: Any,
) -> dict:
    """
    Build the complete response transparency object.

    It provides:

    - source document
    - page number
    - chunk ID
    - retrieved content
    - relevance score
    - citation
    - overall confidence
    - confidence level
    """

    chunks = extract_chunks(
        retrieval_result
    )

    sources = []

    scores = []

    for index, chunk in enumerate(
        chunks
    ):
        metadata = get_metadata(
            chunk
        )

        document = extract_source(
            chunk,
            metadata,
        )

        page = extract_page(
            chunk,
            metadata,
        )

        chunk_id = extract_chunk_id(
            chunk,
            metadata,
            index,
        )

        content = extract_content(
            chunk
        )

        score = extract_score(
            chunk
        )

        # Create human-readable citation.
        if page is not None:
            citation = (
                f"{document}, page {page}"
            )
        else:
            citation = document

        source = {
            "document": document,
            "page": page,
            "chunk_id": chunk_id,
            "content": content,
            "relevance_score": round(
                score,
                4,
            ),
            "citation": citation,
        }

        sources.append(
            source
        )

        scores.append(
            score
        )

    confidence = calculate_confidence(
        scores
    )

    confidence_level = get_confidence_level(
        confidence
    )

    return {
        "confidence": confidence,
        "confidence_level": confidence_level,
        "sources": sources,
    }
