# Access Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the system a caller identity (matter + role) and enforce **deny-by-default** access *inside* the retrieval path, so unauthorized chunks can never be scored, ranked, returned, or fed to a model.

**Architecture:** Add a small `Principal` identity object and a `can_access(chunk, principal)` check in a new `scripts/access.py`. Modify `ChunkSearchEngine.search` to require a `Principal` and skip any chunk the principal cannot access *before* scoring. Thread an authorized pilot principal through the evaluation harness, and add a regression test proving a cross-matter caller gets zero results. This is the local stand-in for the ticket's "matter-level permissions + ethical walls"; in production the same `Principal` would be built from a Microsoft Entra token instead of CLI flags.

**Tech Stack:** Python 3.12 standard library (`dataclasses`). No new dependencies.

## Global Constraints

- Python: 3.12.5; run through `venv\Scripts\python.exe`.
- **Deny-by-default**: a chunk with a missing or malformed `access_scope` is NOT accessible to anyone.
- Enforcement happens in `ChunkSearchEngine.search`, not in a wrapper — there must be no code path that returns chunks without an access check.
- Each chunk's `access_scope` has the shape `{"matter_id": str, "allowed_roles": [str, ...]}` (verified in `sample-docs/chunks.json` / `sample-docs/metadata.json`). Real roles in the corpus: `pilot_user`, `pilot_reviewer`, `pilot_admin`. Real matter: `acme-v-northridge`.
- This plan **modifies files created in [plans/01-evaluation-harness.md](01-evaluation-harness.md)** (`eval/run_eval.py`, `tests/test_run_eval.py`). Do plan 01 first.

---

### Task 1: Principal identity + access check

**Files:**
- Create: `scripts/access.py`
- Test: `tests/test_access.py`

**Interfaces:**
- Produces:
  - `Principal` — a frozen dataclass: `user_id: str`, `role: str`, `matter_ids: frozenset[str]`.
  - `can_access(chunk: dict, principal: Principal) -> bool` — `True` iff the chunk's `access_scope.matter_id` is in `principal.matter_ids` AND `principal.role` is in the chunk's `access_scope.allowed_roles`. Deny-by-default on any missing/malformed scope.
  - `pilot_principal(role: str = "pilot_user", matter_id: str = "acme-v-northridge") -> Principal` — convenience builder for local use and the harness.

- [ ] **Step 1: Write the failing test**

`tests/test_access.py`:
```python
from access import Principal, can_access, pilot_principal

AUTHORIZED_CHUNK = {
    "access_scope": {"matter_id": "acme-v-northridge",
                     "allowed_roles": ["pilot_user", "pilot_reviewer", "pilot_admin"]}
}


def test_authorized_user_can_access():
    p = Principal("u1", "pilot_user", frozenset({"acme-v-northridge"}))
    assert can_access(AUTHORIZED_CHUNK, p) is True


def test_wrong_matter_is_denied():
    p = Principal("u2", "pilot_user", frozenset({"some-other-matter"}))
    assert can_access(AUTHORIZED_CHUNK, p) is False


def test_wrong_role_is_denied():
    p = Principal("u3", "outsider", frozenset({"acme-v-northridge"}))
    assert can_access(AUTHORIZED_CHUNK, p) is False


def test_missing_access_scope_is_denied():
    p = Principal("u4", "pilot_user", frozenset({"acme-v-northridge"}))
    assert can_access({}, p) is False
    assert can_access({"access_scope": None}, p) is False
    assert can_access({"access_scope": {"matter_id": "acme-v-northridge"}}, p) is False


def test_pilot_principal_is_authorized_by_default():
    assert can_access(AUTHORIZED_CHUNK, pilot_principal()) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_access.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'access'`

- [ ] **Step 3: Write the implementation**

`scripts/access.py`:
```python
"""Caller identity and deny-by-default access checks for retrieval.

In production a Principal would be constructed from a verified Microsoft Entra
token. Locally it is built from CLI flags or the harness."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    user_id: str
    role: str
    matter_ids: frozenset[str]


def can_access(chunk: dict, principal: Principal) -> bool:
    scope = chunk.get("access_scope")
    if not isinstance(scope, dict):
        return False
    matter_id = scope.get("matter_id")
    allowed_roles = scope.get("allowed_roles")
    if not matter_id or not isinstance(allowed_roles, list):
        return False
    return matter_id in principal.matter_ids and principal.role in allowed_roles


def pilot_principal(role: str = "pilot_user",
                    matter_id: str = "acme-v-northridge") -> Principal:
    return Principal(user_id=f"local-{role}", role=role,
                     matter_ids=frozenset({matter_id}))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_access.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/access.py tests/test_access.py
git commit -m "feat: add Principal identity and deny-by-default access check"
```

---

### Task 2: Enforce access inside search()

**Files:**
- Modify: `scripts/search_chunks.py` (the `search` method at lines 168-181, and `main` at lines 286-303)
- Test: `tests/test_search_access.py`

**Interfaces:**
- Consumes: `Principal`, `can_access` from `scripts/access.py`.
- Produces (changed signature): `ChunkSearchEngine.search(self, query: str, principal: Principal, top_k: int = 5) -> list[dict]`. Any chunk where `can_access(chunk, principal)` is `False` is skipped before scoring. The CLI gains `--role`, `--matter`, `--user`, all defaulting to an authorized pilot identity so the existing README demo command keeps working.

- [ ] **Step 1: Write the failing test**

`tests/test_search_access.py`:
```python
import json
from pathlib import Path

from search_chunks import ChunkSearchEngine
from access import Principal, pilot_principal

ROOT = Path(__file__).resolve().parent.parent
PAYLOAD = json.loads((ROOT / "sample-docs" / "chunks.json").read_text())


def test_authorized_principal_gets_results():
    engine = ChunkSearchEngine(PAYLOAD)
    results = engine.search("What did the witness say about the failed inspection?",
                            pilot_principal(), top_k=5)
    assert len(results) > 0


def test_cross_matter_principal_gets_nothing():
    engine = ChunkSearchEngine(PAYLOAD)
    outsider = Principal("intruder", "pilot_user", frozenset({"some-other-matter"}))
    results = engine.search("What did the witness say about the failed inspection?",
                            outsider, top_k=5)
    assert results == []


def test_wrong_role_gets_nothing():
    engine = ChunkSearchEngine(PAYLOAD)
    outsider = Principal("intruder", "not-a-pilot-role", frozenset({"acme-v-northridge"}))
    results = engine.search("inspection", outsider, top_k=5)
    assert results == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_search_access.py -v`
Expected: FAIL — `search()` does not yet accept a `principal` argument (`TypeError`).

- [ ] **Step 3: Add the import**

In `scripts/search_chunks.py`, just below the existing `from pathlib import Path` (line 5), add:
```python
from access import Principal, can_access
```

- [ ] **Step 4: Replace the `search` method (lines 168-181) with the access-filtered version**

```python
    def search(self, query: str, principal: Principal, top_k: int = 5) -> list[dict]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        results = []
        for stats in self.chunk_stats:
            if not can_access(stats["chunk"], principal):
                continue
            score = self._bm25_score(query_tokens, stats)
            score += self._heuristic_boosts(query, query_tokens, stats)
            if score > 0:
                results.append({"score": score, "chunk": stats["chunk"]})

        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:top_k]
```

- [ ] **Step 5: Update `main()` (lines 286-303) to build a Principal from CLI flags**

Add these arguments alongside the existing ones:
```python
    parser.add_argument("--role", default="pilot_user", help="Caller role.")
    parser.add_argument("--matter", default="acme-v-northridge", help="Caller matter id.")
    parser.add_argument("--user", default="local-cli", help="Caller user id.")
```
Then replace the `results = engine.search(args.query, top_k=args.top_k)` line with:
```python
    principal = Principal(user_id=args.user, role=args.role,
                          matter_ids=frozenset({args.matter}))
    results = engine.search(args.query, principal, top_k=args.top_k)
```

- [ ] **Step 6: Run the access test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_search_access.py -v`
Expected: PASS (3 passed)

- [ ] **Step 7: Verify the README demo still works (authorized default)**

Run: `venv\Scripts\python.exe scripts\search_chunks.py "What did the witness say about the failed inspection?"`
Expected: prints results as before (defaults are an authorized pilot identity).

Run: `venv\Scripts\python.exe scripts\search_chunks.py "inspection" --matter some-other-matter`
Expected: `Results: 0` (cross-matter caller sees nothing).

- [ ] **Step 8: Commit**

```bash
git add scripts/search_chunks.py tests/test_search_access.py
git commit -m "feat: enforce deny-by-default matter/role access inside search()"
```

---

### Task 3: Thread the principal through the eval harness

**Files:**
- Modify: `eval/run_eval.py` (the `evaluate` function and `main`, from plan 01)
- Modify: `tests/test_run_eval.py` (from plan 01 — calls to `evaluate` now need a principal)
- Test: add a case to `tests/test_run_eval.py` proving an unauthorized principal scores zero recall everywhere

**Interfaces:**
- Consumes: `pilot_principal`, `Principal` from `scripts/access.py`.
- Produces (changed signature): `evaluate(engine, gold: dict, k: int, principal: Principal) -> dict`. `main()` builds an authorized `pilot_principal()` by default.

- [ ] **Step 1: Update the existing `evaluate` call sites in the test (make them fail first)**

In `tests/test_run_eval.py`, add this import near the top:
```python
from access import pilot_principal, Principal
```
Change the two existing `evaluate(engine, GOLD, k=5)` calls to:
```python
evaluate(engine, GOLD, k=5, principal=pilot_principal())
```
Then append a new regression test:
```python
def test_unauthorized_principal_scores_zero():
    from search_chunks import ChunkSearchEngine
    engine = ChunkSearchEngine(PAYLOAD)
    outsider = Principal("intruder", "pilot_user", frozenset({"other-matter"}))
    report = evaluate(engine, GOLD, k=5, principal=outsider)
    assert all(row["recall_at_k"] == 0.0 for row in report["rows"])
    assert report["summary"]["pass_rate"] == 0.0 or all(
        not row["passed"] for row in report["rows"] if row["expected"]
    )
```

- [ ] **Step 2: Run to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_run_eval.py -v`
Expected: FAIL — `evaluate()` does not yet accept `principal` (`TypeError`).

- [ ] **Step 3: Update `evaluate` in `eval/run_eval.py`**

Add to the imports block (after the `search_chunks` import):
```python
from access import Principal, pilot_principal  # noqa: E402
```
Change the signature and the search call:
```python
def evaluate(engine: ChunkSearchEngine, gold: dict, k: int, principal: Principal) -> dict:
```
and inside the loop replace `results = engine.search(question["question"], top_k=k)` with:
```python
        results = engine.search(question["question"], principal, top_k=k)
```

- [ ] **Step 4: Update `main()` in `eval/run_eval.py`**

Replace `report = evaluate(engine, gold, k=args.top_k)` with:
```python
    report = evaluate(engine, gold, k=args.top_k, principal=pilot_principal())
```

- [ ] **Step 5: Run the full suite**

Run: `venv\Scripts\python.exe -m pytest -q`
Expected: all tests pass, including `test_unauthorized_principal_scores_zero`.

- [ ] **Step 6: Re-run the harness and confirm authorized recall is unchanged from the baseline**

Run: `venv\Scripts\python.exe -m eval.run_eval --top-k 5`
Expected: the summary line matches `eval/BASELINE.md` (adding access control must NOT change what an authorized pilot user retrieves). If numbers dropped, an authorized chunk is being wrongly denied — fix `can_access`, do not relax the test.

- [ ] **Step 7: Commit**

```bash
git add eval/run_eval.py tests/test_run_eval.py
git commit -m "feat: enforce caller identity in eval harness and add cross-matter regression"
```

---

## Self-Review

- **Spec coverage:** "Retrieves only from approved matter" → cross-matter principal returns `[]` (Task 2 test + Task 3 regression). "Unauthorized users cannot access indexed content" → enforcement is inside `search()` before scoring, deny-by-default. Identity model (`Principal`) maps cleanly to a future Entra token. The harness proves authorized recall is unchanged, so security didn't silently break retrieval.
- **Placeholder scan:** none — all steps show real code and exact line targets.
- **Type consistency:** `Principal` is defined once in `scripts/access.py` and imported everywhere; `search(query, principal, top_k)` and `evaluate(engine, gold, k, principal)` signatures are used consistently across `search_chunks.py`, `run_eval.py`, and all tests.

## Notes / Limits (for the learner)

- This enforces **matter-level** scoping and a coarse **role** check — the achievable part of "ethical walls" with a local synthetic corpus. True per-person walls (user A may never see matter B even within the firm) need per-user identity from Entra and per-document ACLs synced from SharePoint; that is out of scope here and belongs to the real productionization, not the prototype.
- BM25 corpus statistics (idf, average length) are still computed over all chunks, so an authorized user's *scores* are mildly influenced by the existence of other chunks. This does not leak content and is acceptable for the prototype; a production index would scope statistics per matter.

## Execution Handoff

Run task-by-task with **superpowers:subagent-driven-development** or **superpowers:executing-plans**. When done, proceed to [plans/03-retrieval-rebuild.md](03-retrieval-rebuild.md).
