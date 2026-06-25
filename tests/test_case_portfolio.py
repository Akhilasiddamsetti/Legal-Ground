from pathlib import Path

from legal_ground.retrieval.portfolio import discover_case_roots, merge_case_payloads, merge_case_vectors

ROOT = Path(__file__).resolve().parent.parent
EXPECTED_CASES = {
    "acme-v-northridge",
    "beacon-v-summit",
    "forge-v-axis",
    "harbor-v-ironcrest",
    "redcliff-v-sterling",
    "valewood-v-triton",
}


def test_discover_case_roots_finds_professional_cases_only():
    roots = discover_case_roots(ROOT / "sample-docs")
    names = {root.name for root in roots}
    assert names == EXPECTED_CASES
    assert "_archive" not in names


def test_merged_payload_namespaces_chunk_ids():
    roots = discover_case_roots(ROOT / "sample-docs")
    payload = merge_case_payloads(roots)
    chunk_ids = [chunk["chunk_id"] for chunk in payload["chunks"]]

    assert len(chunk_ids) == payload["chunk_count"]
    assert len(chunk_ids) == len(set(chunk_ids))
    assert all("::" in chunk_id for chunk_id in chunk_ids)
    assert set(payload["matter_ids"]) == EXPECTED_CASES


def test_merged_vectors_align_with_merged_chunks():
    roots = discover_case_roots(ROOT / "sample-docs")
    payload = merge_case_payloads(roots)
    ids, matrix = merge_case_vectors(roots)

    assert len(ids) == payload["chunk_count"]
    assert matrix.shape[0] == payload["chunk_count"]
    assert all("::" in chunk_id for chunk_id in ids)
