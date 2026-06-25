from pathlib import Path

from fastapi.testclient import TestClient

from legal_ground.assistant.llm import StubLLM
from legal_ground.web.app import create_app
from legal_ground.web.runtime import build_runtime_from_llm

ROOT = Path(__file__).resolve().parent.parent


def _client(tmp_path):
    runtime = build_runtime_from_llm(
        StubLLM(lambda system, user: "ok"),
        corpus_dir=ROOT / "sample-docs",
        all_cases=True,
        log_dir=tmp_path,
    )
    return TestClient(create_app(runtime))


def test_open_document_source(tmp_path):
    response = _client(tmp_path).get(
        "/documents/acme-v-northridge/exhibit-12-inspection-report?role=pilot_user"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Exhibit 12 Inspection Report"
    assert "inspection" in body["text"].lower()


def test_open_document_rejects_unknown_role(tmp_path):
    response = _client(tmp_path).get(
        "/documents/acme-v-northridge/exhibit-12-inspection-report?role=outsider"
    )
    assert response.status_code == 400


def test_open_document_unknown_doc_is_404(tmp_path):
    response = _client(tmp_path).get(
        "/documents/acme-v-northridge/no-such-doc?role=pilot_user"
    )
    assert response.status_code == 404
