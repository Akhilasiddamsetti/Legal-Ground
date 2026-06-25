"""Pluggable text embedding support for retrieval."""

from __future__ import annotations

from typing import Protocol

import numpy as np


class Embedder(Protocol):
    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Return an (n, d) float32 matrix with L2-normalized rows."""


class SentenceTransformerEmbedder:
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        local_files_only: bool = True,
    ) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name, local_files_only=local_files_only)

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return np.asarray(vectors, dtype=np.float32)


def cosine_scores(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Rows of `matrix` and `query_vec` are L2-normalized, so cosine == dot."""
    return matrix @ query_vec
