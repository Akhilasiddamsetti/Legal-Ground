from pathlib import Path

import pytest

from legal_ground.web.documents import list_case_documents, load_document_source

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "sample-docs"


def test_loads_source_text_for_a_known_document():
    doc = load_document_source("acme-v-northridge", "exhibit-12-inspection-report", CORPUS)
    assert doc["title"] == "Exhibit 12 Inspection Report"
    assert doc["matter_id"] == "acme-v-northridge"
    assert len(doc["text"]) > 50
    assert "inspection" in doc["text"].lower()


def test_unknown_document_raises_keyerror():
    with pytest.raises(KeyError):
        load_document_source("acme-v-northridge", "no-such-doc", CORPUS)


def test_unknown_matter_raises_keyerror():
    with pytest.raises(KeyError):
        load_document_source("not-a-matter", "complaint", CORPUS)


def test_list_case_documents_omits_text():
    docs = list_case_documents("acme-v-northridge", CORPUS)
    assert len(docs) >= 1
    assert all("text" not in d for d in docs)
    assert any(d["doc_id"] == "complaint" for d in docs)
