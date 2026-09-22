"""
Milestone 2 - Exact Search

This module receives exact terms extracted by the
Query Understanding Agent and reuses the existing
Milestone 1 exact-search implementation.

Responsibilities:
1. Validate exact terms.
2. Clean and deduplicate terms.
3. Call the existing RAG exact-search function.
4. Normalize results into the common Retrieval Agent format.

This module does NOT:
- Extract exact terms from the user query.
- Create an embedding model.
- Create a ChromaDB client.
- Perform semantic search.
- Merge semantic and exact results.
- Rerank results.
- Use an LLM.
- Use LangGraph.
"""

from __future__ import annotations

from typing import Any

from app.rag.chromadb_service import (
    search_exact_documents,
    search_exact_documents_for_user
)


def search_exact(
    exact_terms: list[str],
    user_id: str | None = None
) -> list[dict[str, Any]]:
    """
    Search the indexed knowledge base using exact terms.

    The exact terms are expected to come from the
    Query Understanding Agent.

    Args:
        exact_terms:
            Identifier-like terms that should be searched exactly.
            Examples:
                - "Name_1"
                - "Name_7"
                - "email_25@example.com"
                - "user-123"

    Returns:
        A list of retrieval results using the common structure:

        {
            "chunk_id": str,
            "content": str,
            "metadata": dict,
            "distance": float | None,
            "matched_terms": list[str],
        }

        Returns an empty list when no valid exact terms are provided.
    """

    # ---------------------------------------------------------
    # 1. Validate input
    # ---------------------------------------------------------

    if not exact_terms:
        return []

    # ---------------------------------------------------------
    # 2. Clean invalid terms
    # ---------------------------------------------------------

    cleaned_terms: list[str] = []

    for term in exact_terms:
        if not isinstance(term, str):
            continue

        cleaned_term = term.strip()

        if cleaned_term:
            cleaned_terms.append(cleaned_term)

    if not cleaned_terms:
        return []

    # ---------------------------------------------------------
    # 3. Remove duplicates while preserving order
    # ---------------------------------------------------------

    unique_terms = list(dict.fromkeys(cleaned_terms))

    # ---------------------------------------------------------
    # 4. Reuse the existing Milestone 1 exact-search logic
    # ---------------------------------------------------------

    if user_id:
        exact_results = search_exact_documents_for_user(unique_terms, user_id)
    else:
        exact_results = search_exact_documents(unique_terms)

    # ---------------------------------------------------------
    # 5. Normalize results into the common Retrieval format
    # ---------------------------------------------------------

    normalized_results: list[dict[str, Any]] = []

    for result in exact_results:
        if not isinstance(result, dict):
            continue

        matched_terms = result.get("matched_terms", [])

        if not isinstance(matched_terms, list):
            matched_terms = []

        normalized_results.append(
            {
                "chunk_id": result.get("id", ""),
                "content": result.get("content", ""),
                "metadata": result.get("metadata", {}),
                "distance": result.get("distance"),
                "matched_terms": list(matched_terms),
            }
        )

    return normalized_results


if __name__ == "__main__":
    """
    Standalone test.

    This is only for development/testing and is not used by
    the application during normal execution.
    """

    print("=" * 60)
    print("Milestone 2 - Exact Search Test")
    print("=" * 60)

    test_exact_terms = [
        "Name_1",
        "Name_7",
        "email_25@example.com",
    ]

    print("\nExact terms:")
    for term in test_exact_terms:
        print(f"  - {term}")

    try:
        results = search_exact(test_exact_terms)

        print(f"\nExact results found: {len(results)}")

        for index, result in enumerate(results, start=1):
            print(f"\nResult {index}")
            print("-" * 40)
            print("Chunk ID:", result["chunk_id"])
            print("Content:", result["content"])
            print("Metadata:", result["metadata"])
            print("Distance:", result["distance"])
            print("Matched terms:", result["matched_terms"])

    except Exception as error:
        print("\nExact search test failed:")
        print(error)