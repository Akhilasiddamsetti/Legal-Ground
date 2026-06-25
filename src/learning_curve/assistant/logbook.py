"""Append-only, per-matter exchange log."""

from __future__ import annotations

import json
from pathlib import Path


def log_exchange(record: dict, log_dir: Path) -> Path:
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    matter_id = record.get("matter_id", "unknown-matter")
    path = log_dir / f"{matter_id}.log.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
    return path
