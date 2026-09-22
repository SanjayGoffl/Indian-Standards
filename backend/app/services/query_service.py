import re
from typing import Any

from app.rag.chromadb_service import (
    search_documents,
    search_exact_documents,
)

from app.rag.embedding import (
    load_embedding_model,
    embed_chunks,
)


# Load the embedding model once when the API starts.
model = load_embedding_model()


def normalize_text(text: str) -> str:
    """Normalize text for matching and duplicate detection."""
    if not text:
        return ""

    text = text.lower()
    text = text.replace("\\_", "_")

    # Normalize whitespace.
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def extract_exact_terms(query: str) -> list[str]:
    """
    Extract identifier-like values from the query.

    Examples:
        Name_1
        Name_7
        email_25@example.com
        user-123
    """

    normalized_query = normalize_text(query)

    terms = []

    # Match identifiers such as Name_1.
    terms.extend(
        re.findall(
            r"\b[\w-]*_[\w-]*\d[\w-]*\b",
            normalized_query,
        )
    )

    # Match email addresses.
    terms.extend(
        re.findall(
            r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b",
            normalized_query,
        )
    )

    # Match other identifiers containing digits.
    terms.extend(
        re.findall(
            r"\b[a-z][a-z0-9-]*\d[a-z0-9-]*\b",
            normalized_query,
        )
    )

    # Remove duplicate terms while preserving order.
    unique_terms = []

    for term in terms:
        if term not in unique_terms:
            unique_terms.append(term)

    return unique_terms


def semantic_score(distance: Any) -> float:
    """
    Convert ChromaDB distance into a ranking score.

    Note:
    This is a retrieval relevance score, not a probability.
    """

    if distance is None:
        return 0.0

    try:
        distance = float(distance)
    except (TypeError, ValueError):
        return 0.0

    if distance < 0:
        distance = 0.0

    return 1.0 / (1.0 + distance)


def build_semantic_results(
    chroma_results: dict,
) -> list[dict]:
    """Convert ChromaDB's nested response into a simple list."""

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

    results = []

    for index, content in enumerate(documents):

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
                "id": result_id,
                "content": content,
                "metadata": metadata or {},
                "distance": distance,
                "matched_terms": [],
            }
        )

    return results


def get_content_key(content: str) -> str:
    """
    Create a normalized key from chunk content.

    This removes duplicate chunks even when they have
    different Chroma IDs or document IDs.
    """

    return normalize_text(content)


def merge_results(
    semantic_results: list[dict],
    exact_results: list[dict],
) -> list[dict]:
    """
    Merge semantic and exact results.

    Duplicate chunks are removed using their content,
    not only their ChromaDB ID.
    """

    merged_by_content = {}

    # Add semantic results first.
    for result in semantic_results:

        content = result.get("content", "")
        content_key = get_content_key(content)

        if not content_key:
            continue

        if content_key not in merged_by_content:
            merged_by_content[content_key] = result

    # Add exact-match results.
    for result in exact_results:

        content = result.get("content", "")
        content_key = get_content_key(content)

        if not content_key:
            continue

        if content_key in merged_by_content:

            # Preserve exact-match information.
            existing = merged_by_content[content_key]

            existing["matched_terms"] = list(
                set(
                    existing.get("matched_terms", [])
                    + result.get("matched_terms", [])
                )
            )

            # Keep the better distance if available.
            existing_distance = existing.get("distance")
            new_distance = result.get("distance")

            if (
                existing_distance is None
                and new_distance is not None
            ):
                existing["distance"] = new_distance

        else:
            merged_by_content[content_key] = result

    return list(merged_by_content.values())


def rerank_results(
    query: str,
    results: list[dict],
) -> list[dict]:
    """
    Rank retrieved chunks using semantic and exact matching.

    Exact identifier matches receive higher priority.
    """

    exact_terms = extract_exact_terms(query)

    has_exact_lookup = bool(exact_terms)

    ranked_results = []

    for result in results:

        distance = result.get("distance")

        semantic = semantic_score(distance)

        matched_terms = result.get(
            "matched_terms",
            [],
        )

        if has_exact_lookup:

            # Exact identifier matches are strongly preferred.
            if matched_terms:

                lexical = (
                    len(matched_terms)
                    / len(exact_terms)
                )

                final_score = (
                    lexical * 0.90
                    + semantic * 0.10
                )

            else:

                final_score = (
                    semantic * 0.10
                )

        else:

            # Normal questions rely mainly on semantic retrieval.
            final_score = semantic

        result["semantic_score"] = round(
            semantic,
            6,
        )

        result["lexical_score"] = round(
            (
                len(matched_terms)
                / len(exact_terms)
            )
            if exact_terms and matched_terms
            else 0.0,
            6,
        )

        result["relevance_score"] = round(
            final_score,
            6,
        )

        ranked_results.append(result)

    # Strongest matches first.
    ranked_results.sort(
        key=lambda item: (
            item["relevance_score"],
            item["semantic_score"],
        ),
        reverse=True,
    )

    return ranked_results


def process_query(
    query: str,
    k: int = 3,
) -> dict:
    """
    Run hybrid retrieval and return the best unique chunks.

    Pipeline:
        Query
          ↓
        Query embedding
          ↓
        Semantic search
          ↓
        Exact identifier search
          ↓
        Duplicate removal
          ↓
        Reranking
          ↓
        Top-k results
    """

    if not query or not query.strip():

        return {
            "success": False,
            "query": query,
            "results": [],
            "message": "Query cannot be empty.",
        }

    if k < 1:

        return {
            "success": False,
            "query": query,
            "results": [],
            "message": "k must be at least 1.",
        }

    query = query.strip()

    try:

        # Convert the query into an embedding.
        query_embedding = embed_chunks(
            model,
            [query],
        )[0]

        # Retrieve more candidates so reranking has
        # enough results to choose from.
        semantic_k = max(
            10,
            k * 5,
        )

        chroma_results = search_documents(
            query_embedding,
            semantic_k,
        )

        semantic_results = build_semantic_results(
            chroma_results
        )

        # Search exact identifiers such as Name_1.
        exact_terms = extract_exact_terms(query)

        exact_results = []

        if exact_terms:

            exact_results = search_exact_documents(
                exact_terms
            )

        # Combine semantic and exact results.
        # Duplicate chunks are removed here.
        combined_results = merge_results(
            semantic_results,
            exact_results,
        )

        # Rank the unique results.
        ranked_results = rerank_results(
            query,
            combined_results,
        )

        # Return only the requested number of chunks.
        final_results = ranked_results[:k]

        results = []

        for result in final_results:

            results.append(
                {
                    "content": result.get(
                        "content",
                        "",
                    ),
                    "metadata": result.get(
                        "metadata",
                        {},
                    ),
                    "distance": result.get(
                        "distance"
                    ),
                    "relevance_score": result.get(
                        "relevance_score",
                        0.0,
                    ),
                    "semantic_score": result.get(
                        "semantic_score",
                        0.0,
                    ),
                    "lexical_score": result.get(
                        "lexical_score",
                        0.0,
                    ),
                    "matched_terms": result.get(
                        "matched_terms",
                        [],
                    ),
                }
            )

        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results),
        }

    except Exception as error:

        return {
            "success": False,
            "query": query,
            "results": [],
            "message": str(error),
        }


if __name__ == "__main__":
    # Simple local test for the retrieval pipeline.
    test_query = "Name_1"

    print("================================")
    print("Query API Retrieval Test")
    print("================================")
    print(f"Query: {test_query}")

    response = process_query(
        test_query,
        k=3,
    )

    if response["success"]:

        print(
            f"Results found: {response['count']}"
        )

        for index, result in enumerate(
            response["results"],
            start=1,
        ):

            metadata = result.get(
                "metadata",
                {},
            )

            print(
                f"\nResult {index}"
            )

            print(
                "Source:",
                metadata.get(
                    "filename",
                    "unknown",
                ),
            )

            print(
                "Chunk:",
                metadata.get(
                    "chunk_index",
                    "unknown",
                ),
            )

            print(
                "Relevance:",
                result.get(
                    "relevance_score",
                    0.0,
                ),
            )

            print(
                "Matched terms:",
                result.get(
                    "matched_terms",
                    [],
                ),
            )

    else:

        print(
            "Query test failed:",
            response.get(
                "message",
                "Unknown error",
            ),
        )