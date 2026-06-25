import json
from pathlib import Path

from learning_curve.eval.run_eval import GOLD_PATH, evaluate, retrieved_doc_ids
from learning_curve.retrieval import ChunkSearchEngine, VectorIndex
from learning_curve.retrieval.embeddings import SentenceTransformerEmbedder
from learning_curve.security.access import Principal, pilot_principal

ROOT = Path(__file__).resolve().parent.parent
GOLD = json.loads(GOLD_PATH.read_text())
PAYLOAD = json.loads((ROOT / "sample-docs" / "chunks.json").read_text())
EMBEDDINGS = ROOT / "sample-docs" / "embeddings.npz"


def test_retrieved_doc_ids_dedupes_and_preserves_order():
    results = [
        {"chunk": {"doc_id": "a"}},
        {"chunk": {"doc_id": "a"}},
        {"chunk": {"doc_id": "b"}},
    ]
    assert retrieved_doc_ids(results) == ["a", "b"]


def test_evaluate_scores_only_retrieval_rows():
    engine = ChunkSearchEngine(
        PAYLOAD,
        vector_index=VectorIndex.load(EMBEDDINGS),
        embedder=SentenceTransformerEmbedder(),
    )
    report = evaluate(engine, GOLD, k=5, principal=pilot_principal())
    retrieval_ids = {question["id"] for question in GOLD["questions"] if question["grade"] == "retrieval"}
    scored_ids = {row["id"] for row in report["rows"]}
    assert scored_ids == retrieval_ids
    assert 0.0 <= report["summary"]["mean_recall_at_k"] <= 1.0


def test_easy_question_retrieves_expected_doc():
    engine = ChunkSearchEngine(
        PAYLOAD,
        vector_index=VectorIndex.load(EMBEDDINGS),
        embedder=SentenceTransformerEmbedder(),
    )
    report = evaluate(engine, GOLD, k=5, principal=pilot_principal())
    q03 = next(row for row in report["rows"] if row["id"] == "q03-witness-failed-inspection")
    assert "deposition-transcript-excerpt" in q03["retrieved"][:3]
    assert q03["passed"] is True


def test_unauthorized_principal_scores_zero():
    engine = ChunkSearchEngine(
        PAYLOAD,
        vector_index=VectorIndex.load(EMBEDDINGS),
        embedder=SentenceTransformerEmbedder(),
    )
    outsider = Principal("intruder", "pilot_user", frozenset({"other-matter"}))
    report = evaluate(engine, GOLD, k=5, principal=outsider)
    assert all(row["recall_at_k"] == 0.0 for row in report["rows"])
    assert report["summary"]["pass_rate"] == 0.0
