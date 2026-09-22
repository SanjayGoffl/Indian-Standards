"""
Domain-agnostic semantic query themes for Milestone 4.

This module keeps the existing semantic clustering behavior, but adds a
per-user in-memory cache so unchanged analytics data does not trigger a full
SentenceTransformer encoding + clustering pass every time the Analytics page
is opened.

The cache is intentionally process-local. It is safe for the application's
existing user-scoped analytics and automatically disappears on a process
restart/deploy. The database remains the source of truth.
"""

from __future__ import annotations

import re
from threading import RLock
from typing import Any

import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.analytics.models import QueryAnalytics
from app.analytics.theme_embedding import embed_queries

import logging
logger = logging.getLogger(__name__)

# Generic tuning parameters; no domain-specific topics are hardcoded.
PAIR_THRESHOLD = 0.62
BRIDGE_THRESHOLD = 0.56
LEXICAL_THRESHOLD = 0.22

LOW_CONFIDENCE_THRESHOLD = 0.50
GAP_SCORE_THRESHOLD = 0.35
MIN_COMMON_THEME_QUERIES = 2

STOP_WORDS = {
    "a", "about", "an", "and", "are", "as", "at", "be", "can", "could",
    "do", "does", "for", "from", "how", "i", "if", "in", "is", "it",
    "me", "my", "of", "on", "or", "please", "the", "this", "to",
    "what", "when", "where", "which", "who", "why", "will", "with",
    "would", "you", "your", "there", "their", "they", "we", "our",
    "should", "give", "tell",
}

TRIVIAL = {
    "yes", "no", "ok", "okay", "thanks", "thank you", "thankyou",
    "hello", "hi", "hey", "sure", "fine", "great", "good",
}

# Per-process cache. Key = authenticated user id.
_THEME_CACHE: dict[str, tuple[tuple[Any, ...], list[dict]]] = {}
_THEME_CACHE_LOCK = RLock()


def _normalize(text: str) -> str:
    return re.sub(r"[-–—]", "", text.lower().strip())


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_]{1,}", _normalize(text))
    return {
        w for w in words
        if w not in STOP_WORDS and not w.isdigit()
    }


def _trivial(text: str) -> bool:
    text = re.sub(r"\s+", " ", text.strip().lower())
    return not text or text in TRIVIAL or not _tokens(text)


def _normalize_embeddings(values) -> np.ndarray:
    matrix = np.asarray(values, dtype=np.float32)
    if len(matrix) == 0:
        return matrix

    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.where(norms == 0, 1, norms)


def _lexical_similarity(a: set[str], b: set[str]) -> float:
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def _similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


def _initial_clusters(
    queries: list[str],
    embeddings: np.ndarray,
) -> list[list[int]]:
    """
    First pass:
    group directly related queries using embeddings and lexical overlap.
    """
    tokens = [_tokens(q) for q in queries]
    parent = list(range(len(queries)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a: int, b: int) -> None:
        a, b = find(a), find(b)
        if a != b:
            parent[b] = a

    for i in range(len(queries)):
        for j in range(i + 1, len(queries)):
            sim = _similarity(embeddings[i], embeddings[j])
            lex = _lexical_similarity(tokens[i], tokens[j])

            if sim >= PAIR_THRESHOLD or lex >= LEXICAL_THRESHOLD:
                union(i, j)

    groups: dict[int, list[int]] = {}
    for i in range(len(queries)):
        groups.setdefault(find(i), []).append(i)

    return list(groups.values())


def _cluster_centroid(
    cluster: list[int],
    embeddings: np.ndarray,
) -> np.ndarray:
    centroid = embeddings[cluster].mean(axis=0)
    norm = np.linalg.norm(centroid)
    return centroid / norm if norm else centroid


def _merge_clusters(
    clusters: list[list[int]],
    embeddings: np.ndarray,
) -> list[list[int]]:
    """
    Second pass:
    merge nearby clusters using centroid similarity.
    """
    clusters = [c[:] for c in clusters]

    changed = True
    while changed and len(clusters) > 1:
        changed = False
        best_pair = None
        best_score = BRIDGE_THRESHOLD

        centroids = [
            _cluster_centroid(c, embeddings)
            for c in clusters
        ]

        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                score = _similarity(centroids[i], centroids[j])

                if score > best_score:
                    best_score = score
                    best_pair = (i, j)

        if best_pair:
            i, j = best_pair
            clusters[i].extend(clusters[j])
            del clusters[j]
            changed = True

    return clusters


def _theme_label(
    queries: list[str],
    index: int,
) -> str:
    """
    Domain-agnostic deterministic label.
    Uses words occurring across the cluster; no predefined topic list.
    """
    counts: dict[str, int] = {}

    for query in queries:
        for word in _tokens(query):
            counts[word] = counts.get(word, 0) + 1

    if not counts:
        return f"Theme {index + 1}"

    common = sorted(
        counts,
        key=lambda w: (-counts[w], -len(w), w),
    )[:3]

    return " / ".join(
        word.replace("_", " ").title()
        for word in common
    )


def _gap_score(
    count: int,
    unanswered: int,
    low_confidence: int,
) -> float:
    if count <= 0:
        return 0.0

    score = (
        0.50 * unanswered / count
        + 0.40 * low_confidence / count
        + 0.10 * min(count / 10.0, 1.0)
    )
    return round(min(score, 1.0), 3)


def _theme_cache_signature(
    db: Session,
    user_id: str,
) -> tuple[Any, ...]:
    """
    Cheap database signature used to decide whether semantic themes are stale.

    We only need to know whether this user's QueryAnalytics dataset changed.
    """
    count, max_id, max_created_at = (
        db.query(
            func.count(QueryAnalytics.id),
            func.max(QueryAnalytics.id),
            func.max(QueryAnalytics.created_at),
        )
        .filter(QueryAnalytics.user_id == user_id)
        .one()
    )

    return (
        int(count or 0),
        int(max_id or 0),
        max_created_at.isoformat() if max_created_at else None,
    )


def _compute_query_themes(
    db: Session,
    user_id: str,
) -> list[dict]:
    rows = (
        db.query(QueryAnalytics)
        .filter(QueryAnalytics.user_id == user_id)
        .order_by(QueryAnalytics.created_at.asc(), QueryAnalytics.id.asc())
        .all()
    )

    # Conversational acknowledgements stay in normal analytics but don't
    # become semantic themes.
    rows = [
        row for row in rows
        if not _trivial((row.query_text or "").strip())
    ]

    if not rows:
        return []

    queries = [(row.query_text or "").strip() for row in rows]
    embeddings = _normalize_embeddings(embed_queries(queries))

    if len(embeddings) != len(queries):
        raise ValueError("Embedding/query count mismatch.")

    clusters = _initial_clusters(queries, embeddings)
    clusters = _merge_clusters(clusters, embeddings)

    total = len(rows)
    themes = []

    for index, cluster in enumerate(clusters):
        cluster_rows = [rows[i] for i in cluster]
        cluster_queries = [
            (row.query_text or "").strip()
            for row in cluster_rows
        ]

        unanswered = sum(
            str(row.response_status or "").lower() == "unanswered"
            for row in cluster_rows
        )

        low_confidence = sum(
            row.confidence_score is not None
            and float(row.confidence_score) < LOW_CONFIDENCE_THRESHOLD
            for row in cluster_rows
        )

        confidence_values = [
            float(row.confidence_score)
            for row in cluster_rows
            if row.confidence_score is not None
        ]

        count = len(cluster_rows)
        avg_confidence = (
            round(sum(confidence_values) / len(confidence_values), 3)
            if confidence_values
            else None
        )

        gap_score = _gap_score(
            count,
            unanswered,
            low_confidence,
        )

        themes.append({
            "theme": _theme_label(cluster_queries, index),
            "query_count": count,
            "query_share_pct": round(count / total * 100, 1),
            "unanswered_count": unanswered,
            "low_confidence_count": low_confidence,
            "average_confidence": avg_confidence,
            "gap_score": gap_score,
            "knowledge_gap": (
                count >= MIN_COMMON_THEME_QUERIES
                and gap_score >= GAP_SCORE_THRESHOLD
            ),
            "representative_query": min(cluster_queries, key=len),
            "queries": cluster_queries,
        })

    themes.sort(
        key=lambda item: (
            -int(item["knowledge_gap"]),
            -item["query_count"],
            -item["gap_score"],
            item["theme"],
        )
    )

    return themes


def get_query_themes(
    db: Session,
    user_id: str,
) -> list[dict]:
    """
    Return cached themes when the user's analytics data is unchanged.

    If a new QueryAnalytics row has been recorded, recompute the semantic
    themes and replace the cache entry for that user.
    """
    signature = _theme_cache_signature(db, user_id)

    with _THEME_CACHE_LOCK:
        cached = _THEME_CACHE.get(user_id)

        if cached is not None and cached[0] == signature:
            print(
                f"QUERY THEMES CACHE HIT | user={user_id} | themes={len(cached[1])}"
            )
            return list(cached[1])

        print(
            f"QUERY THEMES CACHE MISS | user={user_id} | computing themes"
        )

        themes = _compute_query_themes(db, user_id)

        _THEME_CACHE[user_id] = (signature, themes)

        print(
            f"QUERY THEMES CACHE STORED | user={user_id} | themes={len(themes)}"
        )

        return list(themes)