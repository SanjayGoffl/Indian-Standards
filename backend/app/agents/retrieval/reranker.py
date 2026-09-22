"""
Milestone 2 - Retrieval Reranker

Domain-agnostic reranker for candidates produced by semantic
and exact retrieval.

Main responsibilities:
    1. Score semantic relevance.
    2. Measure keyword coverage.
    3. Measure exact-term coverage.
    4. Reward exact-term + keyword co-occurrence.
    5. Prefer candidates satisfying the complete query intent without
       making literal whole-query matching dominant.
    6. Penalize candidates that miss required exact entities when
       exact retrieval has already found matching candidates.
    7. Filter low-confidence candidates.
    8. Deduplicate candidates safely.
    9. Preserve useful ranking metadata.

This module contains no LLM/API calls.
"""

from __future__ import annotations

import re
from typing import Any, Iterable


# =====================================================================
# Configuration
# =====================================================================

DEFAULT_RELEVANCE_THRESHOLD = 0.30

# When an exact lookup is available AND exact candidates exist,
# candidates without any required exact term are strongly penalized.
EXACT_MISS_PENALTY = 0.25

# Query-type weights.
#
# Semantic search remains the main general-purpose signal.
QUERY_TYPE_WEIGHTS: dict[str, dict[str, float]] = {
    "factual": {
        "semantic": 0.60,
        "keyword": 0.20,
        "exact": 0.10,
        "synergy": 0.10,
    },
    "procedural": {
        "semantic": 0.65,
        "keyword": 0.20,
        "exact": 0.05,
        "synergy": 0.10,
    },
    "comparative": {
        "semantic": 0.60,
        "keyword": 0.20,
        "exact": 0.05,
        "synergy": 0.15,
    },
    "ambiguous": {
        "semantic": 0.70,
        "keyword": 0.20,
        "exact": 0.03,
        "synergy": 0.07,
    },
}

DEFAULT_QUERY_TYPE = "factual"

TOKEN_PATTERN = re.compile(
    r"\b[a-zA-Z0-9][a-zA-Z0-9_-]*\b"
)


# =====================================================================
# Text utilities
# =====================================================================

def _normalize_text(value: Any) -> str:
    """Normalize text for lexical comparison."""

    if not isinstance(value, str):
        return ""

    value = value.lower()
    value = value.replace("\\_", "_")
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def _tokenize(text: str) -> set[str]:
    """Convert text to normalized tokens."""

    if not text:
        return set()

    return {
        token.lower()
        for token in TOKEN_PATTERN.findall(text)
    }


def _clean_terms(
    terms: Iterable[str] | None,
) -> list[str]:
    """Clean and deduplicate terms while preserving order."""

    cleaned: list[str] = []
    seen: set[str] = set()

    for term in terms or []:
        if not isinstance(term, str):
            continue

        value = _normalize_text(term)

        if not value or value in seen:
            continue

        seen.add(value)
        cleaned.append(value)

    return cleaned


def _contains_term(
    content: str,
    term: str,
) -> bool:
    """
    Check whether a keyword/phrase is present in the content.

    Single words use token matching.
    Multi-word terms use phrase matching.
    """

    normalized_content = _normalize_text(content)
    normalized_term = _normalize_text(term)

    if not normalized_content or not normalized_term:
        return False

    if " " in normalized_term:
        return normalized_term in normalized_content

    return normalized_term in _tokenize(
        normalized_content
    )


# =====================================================================
# Semantic scoring
# =====================================================================

def semantic_score(distance: Any) -> float:
    """
    Convert a ChromaDB distance into a bounded base relevance score.

    Lower distance => higher score.

    The score is intentionally computed independently for each candidate.
    It is not normalized against the current candidate set, so a relevant
    second-best chunk cannot be driven to zero simply because another chunk
    has a better distance.
    """

    if distance is None:
        return 0.0

    try:
        value = float(distance)
    except (TypeError, ValueError):
        return 0.0

    value = max(value, 0.0)

    score = 1.0 / (1.0 + value)

    return max(
        0.0,
        min(1.0, score),
    )


def query_match_score(
    content: str,
    search_query: str | None,
) -> float:
    """
    Measure how strongly the chunk matches the complete retrieval query.

    Phrase matches receive the strongest signal, followed by token
    coverage. Stop-word filtering is intentionally light and generic so
    the function remains domain-agnostic.
    """

    normalized_content = _normalize_text(content)
    normalized_query = _normalize_text(search_query)

    if not normalized_content or not normalized_query:
        return 0.0

    if normalized_query in normalized_content:
        return 1.0

    query_tokens = _tokenize(normalized_query)

    if not query_tokens:
        return 0.0

    content_tokens = _tokenize(normalized_content)
    matched = len(query_tokens.intersection(content_tokens))

    return max(
        0.0,
        min(1.0, matched / len(query_tokens)),
    )


# =====================================================================
# Keyword coverage
# =====================================================================

def keyword_overlap_score(
    content: str,
    keywords: Iterable[str] | None,
) -> float:
    """
    Measure how many important query keywords occur in a chunk.
    """

    normalized_keywords = _clean_terms(
        keywords
    )

    if not normalized_keywords:
        return 0.0

    matched = sum(
        1
        for keyword in normalized_keywords
        if _contains_term(
            content,
            keyword,
        )
    )

    return matched / len(
        normalized_keywords
    )


# =====================================================================
# Exact-term coverage
# =====================================================================

def exact_match_score(
    matched_terms: Iterable[str] | None,
    exact_terms: Iterable[str] | None,
) -> float:
    """
    Measure coverage of the exact terms required by the query.
    """

    expected = set(
        _clean_terms(exact_terms)
    )

    matched = set(
        _clean_terms(matched_terms)
    )

    if not expected:
        return 0.0

    return len(
        expected.intersection(matched)
    ) / len(expected)


# =====================================================================
# Exact + keyword synergy
# =====================================================================

def exact_keyword_synergy(
    content: str,
    matched_terms: Iterable[str] | None,
    exact_terms: Iterable[str] | None,
    keywords: Iterable[str] | None,
) -> float:
    """
    Reward a chunk containing both:

        exact entity/identifier
        +
        requested keyword information

    This is important for queries such as:

        "What is the email of Name_1?"

    without making any domain-specific assumptions.
    """

    exact = exact_match_score(
        matched_terms,
        exact_terms,
    )

    keyword = keyword_overlap_score(
        content,
        keywords,
    )

    if exact <= 0.0 or keyword <= 0.0:
        return 0.0

    return exact * keyword


# =====================================================================
# Query-type weights
# =====================================================================

def get_query_type_weights(
    query_type: str | None,
) -> dict[str, float]:
    """Return ranking weights for the query type."""

    normalized_type = (
        query_type.strip().lower()
        if isinstance(query_type, str)
        and query_type.strip()
        else DEFAULT_QUERY_TYPE
    )

    return QUERY_TYPE_WEIGHTS.get(
        normalized_type,
        QUERY_TYPE_WEIGHTS[
            DEFAULT_QUERY_TYPE
        ],
    ).copy()


# =====================================================================
# Evidence quality
# =====================================================================

def calculate_evidence_score(
    *,
    semantic: float,
    keyword: float,
    exact: float,
    synergy: float,
    has_exact_terms: bool,
    has_keywords: bool,
) -> float:
    """
    Estimate how completely a chunk satisfies the query.

    This remains domain-agnostic.
    """

    # Entity/identifier + requested attribute.
    if has_exact_terms and has_keywords:
        return (
            semantic * 0.35
            + exact * 0.25
            + keyword * 0.20
            + synergy * 0.20
        )

    # Exact lookup without additional keywords.
    if has_exact_terms:
        return (
            semantic * 0.40
            + exact * 0.60
        )

    # Normal semantic/keyword query.
    if has_keywords:
        return (
            semantic * 0.65
            + keyword * 0.35
        )

    return semantic


# =====================================================================
# Deduplication
# =====================================================================

def _content_key(
    content: Any,
) -> str:
    """Create a normalized key for duplicate detection."""

    return _normalize_text(content)


def _merge_matched_terms(
    first: Iterable[str] | None,
    second: Iterable[str] | None,
) -> list[str]:
    """Merge matched terms without duplicates."""

    merged: list[str] = []
    seen: set[str] = set()

    for term in [
        *(first or []),
        *(second or []),
    ]:
        if not isinstance(term, str):
            continue

        value = term.strip()

        if not value:
            continue

        key = value.lower()

        if key not in seen:
            seen.add(key)
            merged.append(value)

    return merged


def deduplicate_results(
    results: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Remove duplicate chunks using normalized content.
    """

    unique: dict[
        str,
        dict[str, Any],
    ] = {}

    for result in results:

        if not isinstance(result, dict):
            continue

        content = result.get(
            "content",
            "",
        )

        key = _content_key(content)

        if not key:
            continue

        if key not in unique:

            item = dict(result)

            item["matched_terms"] = list(
                result.get(
                    "matched_terms",
                    [],
                )
                or []
            )

            unique[key] = item
            continue

        existing = unique[key]

        existing["matched_terms"] = (
            _merge_matched_terms(
                existing.get(
                    "matched_terms"
                ),
                result.get(
                    "matched_terms"
                ),
            )
        )

        # Prefer a real semantic distance.
        if (
            existing.get("distance") is None
            and result.get("distance") is not None
        ):
            existing["distance"] = (
                result["distance"]
            )

    return list(
        unique.values()
    )


# =====================================================================
# Section-heading relevance
# =====================================================================

def section_heading_score(
    metadata: dict[str, Any] | None,
    keywords: Iterable[str] | None,
) -> float:
    """
    Measure whether the candidate's stored section heading matches
    any meaningful query keyword.

    This is completely domain-agnostic: it uses only metadata produced by
    ingestion and the keywords already produced by Query Understanding.
    """

    if not isinstance(metadata, dict):
        return 0.0

    heading = _normalize_text(
        metadata.get("section_heading")
    )

    if not heading:
        return 0.0

    terms = _clean_terms(keywords)

    # Ignore generic query-management words that do not identify a section.
    ignored = {
        "what", "which", "where", "when", "why", "how",
        "is", "are", "was", "were", "does", "do", "did",
        "the", "a", "an", "of", "for", "to", "in", "on",
        "and", "or", "list", "all", "every", "complete",
        "tell", "me", "about", "give", "show", "explain",
    }

    meaningful_terms = [
        term
        for term in terms
        if term not in ignored
        and len(term) >= 3
    ]

    if not meaningful_terms:
        return 0.0

    matched = sum(
        1
        for term in meaningful_terms
        if _contains_term(heading, term)
    )

    return matched / len(meaningful_terms)


# =====================================================================
# Main reranker
# =====================================================================

def rerank_results(
    results: list[dict[str, Any]],
    *,
    exact_terms: list[str] | None = None,
    keywords: list[str] | None = None,
    query_type: str | None = None,
    exact_candidates_found: bool = False,
    search_query: str | None = None,
    relevance_threshold: float | None = (
        DEFAULT_RELEVANCE_THRESHOLD
    ),
) -> list[dict[str, Any]]:
    """
    Rerank candidate chunks.

    Important Milestone 2 behavior:

    When the query contains exact terms and exact retrieval has found
    matching candidates, candidates that do not contain the required
    exact terms are strongly penalized.

    This prevents a generic keyword-only chunk from beating a chunk
    referring to the actual requested entity.

    For queries with no exact terms, this rule is completely inactive,
    keeping the reranker domain-agnostic.
    """

    if not results:
        return []

    if relevance_threshold is not None:
        if not 0.0 <= relevance_threshold <= 1.0:
            raise ValueError(
                "relevance_threshold must be between "
                "0.0 and 1.0."
            )

    exact_terms = _clean_terms(
        exact_terms
    )

    keywords = _clean_terms(
        keywords
    )

    candidates = deduplicate_results(
        results
    )

    if not candidates:
        return []

    weights = get_query_type_weights(
        query_type
    )

    ranked: list[
        dict[str, Any]
    ] = []

    for candidate_index, result in enumerate(candidates):

        content = result.get(
            "content",
            "",
        )

        # Use the candidate's own semantic signal. Do not normalize this
        # against other candidates because that can turn a genuinely
        # relevant lower-ranked chunk into 0.0.
        semantic = semantic_score(
            result.get("distance")
        )

        keyword = keyword_overlap_score(
            content,
            keywords,
        )

        exact = exact_match_score(
            result.get(
                "matched_terms"
            ),
            exact_terms,
        )

        synergy = exact_keyword_synergy(
            content=content,
            matched_terms=result.get(
                "matched_terms"
            ),
            exact_terms=exact_terms,
            keywords=keywords,
        )

        query_match = query_match_score(
            content,
            search_query,
        )

        evidence = calculate_evidence_score(
            semantic=semantic,
            keyword=keyword,
            exact=exact,
            synergy=synergy,
            has_exact_terms=bool(
                exact_terms
            ),
            has_keywords=bool(
                keywords
            ),
        )

        # -------------------------------------------------------------
        # Base query-aware score
        # -------------------------------------------------------------

        base_score = (
            semantic * weights["semantic"]
            + keyword * weights["keyword"]
            + exact * weights["exact"]
            + synergy * weights["synergy"]
        )

        # Keep the existing score formula intact and add a small, generic
        # boost when the candidate explicitly belongs to a section named by
        # the query. This does not change ranking for candidates without a
        # stored section heading.
        section_score = section_heading_score(
            result.get("metadata"),
            keywords,
        )

        # Keep query-match as a small precision bonus. The score is driven
        # primarily by the candidate's own semantic evidence plus generic
        # lexical/entity signals.
        final_score = (
            base_score * 0.80
            + evidence * 0.15
            + query_match * 0.05
        )

        # Section match is a bounded additive refinement, not a replacement
        # for semantic/lexical relevance. A complete section-name match can
        # contribute at most +0.10.
        if section_score > 0.0:
            final_score = min(
                1.0,
                final_score + (0.10 * section_score),
            )

        # -------------------------------------------------------------
        # Exact-candidate availability penalty
        # -------------------------------------------------------------
        #
        # This is the important refinement discovered from your real
        # FastAPI test.
        #
        # Example:
        #
        # Query:
        #   "What is the email of Name_1?"
        #
        # Candidate:
        #   Name_16 + Email
        #
        # It has "email", but not "Name_1".
        #
        # If exact search already found Name_1 candidates, this
        # candidate should not compete equally with them.
        # -------------------------------------------------------------

        exact_lookup_active = (
            bool(exact_terms)
            and exact_candidates_found
        )

        if exact_lookup_active and exact <= 0.0:

            final_score *= EXACT_MISS_PENALTY

        # -------------------------------------------------------------
        # Entity + attribute safety rule
        # -------------------------------------------------------------
        #
        # If the candidate contains the requested exact term but none
        # of the requested keywords, keep it below a candidate that
        # contains both.
        # -------------------------------------------------------------

        if (
            exact_terms
            and keywords
            and exact > 0.0
            and keyword == 0.0
        ):
            # Preserve the safety intent without imposing an artificial
            # absolute ceiling on genuinely strong exact-entity matches.
            final_score *= 0.85

        # -------------------------------------------------------------
        # Build result metadata
        # -------------------------------------------------------------

        item = dict(result)

        item["semantic_score"] = round(
            semantic,
            6,
        )

        item["keyword_score"] = round(
            keyword,
            6,
        )

        # Keep the existing field name for compatibility.
        item["lexical_score"] = round(
            exact,
            6,
        )

        item["synergy_score"] = round(
            synergy,
            6,
        )

        item["evidence_score"] = round(
            evidence,
            6,
        )

        item["query_match_score"] = round(
            query_match,
            6,
        )

        item["section_heading_score"] = round(
            section_score,
            6,
        )

        item["exact_candidate_available"] = (
            exact_lookup_active
        )

        item["exact_term_match"] = (
            exact > 0.0
        )

        item["relevance_score"] = round(
            max(
                0.0,
                min(
                    1.0,
                    final_score,
                ),
            ),
            6,
        )

        # -------------------------------------------------------------
        # Low-confidence filtering
        # -------------------------------------------------------------

        if (
            relevance_threshold is not None
            and item["relevance_score"]
            < relevance_threshold
        ):
            continue

        ranked.append(item)

    # ---------------------------------------------------------------
    # Final ranking
    # ---------------------------------------------------------------

    ranked.sort(
        key=lambda item: (
            item.get(
                "relevance_score",
                0.0,
            ),
            item.get(
                "synergy_score",
                0.0,
            ),
            item.get(
                "lexical_score",
                0.0,
            ),
            item.get(
                "keyword_score",
                0.0,
            ),
            item.get(
                "semantic_score",
                0.0,
            ),
        ),
        reverse=True,
    )

    return ranked


# =====================================================================
# Final diversification
# =====================================================================

def diversify_results(
    ranked_results: list[dict[str, Any]],
    *,
    max_results: int,
    similarity_threshold: float = 0.85,
) -> list[dict[str, Any]]:
    """
    Select final results while avoiding near-duplicate chunks.

    This remains domain-agnostic and does not require an LLM.
    """

    if max_results <= 0:
        return []

    selected: list[
        dict[str, Any]
    ] = []

    selected_token_sets: list[
        set[str]
    ] = []

    for result in ranked_results:

        if len(selected) >= max_results:
            break

        content = str(
            result.get(
                "content",
                "",
            )
        )

        current_tokens = _tokenize(
            content
        )

        if not current_tokens:
            continue

        is_duplicate = False

        for previous_tokens in selected_token_sets:

            intersection = (
                current_tokens
                & previous_tokens
            )

            union = (
                current_tokens
                | previous_tokens
            )

            if not union:
                continue

            jaccard = (
                len(intersection)
                / len(union)
            )

            if jaccard >= similarity_threshold:
                is_duplicate = True
                break

        if is_duplicate:
            continue

        selected.append(result)
        selected_token_sets.append(
            current_tokens
        )

    return selected