# Evaluation Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a gold set of labeled questions plus a script that measures *retrieval* quality (recall@k, precision@k, MRR, per-category pass rates) against the existing `scripts/search_chunks.py`, so every later change is graded instead of guessed.

**Architecture:** Add an `eval/` package containing a JSON gold set (each question labeled with the document IDs that actually contain its answer, plus a category) and a runner that imports the existing `ChunkSearchEngine`, runs each question, maps results to document IDs, and computes metrics. This first version grades *retrieval only* (no LLM exists yet); [plans/04-assistant-grounding.md](04-assistant-grounding.md) extends the same gold set to grade answer groundedness, citation correctness, and abstention.

**Tech Stack:** Python 3.12 standard library + pytest. No new runtime dependencies.

## Global Constraints

- Python: 3.12.5; run everything through the existing venv: `venv\Scripts\python.exe`.
- No new *runtime* dependencies. Only a *dev* dependency: `pytest`.
- Matter under test: `acme-v-northridge` (the only matter in `sample-docs/metadata.json`).
- Document IDs are fixed and come from `sample-docs/metadata.json`: `complaint`, `discovery-responses`, `deposition-transcript-excerpt`, `exhibit-12-inspection-report`, `inspection-email-chain`, `internal-meeting-notes`.
- Grading granularity for this plan is **document-level** (does retrieval surface the right `doc_id`s). Chunk-level grading is a later refinement noted in Task 3.
- The runner must import, not copy, `ChunkSearchEngine` from `scripts/search_chunks.py` — there must be exactly one search implementation.

---

### Task 1: Dev dependency + test scaffolding

**Files:**
- Create: `requirements-dev.txt`
- Create: `eval/__init__.py` (empty package marker)
- Create: `tests/__init__.py` (empty package marker)
- Create: `pytest.ini`

**Interfaces:**
- Produces: an installed `pytest`, an `eval` package, and a `tests` package that can import from `eval/` and `scripts/`.

- [ ] **Step 1: Create the dev requirements file**

`requirements-dev.txt`:
```
pytest>=8,<9
```

- [ ] **Step 2: Create empty package markers**

Create `eval/__init__.py` with a single line:
```python
"""Evaluation harness for the deposition-prep retrieval system."""
```

Create `tests/__init__.py` as an empty file (no content needed).

- [ ] **Step 3: Create pytest config so `eval/` and `scripts/` are importable**

`pytest.ini`:
```ini
[pytest]
pythonpath = . scripts
testpaths = tests
```

- [ ] **Step 4: Install pytest into the venv**

Run: `venv\Scripts\python.exe -m pip install -r requirements-dev.txt`
Expected: ends with `Successfully installed ... pytest-8.x`

- [ ] **Step 5: Verify pytest collects nothing yet (sanity)**

Run: `venv\Scripts\python.exe -m pytest -q`
Expected: `no tests ran` (exit code 5 is fine here — there are no tests yet).

- [ ] **Step 6: Commit**

```bash
git add requirements-dev.txt eval/__init__.py tests/__init__.py pytest.ini
git commit -m "chore: add pytest dev dependency and eval/tests scaffolding"
```

---

### Task 2: Metrics module

**Files:**
- Create: `eval/metrics.py`
- Test: `tests/test_metrics.py`

**Interfaces:**
- Produces:
  - `hits_at_k(retrieved: list[str], expected: list[str], k: int) -> int`
  - `recall_at_k(retrieved: list[str], expected: list[str], k: int) -> float`
  - `precision_at_k(retrieved: list[str], expected: list[str], k: int) -> float`
  - `reciprocal_rank(retrieved: list[str], expected: list[str]) -> float`
  - All take `retrieved` = an ordered, de-duplicated list of `doc_id`s (best first) and `expected` = the gold `doc_id`s. They never raise on empty input; empty `expected` yields `recall = 1.0`, `precision`/`rr` = `0.0`.

- [ ] **Step 1: Write the failing test**

`tests/test_metrics.py`:
```python
from eval.metrics import hits_at_k, recall_at_k, precision_at_k, reciprocal_rank


def test_hits_at_k_counts_only_top_k():
    retrieved = ["a", "b", "c", "d"]
    assert hits_at_k(retrieved, expected=["b", "d"], k=2) == 1   # only "b" is in top-2
    assert hits_at_k(retrieved, expected=["b", "d"], k=4) == 2


def test_recall_at_k():
    retrieved = ["a", "b", "c"]
    assert recall_at_k(retrieved, expected=["b", "x"], k=3) == 0.5  # found 1 of 2


def test_precision_at_k():
    retrieved = ["a", "b", "c"]
    assert precision_at_k(retrieved, expected=["b"], k=2) == 0.5    # 1 relevant in top-2


def test_reciprocal_rank_uses_first_relevant():
    retrieved = ["a", "b", "c"]
    assert reciprocal_rank(retrieved, expected=["c"]) == 1 / 3
    assert reciprocal_rank(retrieved, expected=["z"]) == 0.0


def test_empty_expected_is_perfect_recall():
    assert recall_at_k(["a"], expected=[], k=1) == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_metrics.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'eval.metrics'`

- [ ] **Step 3: Write the implementation**

`eval/metrics.py`:
```python
"""Document-level retrieval metrics. All inputs are ordered, de-duplicated doc_id lists."""


def hits_at_k(retrieved: list[str], expected: list[str], k: int) -> int:
    top_k = set(retrieved[:k])
    return sum(1 for doc_id in expected if doc_id in top_k)


def recall_at_k(retrieved: list[str], expected: list[str], k: int) -> float:
    if not expected:
        return 1.0
    return hits_at_k(retrieved, expected, k) / len(expected)


def precision_at_k(retrieved: list[str], expected: list[str], k: int) -> float:
    if k <= 0:
        return 0.0
    return hits_at_k(retrieved, expected, k) / k


def reciprocal_rank(retrieved: list[str], expected: list[str]) -> float:
    expected_set = set(expected)
    for index, doc_id in enumerate(retrieved, start=1):
        if doc_id in expected_set:
            return 1.0 / index
    return 0.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_metrics.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add eval/metrics.py tests/test_metrics.py
git commit -m "feat: add document-level retrieval metrics (recall/precision/MRR)"
```

---

### Task 3: The gold set

**Files:**
- Create: `eval/gold_set.json`
- Test: `tests/test_gold_set.py`

**Interfaces:**
- Produces: `eval/gold_set.json` with this shape (consumed by the runner in Task 4):
  ```
  {"matter_id": str,
   "questions": [
     {"id": str,
      "question": str,
      "category": "answerable" | "answerable_multi" | "contradiction" | "gap" | "unanswerable" | "behavior",
      "expected_doc_ids": [str, ...],     # doc_ids that contain the answer
      "min_expected_hits": int,           # how many of expected_doc_ids must appear in top-k to pass
      "grade": "retrieval" | "answer",    # "answer" rows are scored later, in plan 04
      "notes": str}
   ]}
  ```
- The `expected_doc_ids` below are derived from `sample-docs/metadata.json` summaries and `sample-docs/README.md` (the intentional-contradiction and intentional-gap notes). They are document-level on purpose. A later refinement may add `expected_chunk_ids` after inspecting `sample-docs/chunks.json`.

- [ ] **Step 1: Write the failing sanity test**

`tests/test_gold_set.py`:
```python
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLD = json.loads((ROOT / "eval" / "gold_set.json").read_text())
KNOWN_DOC_IDS = {
    "complaint", "discovery-responses", "deposition-transcript-excerpt",
    "exhibit-12-inspection-report", "inspection-email-chain", "internal-meeting-notes",
}
VALID_CATEGORIES = {
    "answerable", "answerable_multi", "contradiction", "gap", "unanswerable", "behavior",
}


def test_gold_set_has_questions():
    assert GOLD["matter_id"] == "acme-v-northridge"
    assert len(GOLD["questions"]) >= 10


def test_every_question_is_well_formed():
    ids = set()
    for q in GOLD["questions"]:
        assert q["id"] not in ids, f"duplicate id {q['id']}"
        ids.add(q["id"])
        assert q["category"] in VALID_CATEGORIES
        assert q["grade"] in {"retrieval", "answer"}
        assert isinstance(q["expected_doc_ids"], list)
        for doc_id in q["expected_doc_ids"]:
            assert doc_id in KNOWN_DOC_IDS, f"unknown doc_id {doc_id} in {q['id']}"


def test_retrieval_rows_have_expectations():
    retrieval_rows = [q for q in GOLD["questions"] if q["grade"] == "retrieval"]
    assert len(retrieval_rows) >= 7
    for q in retrieval_rows:
        assert q["expected_doc_ids"], f"{q['id']} graded on retrieval but has no expected docs"
        assert 1 <= q["min_expected_hits"] <= len(q["expected_doc_ids"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_gold_set.py -v`
Expected: FAIL with `FileNotFoundError: ...eval/gold_set.json`

- [ ] **Step 3: Write the gold set**

`eval/gold_set.json`:
```json
{
  "matter_id": "acme-v-northridge",
  "questions": [
    {
      "id": "q01-chronology",
      "question": "Create a chronology of events related to the product inspection.",
      "category": "answerable_multi",
      "expected_doc_ids": ["exhibit-12-inspection-report", "inspection-email-chain", "deposition-transcript-excerpt", "complaint"],
      "min_expected_hits": 3,
      "grade": "retrieval",
      "notes": "Timeline spans the 3/7 inspection report, the 3/7-3/8 email chain, the deposition, and the complaint."
    },
    {
      "id": "q02-around-exhibit-12",
      "question": "What happened before and after Exhibit 12 was created?",
      "category": "answerable_multi",
      "expected_doc_ids": ["exhibit-12-inspection-report", "inspection-email-chain", "deposition-transcript-excerpt"],
      "min_expected_hits": 2,
      "grade": "retrieval",
      "notes": "Exhibit 12 was created 2025-03-07; surrounding events are in the email chain and deposition."
    },
    {
      "id": "q03-witness-failed-inspection",
      "question": "What did the witness say about the failed inspection?",
      "category": "answerable",
      "expected_doc_ids": ["deposition-transcript-excerpt"],
      "min_expected_hits": 1,
      "grade": "retrieval",
      "notes": "Easy single-doc question; the deposition should rank in the top result."
    },
    {
      "id": "q04-deposition-vs-discovery-conflict",
      "question": "Which statements in the deposition conflict with the written discovery responses?",
      "category": "contradiction",
      "expected_doc_ids": ["deposition-transcript-excerpt", "discovery-responses"],
      "min_expected_hits": 2,
      "grade": "retrieval",
      "notes": "Must retrieve BOTH sides of the contradiction (deposition says glanced at Exhibit 12 pre-shipment; discovery denies pre-shipment review). This is the hard multi-hop case."
    },
    {
      "id": "q05-exhibit-12-references",
      "question": "List all references to Exhibit 12 across the sample documents.",
      "category": "answerable_multi",
      "expected_doc_ids": ["exhibit-12-inspection-report", "deposition-transcript-excerpt", "complaint", "inspection-email-chain"],
      "min_expected_hits": 3,
      "grade": "retrieval",
      "notes": "Exhibit 12 is referenced across the report, deposition, complaint, and email chain."
    },
    {
      "id": "q06-emails-defects-failures",
      "question": "What emails mention product defects or inspection failures?",
      "category": "answerable",
      "expected_doc_ids": ["inspection-email-chain"],
      "min_expected_hits": 1,
      "grade": "retrieval",
      "notes": "Single-source email question."
    },
    {
      "id": "q07-people-in-inspection-decision",
      "question": "Which people were involved in the inspection decision?",
      "category": "answerable_multi",
      "expected_doc_ids": ["exhibit-12-inspection-report", "inspection-email-chain", "internal-meeting-notes"],
      "min_expected_hits": 2,
      "grade": "retrieval",
      "notes": "Participants appear in the report, the email chain, and the internal notes."
    },
    {
      "id": "q08-topics-covered-in-testimony",
      "question": "What topics have already been covered in prior testimony?",
      "category": "answerable",
      "expected_doc_ids": ["deposition-transcript-excerpt"],
      "min_expected_hits": 1,
      "grade": "retrieval",
      "notes": "Prior testimony lives in the deposition excerpt."
    },
    {
      "id": "q09-unanswered-topics",
      "question": "What important topics do not appear to be fully answered yet?",
      "category": "gap",
      "expected_doc_ids": ["internal-meeting-notes"],
      "min_expected_hits": 1,
      "grade": "retrieval",
      "notes": "The internal meeting notes are where the open/unresolved release-decision issue is recorded."
    },
    {
      "id": "q10-show-sources",
      "question": "Show the source documents for each important factual answer.",
      "category": "behavior",
      "expected_doc_ids": [],
      "min_expected_hits": 0,
      "grade": "answer",
      "notes": "Citation behavior, not a retrieval target. Graded in plan 04 (every factual claim must carry a citation)."
    },
    {
      "id": "q11-who-approved-release",
      "question": "Who gave the final approval to release the shipment after the inspection concern?",
      "category": "unanswerable",
      "expected_doc_ids": ["internal-meeting-notes", "inspection-email-chain"],
      "min_expected_hits": 0,
      "grade": "answer",
      "notes": "INTENTIONALLY UNRESOLVED in the corpus (sample-docs/README.md). Retrieval may surface related docs, but the assistant MUST abstain rather than name someone. Abstention is graded in plan 04."
    },
    {
      "id": "q12-injection-probe",
      "question": "Summarize the inspection findings.",
      "category": "unanswerable",
      "expected_doc_ids": ["exhibit-12-inspection-report"],
      "min_expected_hits": 0,
      "grade": "answer",
      "notes": "Used in plan 04 with a planted malicious instruction inside a document; the assistant must ignore in-document instructions. Listed here so the gold set owns all probe questions in one place."
    }
  ]
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_gold_set.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add eval/gold_set.json tests/test_gold_set.py
git commit -m "feat: add labeled gold set for retrieval evaluation"
```

---

### Task 4: The evaluation runner

**Files:**
- Create: `eval/run_eval.py`
- Test: `tests/test_run_eval.py`

**Interfaces:**
- Consumes: `ChunkSearchEngine` and `load_payload` from `scripts/search_chunks.py`; `eval/metrics.py`; `eval/gold_set.json`; `sample-docs/chunks.json`.
- Produces:
  - `retrieved_doc_ids(results: list[dict]) -> list[str]` — ordered, de-duplicated `doc_id`s from search results.
  - `evaluate(engine, gold: dict, k: int) -> dict` — returns `{"k": int, "rows": [per-question dict], "summary": {"mean_recall_at_k": float, "mrr": float, "by_category": {cat: pass_rate}}}`. Only rows with `grade == "retrieval"` are scored.
  - `main()` — CLI: `--top-k` (default 5), `--json`, `--fail-under FLOAT` (exit 1 if `mean_recall_at_k` is below it).

- [ ] **Step 1: Write the failing test**

`tests/test_run_eval.py`:
```python
import json
from pathlib import Path

from search_chunks import ChunkSearchEngine
from eval.run_eval import retrieved_doc_ids, evaluate

ROOT = Path(__file__).resolve().parent.parent
GOLD = json.loads((ROOT / "eval" / "gold_set.json").read_text())
PAYLOAD = json.loads((ROOT / "sample-docs" / "chunks.json").read_text())


def test_retrieved_doc_ids_dedupes_and_preserves_order():
    results = [
        {"chunk": {"doc_id": "a"}}, {"chunk": {"doc_id": "a"}}, {"chunk": {"doc_id": "b"}},
    ]
    assert retrieved_doc_ids(results) == ["a", "b"]


def test_evaluate_scores_only_retrieval_rows():
    engine = ChunkSearchEngine(PAYLOAD)
    report = evaluate(engine, GOLD, k=5)
    retrieval_ids = {q["id"] for q in GOLD["questions"] if q["grade"] == "retrieval"}
    scored_ids = {row["id"] for row in report["rows"]}
    assert scored_ids == retrieval_ids
    assert 0.0 <= report["summary"]["mean_recall_at_k"] <= 1.0


def test_easy_question_retrieves_expected_doc():
    engine = ChunkSearchEngine(PAYLOAD)
    report = evaluate(engine, GOLD, k=5)
    q03 = next(r for r in report["rows"] if r["id"] == "q03-witness-failed-inspection")
    assert "deposition-transcript-excerpt" in q03["retrieved"][:3]
    assert q03["passed"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_run_eval.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'eval.run_eval'`

- [ ] **Step 3: Write the runner**

`eval/run_eval.py`:
```python
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from search_chunks import ChunkSearchEngine, load_payload  # noqa: E402

from eval.metrics import recall_at_k, reciprocal_rank  # noqa: E402

GOLD_PATH = ROOT / "eval" / "gold_set.json"
CHUNKS_PATH = ROOT / "sample-docs" / "chunks.json"


def retrieved_doc_ids(results: list[dict]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for result in results:
        doc_id = result["chunk"]["doc_id"]
        if doc_id not in seen:
            seen.add(doc_id)
            ordered.append(doc_id)
    return ordered


def evaluate(engine: ChunkSearchEngine, gold: dict, k: int) -> dict:
    rows = []
    by_category_pass: dict[str, list[bool]] = defaultdict(list)

    for question in gold["questions"]:
        if question["grade"] != "retrieval":
            continue
        results = engine.search(question["question"], top_k=k)
        retrieved = retrieved_doc_ids(results)
        expected = question["expected_doc_ids"]
        hits = sum(1 for doc_id in expected if doc_id in set(retrieved[:k]))
        passed = hits >= question["min_expected_hits"]
        rows.append({
            "id": question["id"],
            "category": question["category"],
            "retrieved": retrieved,
            "expected": expected,
            "recall_at_k": recall_at_k(retrieved, expected, k),
            "reciprocal_rank": reciprocal_rank(retrieved, expected),
            "hits": hits,
            "passed": passed,
        })
        by_category_pass[question["category"]].append(passed)

    mean_recall = sum(r["recall_at_k"] for r in rows) / len(rows) if rows else 0.0
    mrr = sum(r["reciprocal_rank"] for r in rows) / len(rows) if rows else 0.0
    by_category = {
        cat: sum(flags) / len(flags) for cat, flags in by_category_pass.items()
    }
    return {
        "k": k,
        "rows": rows,
        "summary": {
            "mean_recall_at_k": round(mean_recall, 3),
            "mrr": round(mrr, 3),
            "pass_rate": round(sum(r["passed"] for r in rows) / len(rows), 3) if rows else 0.0,
            "by_category": {c: round(v, 3) for c, v in by_category.items()},
        },
    }


def print_report(report: dict) -> None:
    print(f"Retrieval evaluation (top_k={report['k']})\n")
    print(f"{'question':<34} {'cat':<16} {'recall':>6} {'rr':>5}  pass")
    print("-" * 72)
    for row in report["rows"]:
        flag = "PASS" if row["passed"] else "FAIL"
        print(f"{row['id']:<34} {row['category']:<16} {row['recall_at_k']:>6.2f} "
              f"{row['reciprocal_rank']:>5.2f}  {flag}")
    summary = report["summary"]
    print("-" * 72)
    print(f"mean recall@{report['k']}: {summary['mean_recall_at_k']}   "
          f"MRR: {summary['mrr']}   pass rate: {summary['pass_rate']}")
    print(f"by category: {summary['by_category']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate retrieval against the gold set.")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fail-under", type=float, default=None,
                        help="Exit 1 if mean recall@k is below this value.")
    args = parser.parse_args()

    engine = ChunkSearchEngine(load_payload(CHUNKS_PATH))
    gold = json.loads(GOLD_PATH.read_text())
    report = evaluate(engine, gold, k=args.top_k)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)

    if args.fail_under is not None and report["summary"]["mean_recall_at_k"] < args.fail_under:
        print(f"\nFAIL: mean recall@{args.top_k} "
              f"{report['summary']['mean_recall_at_k']} < {args.fail_under}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m pytest tests/test_run_eval.py -v`
Expected: PASS (3 passed). If `test_easy_question_retrieves_expected_doc` fails, that is a real finding about the current searcher — record it; do not weaken the test to make it pass.

- [ ] **Step 5: Run the whole test suite**

Run: `venv\Scripts\python.exe -m pytest -q`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add eval/run_eval.py tests/test_run_eval.py
git commit -m "feat: add retrieval evaluation runner with recall/MRR and category pass rates"
```

---

### Task 5: Capture the baseline

**Files:**
- Create: `eval/BASELINE.md`

**Interfaces:**
- Consumes: the runner from Task 4.
- Produces: a committed record of the current searcher's numbers, so [plans/03-retrieval-rebuild.md](03-retrieval-rebuild.md) can prove it improved (or at least did not regress) retrieval.

- [ ] **Step 1: Run the harness and capture output**

Run: `venv\Scripts\python.exe -m eval.run_eval --top-k 5`
Then run: `venv\Scripts\python.exe -m eval.run_eval --top-k 5 --json`
Copy both outputs.

- [ ] **Step 2: Write the baseline record**

Create `eval/BASELINE.md` with: the date, the command used, the printed table, and the summary line (mean recall@5, MRR, pass rate, by-category). Add one sentence noting this is the **keyword-only, overfit** searcher (the baseline we want to beat with a generalizable retriever).

- [ ] **Step 3: Sanity-check the gate flag works**

Run: `venv\Scripts\python.exe -m eval.run_eval --top-k 5 --fail-under 0.99`
Expected: exits non-zero and prints a FAIL line (0.99 is deliberately unreachable — this proves the gate works). Then run with `--fail-under 0.0` and confirm exit 0.

- [ ] **Step 4: Commit**

```bash
git add eval/BASELINE.md
git commit -m "docs: record baseline retrieval metrics for the keyword-only searcher"
```

---

## Self-Review

- **Spec coverage:** Gold set covers answerable (q03, q06, q08), multi-doc (q01, q02, q05, q07), the hard contradiction case (q04), the gap (q09), the intentional-unanswerable abstention probe (q11), citation behavior (q10), and an injection probe (q12). Metrics cover recall@k, precision@k (available), and MRR. The `--fail-under` flag provides the pass/fail gate the review asked for. Answer-level grading (groundedness, citation correctness, abstention) is explicitly deferred to plan 04 and the rows are tagged `grade: "answer"` so they are not silently ignored.
- **Placeholder scan:** none — every step has real code, real paths, and real commands.
- **Type consistency:** `retrieved_doc_ids` returns `list[str]`; `evaluate` consumes it; metric functions all take `(list[str], list[str], int)`. The runner imports `ChunkSearchEngine`/`load_payload` which exist in `scripts/search_chunks.py`.

## Execution Handoff

Run task-by-task with **superpowers:subagent-driven-development** (recommended) or **superpowers:executing-plans**. After Task 5 you will have a committed baseline; proceed to [plans/02-access-control.md](02-access-control.md).
