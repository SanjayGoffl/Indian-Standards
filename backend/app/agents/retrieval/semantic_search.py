"""
Milestone 2 - Semantic Search

Responsibilities:
1. Receive a search-ready query from the Query Understanding Agent.
2. Convert the query into an embedding using the existing
   Milestone 1 embedding infrastructure.
3. Perform semantic search using the existing ChromaDB service.
4. Convert the raw ChromaDB response into the common Retrieval
   Agent result structure.

This module does NOT:
- normalize or classify queries
- extract exact terms
- perform exact search
- merge results
- rerank results
- filter final results
- create a new ChromaDB client
- use an LLM
- use LangGraph
"""

from __future__ import annotations

from typing import Any

from app.rag.chromadb_service import (
    search_documents,
    search_documents_for_user
)
from app.rag.embedding import (
    embed_chunks,
    load_embedding_model,
)


# Load the embedding model once when this module is imported.
# This follows the existing Milestone 1 approach.
embedding_model = load_embedding_model()


def build_semantic_results(
    chroma_results: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Convert the raw ChromaDB response into the common
    Retrieval Agent result structure.

    ChromaDB returns nested lists because one API call can contain
    multiple queries. We send one query at a time, so we use the
    first inner list.

    Expected output structure:

    {
        "chunk_id": str,
        "content": str,
        "metadata": dict,
        "distance": float | None,
        "matched_terms": []
    }
    """

    if not isinstance(chroma_results, dict):
        return []

    documents = (
        chroma_results.get("documents", [[]])[0]
        if chroma_results.get("documents")
        else []
    )

    metadatas = (
        chroma_results.get("metadatas", [[]])[0]
        if chroma_results.get("metadatas")
        else []
    )

    distances = (
        chroma_results.get("distances", [[]])[0]
        if chroma_results.get("distances")
        else []
    )

    ids = (
        chroma_results.get("ids", [[]])[0]
        if chroma_results.get("ids")
        else []
    )

    results: list[dict[str, Any]] = []

    for index, content in enumerate(documents):

        # Ignore empty documents/chunks.
        if not content:
            continue

        metadata = (
            metadatas[index]
            if index < len(metadatas)
            else {}
        )

        distance = (
            distances[index]
            if index < len(distances)
            else None
        )

        result_id = (
            ids[index]
            if index < len(ids)
            else f"semantic_{index}"
        )

        results.append(
            {
                "chunk_id": str(result_id),
                "content": content,
                "metadata": metadata or {},
                "distance": distance,
                "matched_terms": [],
            }
        )

    return results


def search_semantic(
    query: str,
    k: int = 5,
    user_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Perform semantic retrieval against the existing ChromaDB index.

    Args:
        query:
            Search-ready query from the Query Understanding Agent.

        k:
            Number of semantic candidates to retrieve.

        user_id:
            Optional user ID to restrict search to a specific user's knowledge base.

    Returns:
        A list of retrieval results using the common structure:

        {
            "id": str,
            "content": str,
            "metadata": dict,
            "distance": float | None,
            "matched_terms": []
        }
    """

    # -------------------------------------------------------------
    # 1. Validate query
    # -------------------------------------------------------------

    if not isinstance(query, str):
        return []

    query = query.strip()

    if not query:
        return []

    # -------------------------------------------------------------
    # 2. Validate k
    # -------------------------------------------------------------

    if not isinstance(k, int) or isinstance(k, bool):
        return []

    if k <= 0:
        return []

    # -------------------------------------------------------------
    # 3. Generate query embedding
    #
    # IMPORTANT:
    # search_documents() expects an embedding vector, not raw text.
    # -------------------------------------------------------------

    try:
        query_embedding = embed_chunks(
            embedding_model,
            [query],
        )[0]

    except Exception as error:
        print(
            f"Semantic embedding failed: {error}"
        )
        return []

    # -------------------------------------------------------------
    # 4. Perform ChromaDB semantic search
    # -------------------------------------------------------------

    try:
        if user_id:
            chroma_results = search_documents_for_user(
                query_embedding,
                user_id,
                k,
            )
        else:
            chroma_results = search_documents(
                query_embedding,
                k,
            )

    except Exception as error:
        print(
            f"Semantic ChromaDB search failed: {error}"
        )
        return []

    # -------------------------------------------------------------
    # 5. Convert ChromaDB output to Retrieval Agent format
    # -------------------------------------------------------------

    return build_semantic_results(
        chroma_results
    )


if __name__ == "__main__":
    """
    Standalone test.
    """

    print("=" * 60)
    print("Milestone 2 - Semantic Search Test")
    print("=" * 60)

    test_query = "What is the email of Name_1?"
    test_k = 3

    print(f"\nQuery: {test_query}")
    print(f"Top-K: {test_k}")

    try:
        results = search_semantic(
            query=test_query,
            k=test_k,
        )

        print(
            f"\nSemantic results found: {len(results)}"
        )

        for index, result in enumerate(
            results,
            start=1,
        ):
            print(f"\nResult {index}")
            print("-" * 40)
            print("Chunk ID:", result["chunk_id"])
            print("Content:", result["content"])
            print("Metadata:", result["metadata"])
            print("Distance:", result["distance"])
            print(
                "Matched terms:",
                result["matched_terms"],
            )

    except Exception as error:
        print(
            "\nSemantic search test failed:"
        )
        print(error)