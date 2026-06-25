"""Dense vector index and reciprocal-rank fusion for hybrid retrieval."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from legal_ground.retrieval.embeddings import cosine_scores


def reciprocal_rank_fusion(ranked_lists: list[list[str]], c: int = 60) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranking in ranked_lists:
        for rank, key in enumerate(ranking, start=1):
            scores[key] = scores.get(key, 0.0) + 1.0 / (c + rank)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


class VectorIndex:
    def __init__(self, ids: list[str], matrix: np.ndarray) -> None:
        self.ids = ids
        self.matrix = matrix

    @classmethod
    def load(cls, path: Path) -> VectorIndex:
        data = np.load(path, allow_pickle=True)
        return cls([str(value) for value in data["ids"]], data["vectors"])

    def rank(self, query_vec: np.ndarray, allowed_ids: set[str]) -> list[str]:
        scores = cosine_scores(query_vec, self.matrix)
        order = np.argsort(-scores)
        return [self.ids[index] for index in order if self.ids[index] in allowed_ids]
