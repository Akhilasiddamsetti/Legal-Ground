import json
from pathlib import Path

from legal_ground.assistant.llm import StubLLM
from legal_ground.retrieval.corpus_layout import case_metadata_path
from legal_ground.web.runtime import DEFAULT_CORPUS_DIR, build_runtime_from_llm

ROOT = Path(__file__).resolve().parent.parent
EXPECTED_CASES = {
    "acme-v-northridge",
    "beacon-v-summit",
    "forge-v-axis",
    "harbor-v-ironcrest",
    "redcliff-v-sterling",
    "valewood-v-triton",
}


def _runtime(tmp_path):
    return build_runtime_from_llm(StubLLM(lambda system, user: "ok"), log_dir=tmp_path)


def test_runtime_exposes_case_for_the_real_matter(tmp_path):
    runtime = _runtime(tmp_path)
    case = next(c for c in runtime.cases if c["id"] == "acme-v-northridge")
    assert "Acme" in case["name"]
    assert case["status"] == "Active"
    # the header's "N documents" label is driven by the corpus, not hardcoded
    assert case["doc_count"] == len(runtime.documents)


def test_runtime_exposes_documents_from_matter_metadata(tmp_path):
    runtime = _runtime(tmp_path)
    assert len(runtime.documents) >= 1
    doc = runtime.documents[0]
    assert {"title", "type", "date"} <= doc.keys()
    # documents mirror the matter's own metadata.json (robust to corpus growth)
    meta = json.loads(case_metadata_path(DEFAULT_CORPUS_DIR).read_text(encoding="utf-8"))
    assert len(runtime.documents) == len(meta["documents"])


def test_all_cases_runtime_exposes_full_portfolio(tmp_path):
    runtime = build_runtime_from_llm(
        StubLLM(lambda system, user: "ok"),
        corpus_dir=ROOT / "sample-docs",
        all_cases=True,
        log_dir=tmp_path,
    )
    assert set(runtime.allowed_matters) == EXPECTED_CASES
    assert len(runtime.cases) == 6
    assert all(case["doc_count"] == 16 for case in runtime.cases)
    assert len(runtime.documents) == 96
