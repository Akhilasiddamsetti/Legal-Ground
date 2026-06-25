from pathlib import Path

from fastapi.testclient import TestClient

from learning_curve.assistant.llm import StubLLM
from learning_curve.web.app import create_app
from learning_curve.web.runtime import build_runtime_from_llm

ROOT = Path(__file__).resolve().parent.parent


def _scripted_llm():
    def responder(system, user):
        if "final approval to release" in user:
            return "INSUFFICIENT EVIDENCE"
        return "Daniel Price reviewed Exhibit 12 before the truck left [1]."

    return StubLLM(responder)


def _client(tmp_path):
    runtime = build_runtime_from_llm(
        _scripted_llm(),
        log_dir=tmp_path,
        default_user_id="web-demo",
    )
    return TestClient(create_app(runtime))


def _portfolio_client(tmp_path):
    runtime = build_runtime_from_llm(
        _scripted_llm(),
        corpus_dir=ROOT / "sample-docs",
        all_cases=True,
        log_dir=tmp_path,
        default_user_id="web-demo",
    )
    return TestClient(create_app(runtime))


def test_index_renders_controls_and_evidence_drawer(tmp_path):
    client = _client(tmp_path)
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="matter-select"' in response.text
    assert 'id="role-select"' in response.text
    assert 'id="ask-form"' in response.text
    # The evidence trail (sources, retrieved passages, run details, logs) is now a
    # client-rendered slide-in drawer rather than server-rendered <details> panels.
    assert 'id="drawer"' in response.text
    assert "Evidence trail" in response.text


def test_index_declares_favicon(tmp_path):
    client = _client(tmp_path)
    response = client.get("/")
    assert response.status_code == 200
    assert 'rel="icon"' in response.text
    assert "favicon.svg" in response.text


def test_favicon_is_served_with_long_cache(tmp_path):
    client = _client(tmp_path)
    response = client.get("/favicon.ico")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/")
    assert "max-age=" in response.headers.get("cache-control", "")


def test_health_endpoint_reports_ready(tmp_path):
    client = _client(tmp_path)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ask_returns_answer_payload(tmp_path):
    client = _client(tmp_path)
    response = client.post(
        "/ask",
        json={
            "question": "What did the witness say about the failed inspection?",
            "matter": "acme-v-northridge",
            "role": "pilot_user",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["abstained"] is False
    assert len(payload["citations"]) >= 1
    assert len(payload["debug"]["evidence_cards"]) >= 1
    assert payload["debug"]["recent_logs"][-1]["question"] == "What did the witness say about the failed inspection?"


def test_ask_returns_abstention_payload(tmp_path):
    client = _client(tmp_path)
    response = client.post(
        "/ask",
        json={
            "question": "Who gave the final approval to release the shipment?",
            "matter": "acme-v-northridge",
            "role": "pilot_user",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["abstained"] is True
    assert payload["citations"] == []


def test_invalid_role_is_rejected(tmp_path):
    client = _client(tmp_path)
    response = client.post(
        "/ask",
        json={
            "question": "What did the witness say?",
            "matter": "acme-v-northridge",
            "role": "outsider",
        },
    )
    assert response.status_code == 400
    assert "Unknown role" in response.json()["detail"]


def test_portfolio_runtime_lists_all_matters_and_answers_for_selected_case(tmp_path):
    client = _portfolio_client(tmp_path)
    index = client.get("/")
    assert index.status_code == 200
    assert 'value="beacon-v-summit"' in index.text
    assert 'value="valewood-v-triton"' in index.text

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["matter_count"] == 6

    response = client.post(
        "/ask",
        json={
            "question": "What did the witness say about the failed inspection?",
            "matter": "beacon-v-summit",
            "role": "pilot_user",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["abstained"] is False
    assert payload["debug"]["matter"] == "beacon-v-summit"
