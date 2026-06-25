import json

from learning_curve.assistant.logbook import log_exchange


def test_log_exchange_appends_jsonl(tmp_path):
    record = {
        "matter_id": "acme-v-northridge",
        "user_id": "u1",
        "question": "q",
        "answer": "a",
    }
    path = log_exchange(record, tmp_path)
    path2 = log_exchange({**record, "question": "q2"}, tmp_path)
    assert path == path2
    lines = path.read_text().strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["question"] == "q"
    assert json.loads(lines[1])["question"] == "q2"
    assert path.name == "acme-v-northridge.log.jsonl"
