import json
from pathlib import Path

from learning_curve.retrieval import ChunkSearchEngine, VectorIndex, reciprocal_rank_fusion
from learning_curve.retrieval.embeddings import SentenceTransformerEmbedder
from learning_curve.security.access import Principal, pilot_principal

ROOT = Path(__file__).resolve().parent.parent
PAYLOAD = json.loads((ROOT / "sample-docs" / "chunks.json").read_text())
NPZ = ROOT / "sample-docs" / "embeddings.npz"


def test_rrf_rewards_agreement():
    fused = dict(reciprocal_rank_fusion([["a", "b", "c"], ["b", "a", "d"]]))
    assert fused["a"] > fused["c"]
    assert fused["b"] > fused["d"]


def test_hybrid_engine_returns_access_filtered_results():
    index = VectorIndex.load(NPZ)
    engine = ChunkSearchEngine(
        PAYLOAD,
        vector_index=index,
        embedder=SentenceTransformerEmbedder(),
    )
    results = engine.search(
        "Who released the shipment after the failed inspection?",
        pilot_principal(),
        top_k=5,
    )
    assert 0 < len(results) <= 5
    outsider = Principal("x", "pilot_user", frozenset({"other-matter"}))
    assert engine.search("inspection", outsider, top_k=5) == []
