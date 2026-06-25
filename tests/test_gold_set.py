import json
from pathlib import Path

from legal_ground.eval.run_eval import GOLD_PATH

ROOT = Path(__file__).resolve().parent.parent
GOLD = json.loads(GOLD_PATH.read_text())
KNOWN_DOC_IDS = {
    "complaint",
    "discovery-responses",
    "deposition-transcript-excerpt",
    "exhibit-12-inspection-report",
    "inspection-email-chain",
    "internal-meeting-notes",
}
VALID_CATEGORIES = {
    "answerable",
    "answerable_multi",
    "contradiction",
    "gap",
    "unanswerable",
    "behavior",
}


def test_gold_set_has_questions():
    assert GOLD["matter_id"] == "acme-v-northridge"
    assert len(GOLD["questions"]) >= 10


def test_every_question_is_well_formed():
    ids = set()
    for question in GOLD["questions"]:
        assert question["id"] not in ids, f"duplicate id {question['id']}"
        ids.add(question["id"])
        assert question["category"] in VALID_CATEGORIES
        assert question["grade"] in {"retrieval", "answer"}
        assert isinstance(question["expected_doc_ids"], list)
        for doc_id in question["expected_doc_ids"]:
            assert doc_id in KNOWN_DOC_IDS, f"unknown doc_id {doc_id} in {question['id']}"


def test_retrieval_rows_have_expectations():
    retrieval_rows = [question for question in GOLD["questions"] if question["grade"] == "retrieval"]
    assert len(retrieval_rows) >= 7
    for question in retrieval_rows:
        assert question["expected_doc_ids"], f"{question['id']} graded on retrieval but has no expected docs"
        assert 1 <= question["min_expected_hits"] <= len(question["expected_doc_ids"])
