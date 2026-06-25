# Production-Grade Package Restructure — Migration Plan

> Executed with superpowers:executing-plans. Pure restructuring — **no behavior changes**. The 68 passing tests are the safety net; the suite must be green at every checkpoint. Baseline restore point: commit `1dd4598` on branch `case-workspace-sp1`.

**Goal:** Turn the flat `scripts/` prototype into an installable `src/learning_curve` package optimized for deployment (pyproject, console entry points, bundled web assets, env config, Dockerfile), then split oversized modules, add CI + ruff/mypy, and tidy root docs.

**Run tests with:** `venv/Scripts/python.exe -m pytest --basetemp="<scratchpad>/pytest-tmp" -p no:cacheprovider -q`

## Target layout

```
pyproject.toml · Dockerfile · .dockerignore · .github/workflows/ci.yml
src/learning_curve/
  __init__.py · config.py
  security/access.py
  retrieval/  engine.py · bm25.py · vectors.py · embeddings.py · corpus_layout.py · portfolio.py
  assistant/  assistant.py · prompt.py · llm.py · logbook.py
  web/        app.py · runtime.py · workspace.py · documents.py · templates/ · static/
  cli/ask.py
  eval/       run_eval.py · metrics.py · grade_answers.py · gold_set.json
  tools/      build_chunks.py · build_embeddings.py · demo_cases/
tests/  sample-docs/  docs/  logs/
```

## Module → destination map (Phase B is a pure 1:1 move; renames/splits happen in Phase C)

| Current | Phase B destination | Phase C final |
|---|---|---|
| `scripts/access.py` | `security/access.py` | — |
| `scripts/search_chunks.py` | `retrieval/search_chunks.py` | split → `engine.py`+`bm25.py`+`vectors.py` |
| `scripts/embeddings.py` | `retrieval/embeddings.py` | — |
| `scripts/corpus_layout.py` | `retrieval/corpus_layout.py` | — |
| `scripts/case_portfolio.py` | `retrieval/portfolio.py` | — |
| `scripts/assistant.py` | `assistant/assistant.py` | — |
| `scripts/prompt.py` | `assistant/prompt.py` | — |
| `scripts/llm.py` | `assistant/llm.py` | — |
| `scripts/logbook.py` | `assistant/logbook.py` | — |
| `scripts/app_runtime.py` | `web/runtime.py` | split workspace-meta → `web/workspace.py` |
| `scripts/webapp.py` | `web/app.py` | — |
| `scripts/documents.py` | `web/documents.py` | — |
| `scripts/ask.py` | `cli/ask.py` | — |
| `scripts/build_sample_chunks.py` | `tools/build_chunks.py` | — |
| `scripts/build_embeddings.py` | `tools/build_embeddings.py` | — |
| `scripts/generate_demo_cases.py` | `tools/generate_demo_cases.py` | split → `tools/demo_cases/` |
| `eval/*` | `eval/*` (into package) | — |
| `templates/`, `static/` | `web/templates/`, `web/static/` | — |

## Import rewrite rule (Phase B)

Bare `from <mod> import X` / `import <mod>` → absolute `from learning_curve.<subpkg>.<mod> import X`. Each subpackage `__init__.py` re-exports the public names so consumers can use the short form `from learning_curve.retrieval import ChunkSearchEngine, VectorIndex, build_preview`.

## Phases (each ends green)

- **Phase A — Skeleton + pyproject:** create `src/learning_curve/**/__init__.py`, `pyproject.toml` (PEP 621: deps from requirements.txt, `[project.scripts]` entry points, ruff+mypy config, `[tool.setuptools] package-dir=src`, include web assets as package-data). `pip install -e .`. Suite still green via *old* layout (nothing moved yet).
- **Phase B — Move 1:1 + rewrite imports:** move every module per the map; rewrite imports to absolute; move `templates/`+`static/` into `web/`; switch `web/app.py` to locate assets via `importlib.resources`; update `pytest.ini` (drop `pythonpath = . scripts`; rely on editable install); update every test import; move `eval/` into the package. **Checkpoint: full suite green.**
- **Phase C — Split oversized modules:** `retrieval/search_chunks.py`→`engine.py`+`bm25.py`+`vectors.py` (re-export from `retrieval/__init__`); `web/runtime.py`→ + `web/workspace.py`; `tools/generate_demo_cases.py`→`tools/demo_cases/` package. **Checkpoint after each split: suite green.**
- **Phase D — Deployment:** `config.py` (env settings: `LC_CORPUS_DIR`, `AWS_REGION`, `BEDROCK_MODEL`, `LC_HOST/LC_PORT`); wire `web/app.py` + `web/runtime.py` to read defaults from `config`. `Dockerfile` (slim base, `pip install .`, pre-pull MiniLM, `CMD ["learning-curve-web"]`) + `.dockerignore`. **Checkpoint: `learning-curve-web` boots; suite green.**
- **Phase E — Tooling + CI + docs:** ruff + mypy config already in pyproject — run `ruff check --fix` and fix; `requirements-dev` pinned; `.github/workflows/ci.yml` (install → ruff → pytest); move `plan.md`, `phase1-scope-note.md`, `Ticket`, the standalone HTML into `docs/`; refresh `CLAUDE.md` + `README.md` for the new layout. **Checkpoint: suite + ruff green.**
- **Phase F — Verify + finish:** full suite green; live smoke (`learning-curve-web` serves `/`, `/ask`, `/documents`, `/threads`); finish branch for user review/merge.

## Entry points (`[project.scripts]`)

```
learning-curve-web = "learning_curve.web.app:main"
learning-curve-ask = "learning_curve.cli.ask:main"
learning-curve-eval = "learning_curve.eval.run_eval:main"
lc-build-chunks = "learning_curve.tools.build_chunks:main"
lc-build-embeddings = "learning_curve.tools.build_embeddings:main"
lc-generate-cases = "learning_curve.tools.generate_demo_cases:main"
```

## Risks & mitigations

- **Asset paths break when installed** → locate `templates/`/`static/` via `importlib.resources.files("learning_curve.web")`; include as package-data.
- **Default corpus path** (`DEFAULT_CORPUS_DIR`) currently `__file__/../../sample-docs` → keep a repo-relative default for dev but allow `LC_CORPUS_DIR` override for deploy (`config.py`).
- **Test temp-dir WinError 5** (pre-existing sandbox quirk) → run with `--basetemp` in the scratchpad.
- **Big move breaks many imports at once** → Phase B is one focused step; if red, the baseline commit restores instantly.
