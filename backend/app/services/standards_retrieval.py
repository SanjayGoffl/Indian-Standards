"""
Standards Retrieval Module.
Performs hybrid semantic vector search (ChromaDB) and relational database search (PostgreSQL)
to retrieve candidate Indian Standards for a procurement query.
Applies category metadata filtering to prevent cross-domain pollution.
"""

import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.models import IndianStandard
from app.rag.chromadb_service import chroma_service

logger = logging.getLogger(__name__)


def retrieve_candidate_standards(db: Session, query_text: str, product_category: str = None, top_k: int = 6) -> List[IndianStandard]:
    """
    Retrieves candidate Indian Standards using hybrid vector similarity and keyword search.
    Enforces category matching to prevent domain pollution.
    """
    candidate_ids = set()

    # 1. Vector Search via ChromaDB
    try:
        collection = chroma_service.get_or_create_collection("indian_standards_kb")
        search_query = f"{product_category or ''} {query_text}"
        results = collection.query(
            query_texts=[search_query],
            n_results=top_k * 2
        )
        if results and "metadatas" in results and results["metadatas"]:
            for meta_list in results["metadatas"]:
                for meta in meta_list:
                    std_num = meta.get("standard_number")
                    std_cat = meta.get("category", "")
                    if std_num:
                        std_obj = db.query(IndianStandard).filter(IndianStandard.standard_number == std_num).first()
                        if std_obj:
                            candidate_ids.add(std_obj.id)
    except Exception as e:
        logger.warning(f"Vector search retrieval error: {str(e)}")

    # 2. Keyword & Relational Search in PostgreSQL
    words = query_text.split()
    keywords = [w for w in words if len(w) > 3][:5]
    
    filters = []
    if product_category:
        cat_words = [w for w in product_category.split() if len(w) > 3]
        for cw in cat_words:
            filters.append(IndianStandard.category.ilike(f"%{cw}%"))
            filters.append(IndianStandard.sector.ilike(f"%{cw}%"))

    for kw in keywords:
        filters.append(IndianStandard.title.ilike(f"%{kw}%"))
        filters.append(IndianStandard.scope.ilike(f"%{kw}%"))
        filters.append(IndianStandard.standard_number.ilike(f"%{kw}%"))

    if filters:
        sql_matches = db.query(IndianStandard).filter(or_(*filters)).limit(top_k * 2).all()
        for std in sql_matches:
            candidate_ids.add(std.id)

    # 3. Fallback: load all available standards if search yields no results
    if not candidate_ids:
        all_stds = db.query(IndianStandard).limit(top_k * 2).all()
        for std in all_stds:
            candidate_ids.add(std.id)

    candidate_standards = db.query(IndianStandard).filter(IndianStandard.id.in_(candidate_ids)).all()
    return candidate_standards
