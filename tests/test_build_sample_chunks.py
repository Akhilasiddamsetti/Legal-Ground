from pathlib import Path

from legal_ground.tools.build_chunks import build_chunks
from legal_ground.web.runtime import resolve_corpus_paths

ROOT = Path(__file__).resolve().parent.parent


def test_default_corpus_build_keeps_existing_manifest_path():
    payload = build_chunks(ROOT / "sample-docs")
    assert payload["source_manifest"] == "sample-docs/metadata.json"
    assert payload["matter_id"] == "acme-v-northridge"
    assert payload["chunk_count"] > 0


def test_case_root_resolves_retrieval_paths():
    chunks_path, embeddings_path = resolve_corpus_paths(corpus_dir=ROOT / "sample-docs" / "acme-v-northridge")
    assert chunks_path == ROOT / "sample-docs" / "acme-v-northridge" / "_retrieval" / "chunks.json"
    assert embeddings_path == ROOT / "sample-docs" / "acme-v-northridge" / "_retrieval" / "embeddings.npz"


def test_case_corpus_builds_with_expected_docs():
    payload = build_chunks(ROOT / "sample-docs" / "acme-v-northridge")
    doc_ids = {chunk["doc_id"] for chunk in payload["chunks"]}
    assert payload["source_manifest"] == "sample-docs/acme-v-northridge/_meta/metadata.json"
    assert "deposition-emma-carver" in doc_ids
    assert "shipment-release-form" in doc_ids
    assert "root-cause-memo" in doc_ids
    assert payload["chunk_count"] >= 30
