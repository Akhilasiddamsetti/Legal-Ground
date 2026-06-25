# Case Workspace SP2–SP5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the Case Workspace product on top of the shipped SP1 shell + SP3 portfolio backend: open source documents from citations (SP2), persist/replay per-case thread history (SP4), and add appearance settings + a real-ish profile (SP5). SP3 (multi-case) is already functional; only a small status-from-metadata polish remains.

**Architecture:** Thin read-only FastAPI routes over the existing portfolio runtime, plus client-side rendering in the three UI files. New backend logic is isolated in a self-contained `scripts/documents.py` module to avoid churn in the concurrently-edited `app_runtime.py`/`case_portfolio.py`. Settings are client-only (localStorage). Thread history reuses the existing `read_recent_logs`.

**Tech Stack:** FastAPI + Jinja2 (server), vanilla HTML/CSS/JS (client), pytest. AWS Bedrock for live answers (not exercised by tests; `StubLLM`).

## Global Constraints

- Access stays deny-by-default: every new route validates `matter ∈ runtime.allowed_matters` and `role ∈ runtime.allowed_roles` before returning anything, exactly like `/ask`.
- No new third-party dependencies.
- Tests run offline; never call Bedrock (use `StubLLM`; the MiniLM embedder + `embeddings.npz` are already cached).
- Run pytest with a writable temp dir on this sandbox: `--basetemp="<scratchpad>/pytest-tmp" -p no:cacheprovider`.
- Ownership: this plan's code lives in files the assistant owns — `scripts/documents.py` (new), the three UI files, and **additive** routes in `scripts/webapp.py`. It does **not** modify `app_runtime.py`, `case_portfolio.py`, or `corpus_layout.py`.
- File references use exact paths; markdown source files live at `<case_root>/<filename>.md` per each case's `_meta/metadata.json` `source_path`.

---

## Current state (already shipped)

- SP1: Case Workspace shell (`templates/index.html`, `static/app.css`, `static/app.js`) wired to `/ask`.
- SP3: portfolio backend (`case_portfolio.py`, `generate_demo_cases.py`), 6 cases × 16 docs, `all_cases` runtime, `matter-select` + cards + search. Full suite green (58 tests).

---

## Task 1: SP2 — `documents.py` source loader (backend)

**Files:**
- Create: `scripts/documents.py`
- Test: `tests/test_documents.py`

**Interfaces:**
- Produces: `load_document_source(matter_id: str, doc_id: str, portfolio_root: Path = DEFAULT_CORPUS_DIR) -> dict` returning `{"matter_id","doc_id","title","type","date","citation_label","text"}`; raises `KeyError` if the matter or doc is unknown. `list_case_documents(matter_id, portfolio_root) -> list[dict]` returning the same dicts minus `text`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_documents.py
from pathlib import Path
import pytest
from documents import load_document_source

ROOT = Path(__file__).resolve().parent.parent

def test_loads_source_text_for_a_known_document():
    doc = load_document_source("acme-v-northridge", "exhibit-12-inspection-report", ROOT / "sample-docs")
    assert doc["title"] == "Exhibit 12 Inspection Report"
    assert doc["matter_id"] == "acme-v-northridge"
    assert len(doc["text"]) > 50          # real markdown body
    assert "inspection" in doc["text"].lower()

def test_unknown_document_raises_keyerror():
    with pytest.raises(KeyError):
        load_document_source("acme-v-northridge", "no-such-doc", ROOT / "sample-docs")
```

- [ ] **Step 2: Run to verify it fails** — `pytest tests/test_documents.py -v` → FAIL (`No module named 'documents'`).

- [ ] **Step 3: Implement `scripts/documents.py`**

```python
from __future__ import annotations
from pathlib import Path
from corpus_layout import case_metadata_path
from case_portfolio import discover_case_roots
import json

DEFAULT_CORPUS_DIR = Path(__file__).resolve().parent.parent / "sample-docs"

def _case_root_for(matter_id, portfolio_root):
    for root in discover_case_roots(Path(portfolio_root)):
        meta = json.loads(case_metadata_path(root).read_text(encoding="utf-8"))
        if meta.get("matter_id") == matter_id:
            return root, meta
    # single-case / flat fallback
    meta = json.loads(case_metadata_path(portfolio_root).read_text(encoding="utf-8"))
    if meta.get("matter_id") == matter_id:
        return Path(portfolio_root), meta
    raise KeyError(matter_id)

def _doc_record(doc):
    return {
        "doc_id": doc.get("doc_id"),
        "title": doc.get("title") or doc.get("doc_id"),
        "type": (doc.get("doc_type", "") or "Document").replace("_", " ").title(),
        "date": doc.get("created_date", ""),
        "citation_label": doc.get("citation_label") or doc.get("title") or "",
    }

def list_case_documents(matter_id, portfolio_root=DEFAULT_CORPUS_DIR):
    _, meta = _case_root_for(matter_id, portfolio_root)
    return [{**_doc_record(d), "matter_id": matter_id} for d in meta.get("documents", [])]

def load_document_source(matter_id, doc_id, portfolio_root=DEFAULT_CORPUS_DIR):
    root, meta = _case_root_for(matter_id, portfolio_root)
    doc = next((d for d in meta.get("documents", []) if d.get("doc_id") == doc_id), None)
    if doc is None:
        raise KeyError(doc_id)
    filename = doc.get("filename") or (doc.get("source_path", "").split("/")[-1])
    text = (root / filename).read_text(encoding="utf-8")
    return {**_doc_record(doc), "matter_id": matter_id, "text": text}
```

- [ ] **Step 4: Run to verify it passes** — `pytest tests/test_documents.py -v` → PASS.

- [ ] **Step 5: Commit** — `feat(sp2): add documents source loader`

---

## Task 2: SP2 — `GET /documents/{matter}/{doc_id}` route (backend)

**Files:**
- Modify: `scripts/webapp.py` (add route + import; additive only)
- Test: `tests/test_webapp_documents.py`

**Interfaces:**
- Consumes: `documents.load_document_source`.
- Produces: `GET /documents/{matter}/{doc_id}?role=<role>` → 200 `{title,type,date,citation_label,text,matter_id,doc_id}`; 400 unknown matter/role; 404 unknown doc.

- [ ] **Step 1: Failing test**

```python
# tests/test_webapp_documents.py
from pathlib import Path
from fastapi.testclient import TestClient
from app_runtime import build_runtime_from_llm
from llm import StubLLM
from webapp import create_app
ROOT = Path(__file__).resolve().parent.parent

def _client(tmp_path):
    rt = build_runtime_from_llm(StubLLM(lambda s,u:"ok"), corpus_dir=ROOT/"sample-docs", all_cases=True, log_dir=tmp_path)
    return TestClient(create_app(rt))

def test_open_document_source(tmp_path):
    r = _client(tmp_path).get("/documents/acme-v-northridge/exhibit-12-inspection-report?role=pilot_user")
    assert r.status_code == 200
    assert "inspection" in r.json()["text"].lower()

def test_open_document_rejects_unknown_role(tmp_path):
    r = _client(tmp_path).get("/documents/acme-v-northridge/exhibit-12-inspection-report?role=outsider")
    assert r.status_code == 400
```

- [ ] **Step 2: Verify fail** — 404 (route missing).
- [ ] **Step 3: Implement** — in `create_app`, after `/ask`:

```python
from fastapi import Query
import documents as documents_mod

@app.get("/documents/{matter}/{doc_id}")
def open_document(matter: str, doc_id: str, role: str = Query(...)):
    if matter not in runtime.allowed_matters:
        raise HTTPException(400, f"Unknown matter: {matter}")
    if role not in runtime.allowed_roles:
        raise HTTPException(400, f"Unknown role: {role}")
    try:
        return documents_mod.load_document_source(matter, doc_id)
    except KeyError:
        raise HTTPException(404, f"Unknown document: {doc_id}")
```

- [ ] **Step 4: Verify pass.**
- [ ] **Step 5: Commit** — `feat(sp2): add /documents route`

---

## Task 3: SP2 — source viewer in the UI (frontend)

**Files:** Modify `templates/index.html` (corpus items become buttons + a source-view container in the drawer), `static/app.js` (fetch + render source), `static/app.css` (source styles).

- [ ] **Step 1 (test via index assertion):** add to `tests/` is owned by the user; instead verify by live smoke. Make corpus items `<button class="corpus-item" data-doc-id="{{ doc.doc_id }}">`.
- [ ] **Step 2:** In `app.js`, on corpus-item click and on citation "open source", `fetch('/documents/'+matter+'/'+docId+'?role='+role)`, then render `{title, date, type}` + `<pre>`-style text into a drawer "Source" panel; a back control returns to passages.
- [ ] **Step 3:** Style `.source-view` (serif body, mono meta) in `app.css`.
- [ ] **Step 4:** Live smoke: open drawer → click a corpus doc → source text shows.
- [ ] **Step 5: Commit** — `feat(sp2): open source documents from the corpus/citations`

---

## Task 4: SP4 — `GET /threads/{matter}` history route (backend)

**Files:** Modify `scripts/webapp.py` (additive route), Test `tests/test_webapp_threads.py`.

**Interfaces:** Produces `GET /threads/{matter}?role=&limit=` → `{turns:[{question,answer,abstained,citations,timestamp}]}` from `read_recent_logs`.

- [ ] **Step 1: Failing test** — post an `/ask`, then `GET /threads/<matter>?role=pilot_user` returns ≥1 turn whose `question` matches.
- [ ] **Step 2: Verify fail.**
- [ ] **Step 3: Implement** using existing `read_recent_logs(runtime.log_dir, matter, limit)`; validate matter/role first; map rows → turns.
- [ ] **Step 4: Verify pass.**
- [ ] **Step 5: Commit** — `feat(sp4): add /threads history route`

---

## Task 5: SP4 — load thread history on case select (frontend)

**Files:** Modify `static/app.js`.

- [ ] **Step 1:** Add `loadThread(matter)` → `fetch('/threads/'+matter+'?role='+role+'&limit=20')`, clear transcript, render each prior turn read-only (reuse `fillTurn`-style rendering with a "history" marker, no evidence drawer payload beyond what's logged).
- [ ] **Step 2:** Call `loadThread` in `setActiveMatter` (and on first load). Keep the empty-state when no history.
- [ ] **Step 3:** Live smoke: ask a question, reload page → the prior turn reappears for that case; switch case → its own history loads.
- [ ] **Step 4: Commit** — `feat(sp4): replay per-case thread history`

---

## Task 6: SP5 — appearance settings + profile (frontend-only)

**Files:** Modify `templates/index.html` (settings menu trigger in sidebar foot/header), `static/app.js` (localStorage settings), `static/app.css` (menu + density/answer-style variants).

**Settings (persisted in `localStorage` under `lc-settings`):** `palette` (Indigo default + navy/graphite/oxblood/teal → sets `body[data-theme]`), `answerStyle` (Serif memo / Clean sans → toggles `.ans` font), `density` (Detailed/Compact → sidebar class), `showRelevance` (boolean; reserved — no scores yet, hides the relevance placeholder).

- [ ] **Step 1:** Add a settings control (gear) opening a small menu with the four options.
- [ ] **Step 2:** `applySettings()` reads/writes localStorage and toggles `body[data-theme]` / `.answer-clean` / `.sidebar.compact`. Apply on load.
- [ ] **Step 3:** `app.css`: define the `answerStyle`/`density` variants (themes already exist).
- [ ] **Step 4:** Live smoke: switch palette → colors change and persist across reload.
- [ ] **Step 5: Commit** — `feat(sp5): appearance settings (palette/answer-style/density)`

---

## Task 7: SP3 polish — optional case status from metadata (frontend-tolerant)

**Files:** Modify `static/app.js`/`templates/index.html` only — read an optional `data-status` already emitted; if a case's status is "Closed"/"Pinned" (when backend later adds it) the card routes to the right section. No backend change now; the cards already render under "Active". This task is a no-op placeholder confirming the sections render and is closed once SP3 statuses exist in data.

- [ ] **Step 1:** Confirm Pinned/Closed sections render empty and Active lists all cases (already true). Mark SP3 complete.

---

## Verification (whole plan)

- [ ] Full suite green: `pytest --basetemp=<scratchpad>/pytest-tmp -p no:cacheprovider -q`
- [ ] Live smoke (portfolio mode): boot `webapp.py --aws-region us-east-1 --port 80NN`; verify `/documents/...` 200, `/threads/...` 200, source viewer + history + settings work in `GET /`.

## Self-review notes

- Spec coverage: SP2 (Tasks 1–3), SP4 (Tasks 4–5), SP5 (Task 6), SP3 (Task 7 + already shipped). ✓
- No edits to `app_runtime.py`/`case_portfolio.py` (collision-safe). ✓
- New tests live in their own files (`test_documents.py`, `test_webapp_documents.py`, `test_webapp_threads.py`) to avoid clobbering the user's `test_webapp.py`. ✓
