from pathlib import Path

from fastapi.testclient import TestClient

from legal_ground.assistant.llm import StubLLM
from legal_ground.web.app import create_app
from legal_ground.web.runtime import build_runtime_from_llm

ROOT = Path(__file__).resolve().parent.parent


def _client(tmp_path):
    runtime = build_runtime_from_llm(
        StubLLM(lambda system, user: "Daniel Price reviewed Exhibit 12 [1]."),
        corpus_dir=ROOT / "sample-docs",
        all_cases=True,
        log_dir=tmp_path,
    )
    return TestClient(create_app(runtime))


def test_threads_replays_prior_turns(tmp_path):
    client = _client(tmp_path)
    client.post(
        "/ask",
        json={"question": "What did the witness say?", "matter": "acme-v-northridge", "role": "pilot_user"},
    )
    response = client.get("/threads/acme-v-northridge?role=pilot_user")
    assert response.status_code == 200
    turns = response.json()["turns"]
    assert len(turns) >= 1
    assert turns[-1]["question"] == "What did the witness say?"
    assert "abstained" in turns[-1]


def test_threads_empty_for_fresh_matter(tmp_path):
    response = _client(tmp_path).get("/threads/beacon-v-summit?role=pilot_user")
    assert response.status_code == 200
    assert response.json()["turns"] == []


def test_threads_rejects_unknown_role(tmp_path):
    response = _client(tmp_path).get("/threads/acme-v-northridge?role=outsider")
    assert response.status_code == 400
