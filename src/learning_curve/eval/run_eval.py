import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from learning_curve import config
from learning_curve.eval.metrics import precision_at_k, recall_at_k, reciprocal_rank
from learning_curve.retrieval import ChunkSearchEngine, VectorIndex, load_payload
from learning_curve.retrieval.embeddings import SentenceTransformerEmbedder
from learning_curve.security.access import Principal, pilot_principal

GOLD_PATH = Path(__file__).resolve().parent / "gold_set.json"
CHUNKS_PATH = config.DEFAULT_CORPUS_DIR / "chunks.json"
EMBEDDINGS_PATH = config.DEFAULT_CORPUS_DIR / "embeddings.npz"


def retrieved_doc_ids(results: list[dict]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for result in results:
        doc_id = result["chunk"]["doc_id"]
        if doc_id not in seen:
            seen.add(doc_id)
            ordered.append(doc_id)
    return ordered


def evaluate(engine: ChunkSearchEngine, gold: dict, k: int, principal: Principal) -> dict:
    rows = []
    by_category_pass: dict[str, list[bool]] = defaultdict(list)

    for question in gold["questions"]:
        if question["grade"] != "retrieval":
            continue

        results = engine.search(question["question"], principal, top_k=k)
        retrieved = retrieved_doc_ids(results)
        expected = question["expected_doc_ids"]
        hits = sum(1 for doc_id in expected if doc_id in set(retrieved[:k]))
        passed = hits >= question["min_expected_hits"]

        row = {
            "id": question["id"],
            "category": question["category"],
            "retrieved": retrieved,
            "expected": expected,
            "recall_at_k": recall_at_k(retrieved, expected, k),
            "precision_at_k": precision_at_k(retrieved, expected, k),
            "reciprocal_rank": reciprocal_rank(retrieved, expected),
            "hits": hits,
            "passed": passed,
        }
        rows.append(row)
        by_category_pass[question["category"]].append(passed)

    mean_recall = sum(row["recall_at_k"] for row in rows) / len(rows) if rows else 0.0
    mean_precision = sum(row["precision_at_k"] for row in rows) / len(rows) if rows else 0.0
    mrr = sum(row["reciprocal_rank"] for row in rows) / len(rows) if rows else 0.0
    by_category = {category: sum(flags) / len(flags) for category, flags in by_category_pass.items()}

    return {
        "k": k,
        "rows": rows,
        "summary": {
            "mean_recall_at_k": round(mean_recall, 3),
            "mean_precision_at_k": round(mean_precision, 3),
            "mrr": round(mrr, 3),
            "pass_rate": round(sum(row["passed"] for row in rows) / len(rows), 3) if rows else 0.0,
            "by_category": {category: round(value, 3) for category, value in by_category.items()},
        },
    }


def print_report(report: dict) -> None:
    print(f"Retrieval evaluation (top_k={report['k']})")
    print()
    print(f"{'question':<34} {'cat':<16} {'recall':>6} {'prec':>6} {'rr':>5}  pass")
    print("-" * 80)
    for row in report["rows"]:
        flag = "PASS" if row["passed"] else "FAIL"
        print(
            f"{row['id']:<34} {row['category']:<16} "
            f"{row['recall_at_k']:>6.2f} {row['precision_at_k']:>6.2f} {row['reciprocal_rank']:>5.2f}  {flag}"
        )
    summary = report["summary"]
    print("-" * 80)
    print(
        f"mean recall@{report['k']}: {summary['mean_recall_at_k']}   "
        f"mean precision@{report['k']}: {summary['mean_precision_at_k']}   "
        f"MRR: {summary['mrr']}   pass rate: {summary['pass_rate']}"
    )
    print(f"by category: {summary['by_category']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate retrieval against the gold set.")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--with-vectors",
        action="store_true",
        help="Load embeddings and run hybrid (BM25 + vector) retrieval.",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--fail-under",
        type=float,
        default=None,
        help="Exit 1 if mean recall@k is below this value.",
    )
    args = parser.parse_args()

    if args.with_vectors:
        engine = ChunkSearchEngine(
            load_payload(CHUNKS_PATH),
            vector_index=VectorIndex.load(EMBEDDINGS_PATH),
            embedder=SentenceTransformerEmbedder(),
        )
    else:
        engine = ChunkSearchEngine(load_payload(CHUNKS_PATH))
    gold = json.loads(GOLD_PATH.read_text())
    report = evaluate(engine, gold, k=args.top_k, principal=pilot_principal())

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)

    if args.fail_under is not None and report["summary"]["mean_recall_at_k"] < args.fail_under:
        print(
            f"\nFAIL: mean recall@{args.top_k} "
            f"{report['summary']['mean_recall_at_k']} < {args.fail_under}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
