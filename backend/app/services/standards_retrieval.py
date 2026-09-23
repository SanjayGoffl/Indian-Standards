"""
Standards Retrieval Module.
Performs hybrid semantic vector search (ChromaDB) and relational database search (PostgreSQL)
with exact IS-number matching, candidate deduplication, deterministic re-ranking,
and retrieval latency & token context reduction metrics calculation.
Never sends the full standards database to the LLM.
"""

import re
import time
import logging
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.models import IndianStandard
from app.rag.chromadb_service import chroma_service

logger = logging.getLogger(__name__)


def extract_is_numbers(text: str) -> List[str]:
    """
    Extracts explicit IS standard digits/patterns from query text.
    e.g. 'IS 694:2010' -> ['694'], 'IS 7098 (Part 1)' -> ['7098']
    """
    matches = re.findall(r"IS\s*(\d+)", text, re.IGNORECASE)
    return list(set(matches))


def retrieve_candidate_standards(db: Session, query_text: str, product_category: str = None, top_k: int = 10) -> List[IndianStandard]:
    """
    Retrieves candidate Indian Standards using hybrid retrieval (Exact IS lookup + Vector similarity + Keyword).
    Reranks candidates deterministically and returns top K deduplicated candidates.
    """
    res, _ = retrieve_candidate_standards_with_metrics(db, query_text, product_category, top_k)
    return res


def retrieve_candidate_standards_with_metrics(
    db: Session,
    query_text: str,
    product_category: str = None,
    top_k: int = 10
) -> Tuple[List[IndianStandard], Dict[str, Any]]:
    """
    Hybrid retrieval returning candidate standards along with explicit latency and context reduction metrics.
    """
    t_start = time.perf_counter()

    total_indexed_standards = db.query(IndianStandard).count()
    candidate_map: Dict[str, IndianStandard] = {}
    is_numbers = extract_is_numbers(query_text)

    # 1. Exact IS Number Lookup (Highest Priority)
    for is_num in is_numbers:
        exact_matches = db.query(IndianStandard).filter(
            IndianStandard.standard_number.ilike(f"%IS {is_num}%") |
            IndianStandard.standard_number.ilike(f"%IS{is_num}%")
        ).all()
        for std in exact_matches:
            candidate_map[std.id] = std

    # 2. Vector Search via ChromaDB
    try:
        collection = chroma_service.get_or_create_collection("indian_standards_kb")
        search_query = f"{product_category or ''} {query_text}".strip()
        results = collection.query(
            query_texts=[search_query],
            n_results=top_k * 2
        )
        if results and "metadatas" in results and results["metadatas"]:
            for meta_list in results["metadatas"]:
                for meta in meta_list:
                    std_num = meta.get("standard_number")
                    if std_num:
                        std_obj = db.query(IndianStandard).filter(IndianStandard.standard_number == std_num).first()
                        if std_obj:
                            candidate_map[std_obj.id] = std_obj
    except Exception as e:
        logger.warning(f"Vector search retrieval warning: {str(e)}")

    # 3. Keyword Search in PostgreSQL
    words = [w for w in query_text.split() if len(w) > 3]
    keywords = words[:6]

    filters = []
    if product_category:
        cat_words = [w for w in product_category.split() if len(w) > 3]
        for cw in cat_words:
            filters.append(IndianStandard.category.ilike(f"%{cw}%"))
            filters.append(IndianStandard.sector.ilike(f"%{cw}%"))

    for kw in keywords:
        filters.append(IndianStandard.title.ilike(f"%{kw}%"))
        filters.append(IndianStandard.scope.ilike(f"%{kw}%"))

    if filters:
        sql_matches = db.query(IndianStandard).filter(or_(*filters)).limit(top_k * 2).all()
        for std in sql_matches:
            candidate_map[std.id] = std

    raw_retrieved_count = len(candidate_map)

    # 4. Fallback if empty
    if not candidate_map:
        all_stds = db.query(IndianStandard).limit(top_k).all()
        for std in all_stds:
            candidate_map[std.id] = std
        raw_retrieved_count = len(candidate_map)

    candidates = list(candidate_map.values())

    # 5. Deterministic Candidate Re-ranking
    def score_candidate(std: IndianStandard) -> float:
        score = 0.0
        # Exact IS number match boost
        for is_num in is_numbers:
            if f"IS {is_num}" in std.standard_number or f"IS{is_num}" in std.standard_number:
                score += 10.0

        # Category alignment
        if product_category and std.category:
            cat_words = [w.lower() for w in product_category.split() if len(w) > 3]
            for cw in cat_words:
                if cw in std.category.lower() or cw in (std.sector or "").lower():
                    score += 3.0

        # Keyword overlap
        title_lower = (std.title or "").lower()
        scope_lower = (std.scope or "").lower()

        for kw in keywords:
            kw_l = kw.lower()
            if kw_l in title_lower:
                score += 1.5
            elif kw_l in scope_lower:
                score += 0.5

        return score

    candidates.sort(key=score_candidate, reverse=True)
    selected_candidates = candidates[:top_k]

    t_end = time.perf_counter()
    retrieval_duration_ms = round((t_end - t_start) * 1000, 2)

    total_catalog = max(total_indexed_standards, len(selected_candidates), 1)
    sent_count = len(selected_candidates)
    reduction_pct = round((1.0 - (sent_count / total_catalog)) * 100, 2)

    metrics = {
        "total_indexed_standards": total_indexed_standards,
        "candidates_retrieved": raw_retrieved_count,
        "candidates_sent_to_llm": sent_count,
        "retrieval_time_ms": retrieval_duration_ms,
        "context_reduction_percent": max(0.0, reduction_pct)
    }

    return selected_candidates, metrics
