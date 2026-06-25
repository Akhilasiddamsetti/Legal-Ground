"""Read-only access to a case's source documents for the corpus/source viewer (SP2).

Self-contained on purpose: it re-reads each case's metadata.json rather than
depending on the runtime, so it stays decoupled from app_runtime/case_portfolio.
"""

from __future__ import annotations

import json
from pathlib import Path

from legal_ground import config
from legal_ground.retrieval.corpus_layout import case_metadata_path
from legal_ground.retrieval.portfolio import discover_case_roots

DEFAULT_CORPUS_DIR = config.DEFAULT_CORPUS_DIR


def _case_root_for(matter_id: str, portfolio_root: Path) -> tuple[Path, dict]:
    """Find the case folder + metadata whose matter_id matches, across a portfolio
    root (multi-case) or a single flat corpus dir."""
    portfolio_root = Path(portfolio_root)
    for root in discover_case_roots(portfolio_root):
        meta = json.loads(case_metadata_path(root).read_text(encoding="utf-8"))
        if meta.get("matter_id") == matter_id:
            return root, meta
    flat_meta_path = case_metadata_path(portfolio_root)
    if flat_meta_path.exists():
        meta = json.loads(flat_meta_path.read_text(encoding="utf-8"))
        if meta.get("matter_id") == matter_id:
            return portfolio_root, meta
    raise KeyError(matter_id)


def _doc_record(doc: dict, matter_id: str) -> dict:
    doc_type = doc.get("doc_type", "") or ""
    return {
        "matter_id": matter_id,
        "doc_id": doc.get("doc_id"),
        "title": doc.get("title") or doc.get("doc_id") or "Untitled",
        "type": doc_type.replace("_", " ").title() if doc_type else "Document",
        "date": doc.get("created_date", ""),
        "citation_label": doc.get("citation_label") or doc.get("title") or "",
    }


def list_case_documents(matter_id: str, portfolio_root: Path = DEFAULT_CORPUS_DIR) -> list[dict]:
    _, meta = _case_root_for(matter_id, portfolio_root)
    return [_doc_record(doc, matter_id) for doc in meta.get("documents", [])]


def load_document_source(
    matter_id: str,
    doc_id: str,
    portfolio_root: Path = DEFAULT_CORPUS_DIR,
) -> dict:
    root, meta = _case_root_for(matter_id, portfolio_root)
    doc = next((d for d in meta.get("documents", []) if d.get("doc_id") == doc_id), None)
    if doc is None:
        raise KeyError(doc_id)
    filename = doc.get("filename") or Path(doc.get("source_path", "")).name
    if not filename:
        raise KeyError(doc_id)
    record = _doc_record(doc, matter_id)
    record["text"] = (root / filename).read_text(encoding="utf-8")
    return record
