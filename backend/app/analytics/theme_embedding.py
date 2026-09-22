"""
Embedding helpers for Analytics query-theme analysis.

Query themes intentionally use the same embedding model as RAG.  The
shared loader prevents a second all-MiniLM-L6-v2 model instance from being
created in the same backend process.
"""

from __future__ import annotations

from app.core.embedding_model import get_embedding_model


# Kept as a compatibility constant for any code that imports it.
THEME_EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def load_theme_embedding_model():
    """
    Return the shared SentenceTransformer instance.

    This function remains available so existing analytics imports do not
    need to change, but it now delegates to the single shared model loader.
    """
    return get_embedding_model()


def embed_queries(queries: list[str]) -> list[list[float]]:
    """Return normalized embeddings for the supplied query texts."""
    if not queries:
        return []

    model = get_embedding_model()

    embeddings = model.encode(
        queries,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    return embeddings.tolist()