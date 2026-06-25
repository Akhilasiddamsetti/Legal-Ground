import json
from pathlib import Path

from legal_ground.retrieval import ChunkSearchEngine
from legal_ground.retrieval.portfolio import discover_case_roots, merge_case_payloads
from legal_ground.security.access import Principal, pilot_principal

ROOT = Path(__file__).resolve().parent.parent
PAYLOAD = json.loads((ROOT / "sample-docs" / "chunks.json").read_text())


def test_authorized_principal_gets_results():
    engine = ChunkSearchEngine(PAYLOAD)
    results = engine.search(
        "What did the witness say about the failed inspection?",
        pilot_principal(),
        top_k=5,
    )
    assert len(results) > 0


def test_cross_matter_principal_gets_nothing():
    engine = ChunkSearchEngine(PAYLOAD)
    outsider = Principal("intruder", "pilot_user", frozenset({"some-other-matter"}))
    results = engine.search(
        "What did the witness say about the failed inspection?",
        outsider,
        top_k=5,
    )
    assert results == []


def test_wrong_role_gets_nothing():
    engine = ChunkSearchEngine(PAYLOAD)
    outsider = Principal("intruder", "not-a-pilot-role", frozenset({"acme-v-northridge"}))
    results = engine.search("inspection", outsider, top_k=5)
    assert results == []


def test_multi_case_search_stays_inside_selected_matter():
    payload = merge_case_payloads(discover_case_roots(ROOT / "sample-docs"))
    engine = ChunkSearchEngine(payload)
    principal = Principal("demo", "pilot_user", frozenset({"beacon-v-summit"}))
    results = engine.search("Exhibit 18 Truck 7721 hold", principal, top_k=5)
    assert len(results) > 0
    assert {result["chunk"]["matter_id"] for result in results} == {"beacon-v-summit"}
