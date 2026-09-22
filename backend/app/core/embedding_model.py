"""
Shared SentenceTransformer model loader.

The RAG pipeline and Analytics query-theme pipeline use the same
embedding model (all-MiniLM-L6-v2).  Keeping one cached model instance
avoids loading the same model twice in the same backend process.
"""

from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer


EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """
    Return the shared SentenceTransformer instance.

    The first caller loads the model. Subsequent callers in the same
    backend process reuse the exact same model object.
    """
    return SentenceTransformer(EMBEDDING_MODEL_NAME)
