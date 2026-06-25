# Retrieval Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the overfit, corpus-specific retrieval with something that generalizes: remove the legally-distorting synonym map and the hardcoded per-document boosts, add semantic (vector) search, and fuse it with BM25 using Reciprocal Rank Fusion (RRF) — all gated by the evaluation harness so we can prove it didn't regress.

**Architecture:** Add a pluggable embedding model (`scripts/embeddings.py`, default `sentence-transformers/all-MiniLM-L6-v2`, swappable for Azure OpenAI in production). A build script writes one vector per chunk to `sample-docs/embeddings.npz`. `ChunkSearchEngine` gains an *optional* vector arm: when embeddings are loaded, `search()` ranks chunks by BM25 and by cosine similarity over the access-allowed set, then fuses the two rankings with RRF. When no vectors are loaded, it stays BM25-only, so existing tests keep working. Access filtering from [plans/02-access-control.md](02-access-control.md) is applied to **both** arms.

**Tech Stack:** Python 3.12, `sentence-transformers` + `numpy` (new runtime deps). RRF for fusion (no score normalization needed).

## Global Constraints

- Python: 3.12.5; run through `venv\Scripts\python.exe`.
- Do [plans/01-evaluation-harness.md](01-evaluation-harness.md) and [plans/02-access-control.md](02-access-control.md) first. This plan gates on the harness and must preserve access control.
- **The hybrid retriever must score mean recall@5 ≥ the keyword-only baseline in `eval/BASELINE.md`.** That is the acceptance gate for this plan.
- The vector arm is **additive and optional**: `ChunkSearchEngine(payload)` with no vector index must behave exactly as the BM25-only engine (so plan 01/02 tests still pass unchanged).
- Embedding provider is behind an interface. Default local model: `sentence-transformers/all-MiniLM-L6-v2` (384-dim, normalized). Production swaps in Azure OpenAI `text-embedding-3-large` behind the same `embed_texts` method — that swap is the only change needed.
- First run downloads the model (~90 MB) from Hugging Face; embeddings are then cached in `sample-docs/embeddings.npz` and reused offline.

---

### Task 1: Embedding model + similarity helper

**Files:**
- Create: `requirements.txt` (first runtime dependency file)
- Create: `scripts/embeddings.py`
- Test: `tests/test_embeddings.py`

**Interfaces:**
- Produces:
  - `Embedder` protocol with `embed_texts(self, texts: list[str]) -> np.ndarray` (returns `(n, d)` float32, L2-normalized rows).
  - `SentenceTransformerEmbedder(model_name=...)` — default implementation.
  - `cosine_scores(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray` — dot product (valid because rows are normalized), returns `(n,)`.

- [ ] **Step 1: Declare runtime dependencies**

`requirements.txt`:
```
numpy>=1.26
sentence-transformers>=2.7
```

- [ ] **Step 2: Install them**

Run: `venv\Scripts\python.exe -m pip install -r requirements.txt`
Expected: installs numpy, torch, sentence-transformers (this is a large download; allow time).

- [ ] **Step 3: Write the failing test**

`tests/test_embeddings.py`:
```python
import numpy as np
from embeddings import cosine_scores


def test_cosine_scores_ranks_parallel_vector_highest():
    matrix = np.array([[1.0, 0.0], [0.0, 1.0], [0.7071, 0.7071]], dtype=np.float32)
    query = np.array([1.0, 0.0], dtype=np.float32)
    scores = cosine_scores(query, matrix)
    assert int(np.argmax(scores)) == 0          # identical direction wins
    assert scores[2] > scores[1]                # 45-degree beats orthogonal


def test_embedder_shape_and_norm():
    from embeddings import SentenceTransformerEmbedder
    embedder = SentenceTransformerEmbedder()
    vecs = embedder.embed_texts(["failed inspection report", "shipment release approval"])
    assert vecs.shape[0] == 2
    norms = np.linalg.norm(vecs, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-3)   # rows are L2-normalized
```

- [ ] **Step 4: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_embeddings.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'embeddings'`

- [ ] **Step 5: Write the implementation**

`scripts/embeddings.py`:
```python
"""Pluggable text embedding. Default is a local sentence-transformers model;
production swaps SentenceTransformerEmbedder for an Azure OpenAI embedder behind
the same embed_texts() method."""

from __future__ import annotations

from typing import Protocol

import numpy as np


class Embedder(Protocol):
    def embed_texts(self, texts: list[str]) -> np.ndarray:
        ...


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(model_name)

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return np.asarray(vectors, dtype=np.float32)


def cosine_scores(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Rows of `matrix` and `query_vec` are L2-normalized, so cosine == dot."""
    return matrix @ query_vec
```

- [ ] **Step 6: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_embeddings.py -v`
Expected: PASS (2 passed; the second test downloads the model on first run).

- [ ] **Step 7: Commit**

```bash
git add requirements.txt scripts/embeddings.py tests/test_embeddings.py
git commit -m "feat: add pluggable embedding model and cosine similarity helper"
```

---

### Task 2: Build the chunk embeddings

**Files:**
- Create: `scripts/build_embeddings.py`
- Create (generated): `sample-docs/embeddings.npz`
- Test: `tests/test_build_embeddings.py`

**Interfaces:**
- Consumes: `sample-docs/chunks.json`, `SentenceTransformerEmbedder`.
- Produces: `sample-docs/embeddings.npz` containing `ids` (array of `chunk_id`) and `vectors` (`(n, d)` float32), aligned by index. `VectorIndex.load(path)` (Task 3) reads it.

- [ ] **Step 1: Write the failing test**

`tests/test_build_embeddings.py`:
```python
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
NPZ = ROOT / "sample-docs" / "embeddings.npz"
CHUNKS = json.loads((ROOT / "sample-docs" / "chunks.json").read_text())


def test_embeddings_file_aligns_with_chunks():
    assert NPZ.exists(), "run: venv\\Scripts\\python.exe scripts\\build_embeddings.py"
    data = np.load(NPZ, allow_pickle=True)
    ids = list(data["ids"])
    vectors = data["vectors"]
    chunk_ids = [c["chunk_id"] for c in CHUNKS["chunks"]]
    assert ids == chunk_ids                       # same order, same count
    assert vectors.shape[0] == len(chunk_ids)
    assert vectors.shape[1] >= 128                # real embedding dimension
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_build_embeddings.py -v`
Expected: FAIL on the `NPZ.exists()` assertion.

- [ ] **Step 3: Write the build script**

`scripts/build_embeddings.py`:
```python
import json
from pathlib import Path

import numpy as np

from embeddings import SentenceTransformerEmbedder

ROOT = Path(__file__).resolve().parent.parent
CHUNKS_PATH = ROOT / "sample-docs" / "chunks.json"
OUTPUT_PATH = ROOT / "sample-docs" / "embeddings.npz"


def main() -> None:
    chunks = json.loads(CHUNKS_PATH.read_text())["chunks"]
    ids = [chunk["chunk_id"] for chunk in chunks]
    texts = [chunk["search_text"] for chunk in chunks]
    vectors = SentenceTransformerEmbedder().embed_texts(texts)
    np.savez(OUTPUT_PATH, ids=np.array(ids, dtype=object), vectors=vectors)
    print(f"Wrote {vectors.shape[0]} embeddings ({vectors.shape[1]}-dim) to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Generate the embeddings**

Run: `venv\Scripts\python.exe scripts\build_embeddings.py`
Expected: prints `Wrote N embeddings (384-dim) to ...embeddings.npz`

- [ ] **Step 5: Run the test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_build_embeddings.py -v`
Expected: PASS

- [ ] **Step 6: Commit (and decide whether to track the .npz)**

Track the generated file so the harness and assistant are reproducible without re-embedding:
```bash
git add scripts/build_embeddings.py tests/test_build_embeddings.py sample-docs/embeddings.npz
git commit -m "feat: build and store per-chunk embeddings"
```

---

### Task 3: Remove the overfit synonyms and per-document boosts

**Files:**
- Modify: `scripts/search_chunks.py` (`CANONICAL_TOKENS` at lines 52-95; `_heuristic_boosts` at lines 212-259; its call site in `search`)
- Test: `tests/test_no_overfit.py`

**Interfaces:**
- Produces: tokenization that no longer collapses legally-distinct terms, and a `search()` that no longer adds corpus-specific boosts. `_bm25_score` stays. Recall may drop here — that is expected and is recovered by the vector arm in Task 4. Do **not** re-gate the harness until Task 5.

- [ ] **Step 1: Write the failing test**

`tests/test_no_overfit.py`:
```python
from search_chunks import normalize_token, ChunkSearchEngine


def test_legally_distinct_terms_are_not_collapsed():
    # "approval" must NOT become "release"; "deposition" must NOT become "witness".
    assert normalize_token("approval") != normalize_token("release")
    assert normalize_token("deposition") != normalize_token("witness")


def test_no_heuristic_boosts_method():
    # The corpus-specific boost layer is gone.
    assert not hasattr(ChunkSearchEngine, "_heuristic_boosts")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_no_overfit.py -v`
Expected: FAIL (the synonyms still collapse and `_heuristic_boosts` still exists).

- [ ] **Step 3: Empty the synonym map**

In `scripts/search_chunks.py`, replace the entire `CANONICAL_TOKENS = { ... }` block (lines 52-95) with:
```python
# Intentionally empty: hand-built synonym collapsing distorted legally-distinct
# terms (e.g. approval->release, deposition->witness). Semantic matching is now
# the vector arm's job. Only morphological suffix stripping remains below.
CANONICAL_TOKENS: dict[str, str] = {}
```

- [ ] **Step 4: Remove the `_heuristic_boosts` method and its call**

Delete the whole `_heuristic_boosts` method (lines 212-259). In `search`, remove the line:
```python
            score += self._heuristic_boosts(query, query_tokens, stats)
```
so scoring is BM25-only for the keyword arm:
```python
            score = self._bm25_score(query_tokens, stats)
            if score > 0:
                results.append({"score": score, "chunk": stats["chunk"]})
```

- [ ] **Step 5: Run the overfit test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_no_overfit.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Run the harness to observe the drop (informational, not a gate)**

Run: `venv\Scripts\python.exe -m eval.run_eval --top-k 5`
Expected: mean recall@5 likely drops vs `eval/BASELINE.md`. Note the number; Task 4 recovers it. Do not "fix" by re-adding boosts.

- [ ] **Step 7: Commit**

```bash
git add scripts/search_chunks.py tests/test_no_overfit.py
git commit -m "refactor: remove overfit synonyms and corpus-specific retrieval boosts"
```

---

### Task 4: Add the vector arm and RRF fusion

**Files:**
- Modify: `scripts/search_chunks.py` (`ChunkSearchEngine.__init__`, `search`; add `reciprocal_rank_fusion`, `_bm25_rank`, and a `VectorIndex`)
- Test: `tests/test_hybrid_search.py`

**Interfaces:**
- Produces:
  - `reciprocal_rank_fusion(ranked_lists: list[list[str]], c: int = 60) -> list[tuple[str, float]]` — keys are `chunk_id`s.
  - `VectorIndex(ids, matrix)` with `.load(path)` and `.rank(query_vec, allowed_ids: set[str]) -> list[str]`.
  - `ChunkSearchEngine(payload, vector_index=None, embedder=None)` — when both are provided, `search` fuses BM25 and vector rankings; otherwise BM25-only (unchanged behavior).

- [ ] **Step 1: Write the failing test**

`tests/test_hybrid_search.py`:
```python
import json
from pathlib import Path

from search_chunks import ChunkSearchEngine, reciprocal_rank_fusion, VectorIndex
from embeddings import SentenceTransformerEmbedder
from access import pilot_principal

ROOT = Path(__file__).resolve().parent.parent
PAYLOAD = json.loads((ROOT / "sample-docs" / "chunks.json").read_text())
NPZ = ROOT / "sample-docs" / "embeddings.npz"


def test_rrf_rewards_agreement():
    fused = dict(reciprocal_rank_fusion([["a", "b", "c"], ["b", "a", "d"]]))
    assert fused["a"] > fused["c"]   # a is high in both lists
    assert fused["b"] > fused["d"]


def test_hybrid_engine_returns_access_filtered_results():
    index = VectorIndex.load(NPZ)
    engine = ChunkSearchEngine(PAYLOAD, vector_index=index,
                               embedder=SentenceTransformerEmbedder())
    results = engine.search("Who released the shipment after the failed inspection?",
                            pilot_principal(), top_k=5)
    assert 0 < len(results) <= 5
    # access still enforced on the vector arm:
    from access import Principal
    outsider = Principal("x", "pilot_user", frozenset({"other-matter"}))
    assert engine.search("inspection", outsider, top_k=5) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_hybrid_search.py -v`
Expected: FAIL — `reciprocal_rank_fusion` / `VectorIndex` do not exist yet.

- [ ] **Step 3: Add the fusion function and VectorIndex (module level in `search_chunks.py`)**

Add near the top of `scripts/search_chunks.py` (after imports), and import numpy:
```python
import numpy as np
from embeddings import cosine_scores


def reciprocal_rank_fusion(ranked_lists: list[list[str]], c: int = 60) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranking in ranked_lists:
        for rank, key in enumerate(ranking, start=1):
            scores[key] = scores.get(key, 0.0) + 1.0 / (c + rank)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)


class VectorIndex:
    def __init__(self, ids: list[str], matrix: "np.ndarray") -> None:
        self.ids = ids
        self.matrix = matrix
        self._row_of = {chunk_id: i for i, chunk_id in enumerate(ids)}

    @classmethod
    def load(cls, path) -> "VectorIndex":
        data = np.load(path, allow_pickle=True)
        return cls([str(x) for x in data["ids"]], data["vectors"])

    def rank(self, query_vec: "np.ndarray", allowed_ids: set[str]) -> list[str]:
        scores = cosine_scores(query_vec, self.matrix)
        order = np.argsort(-scores)
        return [self.ids[i] for i in order if self.ids[i] in allowed_ids]
```

- [ ] **Step 4: Make the engine vector-aware**

Change `__init__` to accept the optional vector arm and build a `chunk_id -> chunk` map:
```python
    def __init__(self, payload: dict, vector_index=None, embedder=None) -> None:
        self.payload = payload
        self.chunks = payload["chunks"]
        self.vector_index = vector_index
        self.embedder = embedder
        self.avg_doc_len = 0.0
        self.doc_frequencies: Counter[str] = Counter()
        self.chunk_stats: list[dict] = []
        self._build_index()
        self.by_id = {s["chunk"]["chunk_id"]: s["chunk"] for s in self.chunk_stats}
```

- [ ] **Step 5: Add a BM25 ranking helper and rewrite `search` to fuse**

Add:
```python
    def _bm25_rank(self, query_tokens: list[str], allowed: list[dict]) -> list[str]:
        scored = []
        for stats in allowed:
            score = self._bm25_score(query_tokens, stats)
            if score > 0:
                scored.append((stats["chunk"]["chunk_id"], score))
        scored.sort(key=lambda kv: kv[1], reverse=True)
        return [chunk_id for chunk_id, _ in scored]
```
Replace `search` with:
```python
    def search(self, query: str, principal: Principal, top_k: int = 5) -> list[dict]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        allowed = [s for s in self.chunk_stats if can_access(s["chunk"], principal)]
        if not allowed:
            return []
        allowed_ids = {s["chunk"]["chunk_id"] for s in allowed}

        bm25_ranked = self._bm25_rank(query_tokens, allowed)
        ranked_lists = [bm25_ranked]

        if self.vector_index is not None and self.embedder is not None:
            query_vec = self.embedder.embed_texts([query])[0]
            ranked_lists.append(self.vector_index.rank(query_vec, allowed_ids))

        fused = reciprocal_rank_fusion(ranked_lists)
        return [{"score": score, "chunk": self.by_id[chunk_id]}
                for chunk_id, score in fused[:top_k]]
```

- [ ] **Step 6: Run the hybrid test**

Run: `venv\Scripts\python.exe -m pytest tests/test_hybrid_search.py -v`
Expected: PASS (2 passed)

- [ ] **Step 7: Run the full suite (confirm BM25-only callers still pass)**

Run: `venv\Scripts\python.exe -m pytest -q`
Expected: all pass. Plan 01/02 tests construct `ChunkSearchEngine(PAYLOAD)` with no vector arm and must still work.

- [ ] **Step 8: Commit**

```bash
git add scripts/search_chunks.py tests/test_hybrid_search.py
git commit -m "feat: add vector arm and RRF hybrid fusion to search"
```

---

### Task 5: Wire vectors into the harness and gate the rebuild

**Files:**
- Modify: `eval/run_eval.py` (add an optional `--with-vectors` flag that loads the index/embedder)
- Modify: `eval/BASELINE.md` (append the hybrid numbers next to the keyword baseline)

**Interfaces:**
- Consumes: `VectorIndex`, `SentenceTransformerEmbedder`.
- Produces: `run_eval --with-vectors` builds a hybrid engine; the comparison proves the gate.

- [ ] **Step 1: Add the flag and wiring to `eval/run_eval.py`**

Add imports:
```python
from search_chunks import VectorIndex  # noqa: E402
from embeddings import SentenceTransformerEmbedder  # noqa: E402
```
Add the arg in `main()`:
```python
    parser.add_argument("--with-vectors", action="store_true",
                        help="Load embeddings and run hybrid (BM25 + vector) retrieval.")
```
Build the engine accordingly:
```python
    if args.with_vectors:
        index = VectorIndex.load(ROOT / "sample-docs" / "embeddings.npz")
        engine = ChunkSearchEngine(load_payload(CHUNKS_PATH), vector_index=index,
                                   embedder=SentenceTransformerEmbedder())
    else:
        engine = ChunkSearchEngine(load_payload(CHUNKS_PATH))
```

- [ ] **Step 2: Run both configurations**

Run: `venv\Scripts\python.exe -m eval.run_eval --top-k 5`               (BM25-only, post-de-overfit)
Run: `venv\Scripts\python.exe -m eval.run_eval --top-k 5 --with-vectors` (hybrid)
Record both summary lines.

- [ ] **Step 3: Check the gate**

The hybrid mean recall@5 must be ≥ the keyword baseline recorded in `eval/BASELINE.md`. Pay special attention to `q04-deposition-vs-discovery-conflict` (the cross-document case) and `q11`/semantic phrasings — vectors should help most there. If hybrid does NOT beat the baseline, do not proceed: investigate (try `c=10` in RRF, or check that embeddings cover all chunks) and re-measure.

- [ ] **Step 4: Enforce the gate in CI form**

Run: `venv\Scripts\python.exe -m eval.run_eval --top-k 5 --with-vectors --fail-under <baseline_recall>`
(substitute the recorded baseline number). Expected: exit 0.

- [ ] **Step 5: Append results to the baseline doc and commit**

Update `eval/BASELINE.md` with a short table: keyword-only (original) vs BM25-only (de-overfit) vs hybrid, for mean recall@5 / MRR / pass rate. One sentence on which questions improved.
```bash
git add eval/run_eval.py eval/BASELINE.md
git commit -m "feat: evaluate hybrid retrieval and gate it against the keyword baseline"
```

---

## Self-Review

- **Spec coverage:** Removes the overfit synonyms (Task 3 `test_legally_distinct_terms_are_not_collapsed`) and per-document boosts (Task 3 `test_no_heuristic_boosts_method`), satisfying the review's "won't generalize" finding. Adds the ticket's required hybrid keyword+vector retrieval (Tasks 1–4). Access control from plan 02 is preserved on both arms (Task 4 test). The harness gates the change (Task 5).
- **Placeholder scan:** `<baseline_recall>` in Task 4 Step 4 and `<baseline_number>` references are values the executor reads from `eval/BASELINE.md` at run time, not unfinished plan content — every code block is complete.
- **Type consistency:** fusion keys are `chunk_id` strings throughout; `VectorIndex.rank` and `_bm25_rank` both return `list[str]` of `chunk_id`; `search` maps them back via `self.by_id`. `ChunkSearchEngine(payload, vector_index=None, embedder=None)` signature is used consistently in tests and the harness.

## Notes / Limits (for the learner)

- `all-MiniLM-L6-v2` is a general-purpose model, not legal-domain-tuned; it is good enough to demonstrate hybrid retrieval but a production legal system would evaluate domain or larger embeddings. Because everything is graded by the harness, swapping models later is a measured change, not a guess.
- RRF needs no score calibration between BM25 and cosine, which is exactly why it is the safe first fusion method. A later refinement could weight the arms, but only if the harness shows it helps.

## Execution Handoff

Run task-by-task with **superpowers:subagent-driven-development** or **superpowers:executing-plans**. When the gate passes, proceed to [plans/04-assistant-grounding.md](04-assistant-grounding.md).
