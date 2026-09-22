import json
import re
import uuid
from typing import Any

import chromadb

from app.core.config import CHROMA_DB_PATH

client = chromadb.PersistentClient(
    path=str(CHROMA_DB_PATH)
)

collection = client.get_or_create_collection(
    name="ai_query_resolution"
)


def _sanitize_metadata_value(value: Any) -> Any:
    """
    Convert application metadata into a Chroma-compatible value.

    Chroma accepts primitive metadata values and flat homogeneous lists of
    primitive values. Layout-aware OCR metadata can contain nested structures
    such as:

        [[640.0, 9.0], [768.0, 9.0], [768.0, 33.0], [640.0, 33.0]]

    which Chroma rejects. Preserve those structures by serializing them to
    JSON strings at the storage boundary. The OCR/layout processing itself
    can continue to use the original Python structures before persistence.
    """

    if value is None:
        return ""

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, (list, tuple, dict)):
        # Flat primitive lists are valid Chroma metadata, so preserve them.
        if isinstance(value, (list, tuple)):
            if all(isinstance(item, (str, int, float, bool)) for item in value):
                return list(value)

        # Nested lists / dicts / mixed structures must be serialized.
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    # Handle numpy scalar values or other scalar-like objects without adding
    # a hard dependency on NumPy here.
    try:
        if hasattr(value, "item"):
            scalar = value.item()
            if isinstance(scalar, (str, int, float, bool)):
                return scalar
    except Exception:
        pass

    return str(value)


def _sanitize_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Return a Chroma-safe copy without mutating the original metadata."""

    if not isinstance(metadata, dict):
        return {}

    return {
        str(key): _sanitize_metadata_value(value)
        for key, value in metadata.items()
    }


def add_documents(
    chunks,
    embeddings,
    metadatas=None,
    document_id=None,
):
    # Validate that chunks and embeddings are available.
    if not chunks:
        print("No chunks to store.")
        return

    if not embeddings:
        print("No embeddings to store.")
        return

    # Each chunk must have one corresponding embedding.
    if len(chunks) != len(embeddings):
        raise ValueError(
            "Number of chunks and embeddings must be the same."
        )

    # Create empty metadata when none is provided.
    if metadatas is None:
        metadatas = [{} for _ in chunks]

    if len(metadatas) != len(chunks):
        raise ValueError(
            "Number of chunks and metadata entries must be the same."
        )

    # Sanitize metadata only at the Chroma persistence boundary.
    # This preserves the layout-aware structures everywhere upstream.
    safe_metadatas = [
        _sanitize_metadata(metadata)
        for metadata in metadatas
    ]

    # Create a unique ID for every stored chunk.
    ids = [
        f"{document_id or uuid.uuid4().hex}_{i}"
        for i in range(len(chunks))
    ]

    # Store chunks, embeddings and metadata together.
    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=safe_metadatas,
    )

    print(
        f"{len(chunks)} chunks and embeddings "
        "stored successfully in ChromaDB."
    )


def delete_documents(document_id):
    # Delete all vectors belonging to the document.
    collection.delete(
        where={
            "document_id": document_id
        }
    )


def delete_documents_for_user(document_id, user_id):
    """Delete vectors for a specific document owned by user."""
    collection.delete(
        where={
            "$and": [
                {"document_id": document_id},
                {"user_id": user_id},
            ]
        }
    )


def delete_all_documents_for_user(user_id):
    """Delete all ChromaDB vectors owned by a specific user."""
    collection.delete(
        where={"user_id": user_id},
    )


def search_documents(
    query_embedding,
    k=3,
):
    # Perform semantic vector search.
    return collection.query(
        query_embeddings=[
            query_embedding
        ],
        n_results=k,
    )


def search_documents_for_user(
    query_embedding,
    user_id,
    k=3,
):
    """Semantic search filtered by user_id."""
    return collection.query(
        query_embeddings=[
            query_embedding
        ],
        n_results=k,
        where={"user_id": user_id},
    )


def _contains_exact_term(
    content,
    term,
):
    """
    Check for a complete identifier instead of a substring.

    This prevents Name_1 from matching Name_10 or Name_11.
    """

    normalized_content = content.lower()
    normalized_term = term.lower()

    pattern = (
        r"(?<![\w@.-])"
        + re.escape(normalized_term)
        + r"(?![\w@.-])"
    )

    return re.search(
        pattern,
        normalized_content,
    ) is not None


def search_exact_documents(
    terms,
):
    """
    Search stored chunks for exact identifier matches.

    Useful for values such as Name_1, Name_7 or email addresses.
    """

    if not terms:
        return []

    # Read stored chunks and metadata from ChromaDB.
    stored_data = collection.get(
        include=[
            "documents",
            "metadatas",
        ]
    )

    return _process_exact_search_results(stored_data, terms)


def search_exact_documents_for_user(
    terms,
    user_id,
):
    """Exact search filtered by user_id."""
    if not terms:
        return []

    stored_data = collection.get(
        where={"user_id": user_id},
        include=[
            "documents",
            "metadatas",
        ]
    )

    return _process_exact_search_results(stored_data, terms)


def _process_exact_search_results(stored_data, terms):
    documents = (
        stored_data.get(
            "documents",
            []
        )
        or []
    )

    metadatas = (
        stored_data.get(
            "metadatas",
            []
        )
        or []
    )

    ids = (
        stored_data.get(
            "ids",
            []
        )
        or []
    )

    matches = []

    for index, content in enumerate(
        documents
    ):
        if not content:
            continue

        matched_terms = []

        for term in terms:
            if _contains_exact_term(
                content,
                term,
            ):
                matched_terms.append(term)

        if not matched_terms:
            continue

        metadata = (
            metadatas[index]
            if index < len(metadatas)
            else {}
        )

        document_id = (
            ids[index]
            if index < len(ids)
            else f"exact_{index}"
        )

        matches.append(
            {
                "id": document_id,
                "content": content,
                "metadata": metadata or {},
                "matched_terms": matched_terms,
            }
        )

    return matches


class ChromaService:
    """Class wrapper for ChromaDB client operations."""
    def __init__(self, persistent_client=client):
        self.client = persistent_client

    def get_or_create_collection(self, name: str):
        return self.client.get_or_create_collection(name=name)


chroma_service = ChromaService()


if __name__ == "__main__":

    # Run a simple storage check when this file is executed directly.
    print("ChromaDB service check")
    print(f"Database path: {CHROMA_DB_PATH}")
    print(f"Collection: {collection.name}")
    print(f"Stored vectors: {collection.count()}")

