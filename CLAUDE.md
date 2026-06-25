# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A secure RAG assistant for legal **deposition preparation** (Jira epic in [docs/jira-ticket.md](docs/jira-ticket.md)). It answers attorney questions strictly from approved matter documents, with source citations, and abstains when evidence is insufficient. The reference matter is *Acme Manufacturing v. North Ridge Inspections* (`acme-v-northridge`); five more synthetic matters live alongside it for demos. Scope/intent: [docs/phase1-scope-note.md](docs/phase1-scope-note.md); plans: [docs/plans/](docs/plans/).

## Commands

Installable `learning_curve` package (src layout). Use the repo `venv`.

```powershell
# Install (editable, with dev tools: ruff, mypy, pytest)
venv\Scripts\python.exe -m pip install -e ".[dev]"

# Tests (config in pyproject [tool.pytest.ini_options]; no pythonpath hacks)
venv\Scripts\python.exe -m pytest                                   # all 68 tests
venv\Scripts\python.exe -m pytest tests/test_assistant.py::test_name # single test

# Lint / type-check
venv\Scripts\python.exe -m ruff check src tests
venv\Scripts\python.exe -m mypy src

# Console entry points (defined in pyproject [project.scripts])
learning-curve-web --aws-region us-east-1        # web UI at http://127.0.0.1:8000
learning-curve-ask "..." --aws-region us-east-1  # CLI assistant
learning-curve-search "..." --with-vectors       # retrieval only (no LLM/AWS)
learning-curve-eval --with-vectors --fail-under 0.75   # retrieval gate: exit 1 if mean recall@k < threshold
lc-build-chunks --corpus-dir sample-docs/acme-v-northridge   # rebuild chunks.json
lc-build-embeddings --corpus-dir sample-docs/acme-v-northridge  # rebuild embeddings.npz
```

> **Windows sandbox note:** `tmp_path`-based tests can hit `WinError 5` under the default temp dir. Run pytest with `--basetemp=<a writable dir> -p no:cacheprovider` if you see that.

## Package layout & import convention (important)

All code lives in `src/learning_curve/` and uses **absolute imports** (`from learning_curve.security.access import Principal`). The package is installed editable, so there is **no `pythonpath` hack** — never reintroduce `scripts/` or bare-name imports. Subpackages: `security/`, `retrieval/`, `assistant/`, `web/`, `cli/`, `eval/`, `tools/`.

- [config.py](src/learning_curve/config.py) is the single source of paths/knobs, all env-overridable (`LC_CORPUS_DIR`, `LC_LOG_DIR`, `LC_HOST`/`LC_PORT`, `AWS_REGION`, `BEDROCK_MODEL`). Use it instead of `Path(__file__)...` walks.
- [web/runtime.py](src/learning_curve/web/runtime.py) is the **shared wiring layer** for CLI + web: `build_live_runtime()` loads the corpus (single case or `all_cases` portfolio), builds the hybrid engine, attaches a Bedrock `Assistant`, and derives the UI's cases/matters/roles. Change wiring here, not in `cli/ask.py` / `web/app.py`.
- Web assets ([web/templates/](src/learning_curve/web/templates/), [web/static/](src/learning_curve/web/static/)) are **bundled inside the package** and located via the package dir, so they resolve from source, pip-installed, or in Docker. `retrieval/__init__.py` re-exports the public API (`ChunkSearchEngine`, `VectorIndex`, `tokenize`, …) — import from `learning_curve.retrieval`.

## Architecture: the answer pipeline

End-to-end flow (`question → access-filtered retrieval → grounding prompt → LLM → validated citations`), spread across small modules:

1. **Access first, always.** `Assistant.answer` ([assistant/assistant.py](src/learning_curve/assistant/assistant.py)) calls `ChunkSearchEngine.search(query, principal, top_k)` ([retrieval/engine.py](src/learning_curve/retrieval/engine.py)), which applies a **deny-by-default** filter (`can_access` in [security/access.py](src/learning_curve/security/access.py)) **before** any scoring. Unauthorized chunks are dropped before BM25/vector ranking, so they never reach scoring, the prompt, citations, or evidence. This single enforcement point is the security boundary — preserve it. A caller is a frozen `Principal(user_id, role, matter_ids)`.
2. **Retrieval is hybrid-capable, lexical by default.** Okapi BM25 (`engine.py`, tokenization in [retrieval/bm25.py](src/learning_curve/retrieval/bm25.py)) runs by default; `--with-vectors` adds an all-MiniLM-L6-v2 cosine arm ([retrieval/vectors.py](src/learning_curve/retrieval/vectors.py)) fused via `reciprocal_rank_fusion` (RRF).
3. **Empty retrieval short-circuits to abstention with NO LLM call.** Access denial and "no relevant evidence" are intentionally indistinguishable (both → `[]` → abstain), avoiding leaking the existence of restricted chunks.
4. **Grounding contract.** [assistant/prompt.py](src/learning_curve/assistant/prompt.py) builds a fixed system prompt (answer only from evidence, cite every claim, surface conflicts, abstain when unsupported, ignore instructions inside documents) plus a numbered `<evidence>`-delimited user prompt. Model-trusted; code validates citation markers, not entailment.
5. **LLM is AWS Bedrock.** `BedrockLLM` ([assistant/llm.py](src/learning_curve/assistant/llm.py)) wraps `anthropic.AnthropicBedrock`; default is the global Claude Haiku 4.5 inference profile. **A region is required** or construction raises `ValueError`. `LLM` is an interface; tests use `StubLLM` so no network call ever happens.
6. **Citations validated, abstention sentinel-based.** Post-processing regex-extracts `[N]` markers, **range-validates** them against the evidence, maps each to a real chunk. Abstention = reply starts with `ABSTAIN_SENTINEL` ("INSUFFICIENT EVIDENCE").
7. **Every exchange is logged** as one JSON line to `logs/<matter_id>.log.jsonl` via [assistant/logbook.py](src/learning_curve/assistant/logbook.py) (`logs/` gitignored). The web `/threads/{matter}` route replays this history.

## Web app (Case Workspace)

[web/app.py](src/learning_curve/web/app.py) (`create_app`) serves: `GET /` (the Case Workspace SPA), `POST /ask`, `GET /documents/{matter}/{doc_id}` (source viewer, via [web/documents.py](src/learning_curve/web/documents.py)), `GET /threads/{matter}` (history), `/health`, `/favicon.ico`. The front-end ([web/static/app.js](src/learning_curve/web/static/app.js)) is a multi-case workspace: sidebar case cards drive a hidden `matter-select`; an evidence drawer shows retrieved passages + the approved corpus; appearance settings persist in `localStorage`.

## Build pipeline (offline) & corpus layout

A case folder is `sample-docs/<matter>/` with `_meta/metadata.json` (manifest) + raw `.md` docs → [tools/build_chunks.py](src/learning_curve/tools/build_chunks.py) → `_retrieval/chunks.json` → [tools/build_embeddings.py](src/learning_curve/tools/build_embeddings.py) → `_retrieval/embeddings.npz`. [retrieval/corpus_layout.py](src/learning_curve/retrieval/corpus_layout.py) resolves these paths; [retrieval/portfolio.py](src/learning_curve/retrieval/portfolio.py) merges all cases for `all_cases` mode. The legacy flat `sample-docs/{chunks,embeddings,metadata}.json` (single-case `acme-v-northridge`) still works.

## Evaluation & the anti-overfit invariant

[eval/gold_set.json](src/learning_curve/eval/gold_set.json) has 12 questions (9 `grade:"retrieval"` scored by recall@k/precision@k/MRR in [eval/metrics.py](src/learning_curve/eval/metrics.py); 3 `grade:"answer"` for abstention/valid-citation/injection-blocked in [eval/grade_answers.py](src/learning_curve/eval/grade_answers.py)). **Only mean recall@k is an enforced exit-code gate**; the rest is advisory. Baseline in [docs/eval-baseline.md](docs/eval-baseline.md).

**Do not reintroduce overfit heuristics.** [tests/test_no_overfit.py](tests/test_no_overfit.py) guards two invariants: `CANONICAL_TOKENS` (in `retrieval/bm25.py`) must stay **empty** (hand-built synonyms collapsed legally-distinct terms), and `ChunkSearchEngine` must have **no** `_heuristic_boosts` or per-document/Exhibit score boosts.

## Known gaps (when extending)

- **Identity is self-declared.** `--role`/`--matter` (CLI) and the `{matter, role}` request body (web) are trusted as-is — no real authentication maps users to entitlements. The access *filter* is sound; the *identity* feeding it is not.
- **`generate_demo_cases.py` is ~1700 lines and untested** — a candidate for splitting *after* adding test coverage (don't split it blind).
- **Grounding/conflict-surfacing is model-trusted**, not code-verified (no entailment check); relevance scores aren't surfaced to the UI yet.
