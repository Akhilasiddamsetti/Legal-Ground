"""Access-scoped chunk retrieval: BM25 by default, optional hybrid (BM25 + vector).

Access control is enforced first (deny-by-default) so unauthorized chunks can never
reach scoring, the prompt, citations, or evidence.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

from learning_curve.retrieval.bm25 import tokenize
from learning_curve.retrieval.vectors import VectorIndex, reciprocal_rank_fusion
from learning_curve.security.access import Principal, can_access


class ChunkSearchEngine:
    def __init__(self, payload: dict, vector_index: VectorIndex | None = None, embedder=None) -> None:
        self.payload = payload
        self.chunks = payload["chunks"]
        self.vector_index = vector_index
        self.embedder = embedder
        self.avg_doc_len = 0.0
        self.doc_frequencies: Counter[str] = Counter()
        self.chunk_stats: list[dict] = []
        self._build_index()
        self.by_id = {stats["chunk"]["chunk_id"]: stats["chunk"] for stats in self.chunk_stats}

    def _build_index(self) -> None:
        total_tokens = 0

        for chunk in self.chunks:
            metadata_text = " ".join(
                [
                    chunk["doc_title"],
                    chunk.get("section_title", ""),
                    chunk.get("citation_label", ""),
                    " ".join(chunk.get("tags", [])),
                    " ".join(chunk.get("participants", [])),
                    chunk.get("email_subject", "") or "",
                ]
            )
            tokens = tokenize(chunk["search_text"])
            metadata_tokens = tokenize(metadata_text)
            counts = Counter(tokens)
            metadata_counts = Counter(metadata_tokens)
            total_tokens += len(tokens)
            self.chunk_stats.append(
                {
                    "chunk": chunk,
                    "tokens": tokens,
                    "counts": counts,
                    "metadata_counts": metadata_counts,
                }
            )
            self.doc_frequencies.update(set(tokens))

        self.avg_doc_len = total_tokens / len(self.chunk_stats) if self.chunk_stats else 0.0

    def _bm25_rank(self, query_tokens: list[str], allowed: list[dict]) -> list[tuple[str, float]]:
        scored = []
        for stats in allowed:
            score = self._bm25_score(query_tokens, stats)
            if score > 0:
                scored.append((stats["chunk"]["chunk_id"], score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored

    def search(self, query: str, principal: Principal, top_k: int = 5) -> list[dict]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        allowed = [stats for stats in self.chunk_stats if can_access(stats["chunk"], principal)]
        if not allowed:
            return []

        bm25_scored = self._bm25_rank(query_tokens, allowed)
        if self.vector_index is None or self.embedder is None:
            return [
                {"score": score, "chunk": self.by_id[chunk_id]}
                for chunk_id, score in bm25_scored[:top_k]
            ]

        allowed_ids = {stats["chunk"]["chunk_id"] for stats in allowed}
        query_vec = self.embedder.embed_texts([query])[0]
        vector_ranked = self.vector_index.rank(query_vec, allowed_ids)
        fused = reciprocal_rank_fusion([[chunk_id for chunk_id, _ in bm25_scored], vector_ranked])
        return [
            {"score": score, "chunk": self.by_id[chunk_id]}
            for chunk_id, score in fused[:top_k]
        ]

    def _bm25_score(self, query_tokens: list[str], stats: dict) -> float:
        counts = stats["counts"]
        metadata_counts = stats["metadata_counts"]
        doc_len = len(stats["tokens"])
        if doc_len == 0 or self.avg_doc_len == 0:
            return 0.0

        score = 0.0
        k1 = 1.5
        b = 0.75
        num_docs = len(self.chunk_stats)

        for term in query_tokens:
            tf = counts.get(term, 0)
            if tf == 0:
                continue

            df = self.doc_frequencies.get(term, 0)
            idf = math.log(1 + (num_docs - df + 0.5) / (df + 0.5))
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * doc_len / self.avg_doc_len)
            score += idf * (numerator / denominator)

            metadata_tf = metadata_counts.get(term, 0)
            if metadata_tf:
                score += idf * 0.75 * metadata_tf

        return score


def load_payload(chunks_path: Path) -> dict:
    return json.loads(chunks_path.read_text())


def build_preview(text: str, limit: int) -> str:
    collapsed = " ".join(text.split())
    return collapsed if len(collapsed) <= limit else collapsed[: limit - 3] + "..."
