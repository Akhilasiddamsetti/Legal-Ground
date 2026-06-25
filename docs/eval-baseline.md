# Retrieval Baseline

## Date

2026-06-24

## Purpose

This file records the first retrieval baseline for the current search system.

This baseline belongs to the current keyword-only, heuristic-heavy searcher in `scripts/search_chunks.py`.

## Commands used

```powershell
venv\Scripts\python.exe -m eval.run_eval --top-k 5
venv\Scripts\python.exe -m eval.run_eval --top-k 5 --json
venv\Scripts\python.exe -m eval.run_eval --top-k 5 --fail-under 0.99
venv\Scripts\python.exe -m eval.run_eval --top-k 5 --fail-under 0.0
```

## Text report

```text
Retrieval evaluation (top_k=5)

question                           cat              recall   prec    rr  pass
--------------------------------------------------------------------------------
q01-chronology                     answerable_multi   0.50   0.40  1.00  FAIL
q02-around-exhibit-12              answerable_multi   0.33   0.20  1.00  FAIL
q03-witness-failed-inspection      answerable         1.00   0.20  1.00  PASS
q04-deposition-vs-discovery-conflict contradiction      1.00   0.40  1.00  PASS
q05-exhibit-12-references          answerable_multi   0.50   0.40  1.00  FAIL
q06-emails-defects-failures        answerable         1.00   0.20  1.00  PASS
q07-people-in-inspection-decision  answerable_multi   0.67   0.40  1.00  PASS
q08-topics-covered-in-testimony    answerable         1.00   0.20  1.00  PASS
q09-unanswered-topics              gap                1.00   0.20  0.50  PASS
--------------------------------------------------------------------------------
mean recall@5: 0.778   mean precision@5: 0.289   MRR: 0.944   pass rate: 0.667
by category: {'answerable_multi': 0.25, 'answerable': 1.0, 'contradiction': 1.0, 'gap': 1.0}
```

## JSON summary

```json
{
  "mean_recall_at_k": 0.778,
  "mean_precision_at_k": 0.289,
  "mrr": 0.944,
  "pass_rate": 0.667,
  "by_category": {
    "answerable_multi": 0.25,
    "answerable": 1.0,
    "contradiction": 1.0,
    "gap": 1.0
  }
}
```

## Plain-English interpretation

The current searcher does well on easy single-document questions and on the contradiction question, but it is much weaker on multi-document retrieval.

That matters because the real product needs to combine evidence from several documents, not just find one obvious source.

## Gate sanity check

- `--fail-under 0.99` failed as expected because `mean recall@5 = 0.778`
- `--fail-under 0.0` passed as expected

## Retrieval Rebuild Comparison

### Additional commands used

```powershell
venv\Scripts\python.exe -m eval.run_eval --top-k 5
venv\Scripts\python.exe -m eval.run_eval --top-k 5 --with-vectors
venv\Scripts\python.exe -m eval.run_eval --top-k 5 --with-vectors --fail-under 0.778
```

### Summary comparison

| mode | mean recall@5 | MRR | pass rate |
| --- | ---: | ---: | ---: |
| original keyword-only heuristic baseline | 0.778 | 0.944 | 0.667 |
| de-overfit BM25 only | 0.556 | 0.611 | 0.444 |
| hybrid BM25 + vectors | 0.815 | 0.815 | 0.778 |

### Plain-English note

Removing the hand-tuned boosts made the keyword-only retriever worse, which is expected because those shortcuts were compensating for lexical gaps.

The hybrid retriever recovered that loss and beat the original baseline on mean recall@5. The clearest wins were the witness/testimony style questions and the Exhibit 12 comparison question, where semantic matching helped even when exact words did not line up.
