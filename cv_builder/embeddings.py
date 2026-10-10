"""Sentence-embedding backend behind a small interface.

`LocalBackend` uses a `sentence-transformers` model and runs offline (no API
key). The `EmbeddingBackend` protocol lets tests inject a deterministic fake
backend (see `tests/test_data_and_retrieval.py`).

`embed()` returns L2-normalised float32 vectors, so cosine similarity is a dot
product.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np

from .config import EmbeddingsConfig


class EmbeddingBackend(Protocol):
    name: str

    def embed(self, texts: list[str]) -> np.ndarray:  # (n, d) float32, unit norm
        ...


def _normalise(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=np.float32)
    norms = np.linalg.norm(v, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return v / norms


class LocalBackend:
    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer  # lazy import

        self.name = f"local:{model_name}"
        self._model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> np.ndarray:
        vecs = self._model.encode(texts, convert_to_numpy=True)
        return _normalise(vecs)


def build_backend(cfg: EmbeddingsConfig) -> EmbeddingBackend:
    if cfg.backend == "local":
        return LocalBackend(cfg.local_model)
    raise ValueError(f"unknown embeddings backend: {cfg.backend!r}")
