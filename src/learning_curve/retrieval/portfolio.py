from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np

from learning_curve.retrieval.corpus_layout import case_chunks_path, case_embeddings_path, case_metadata_path


def is_case_root(case_root: Path) -> bool:
    root = Path(case_root)
    return (
        root.is_dir()
        and case_metadata_path(root).exists()
        and case_chunks_path(root).exists()
        and case_embeddings_path(root).exists()
    )


def discover_case_roots(portfolio_root: Path) -> list[Path]:
    roots: list[Path] = []
    for child in sorted(Path(portfolio_root).iterdir()):
        if not child.is_dir() or child.name.startswith("_"):
            continue
        if is_case_root(child):
            roots.append(child)
    return roots


def namespace_chunk_id(matter_id: str, chunk_id: str) -> str:
    return f"{matter_id}::{chunk_id}"


def load_case_metadata(case_root: Path) -> dict:
    return json.loads(case_metadata_path(case_root).read_text(encoding="utf-8"))


def load_case_payload(case_root: Path) -> dict:
    return json.loads(case_chunks_path(case_root).read_text(encoding="utf-8"))


def merge_case_payloads(case_roots: list[Path]) -> dict:
    if not case_roots:
        raise ValueError("no professional case folders found to merge")

    merged_chunks: list[dict] = []
    manifests: list[str] = []
    matter_ids: list[str] = []
    matter_names: list[str] = []
    seen_ids: set[str] = set()

    for case_root in case_roots:
        payload = load_case_payload(case_root)
        matter_id = payload["matter_id"]
        matter_ids.append(matter_id)
        matter_names.append(payload.get("matter_name", matter_id))
        manifests.append(payload.get("source_manifest", ""))

        for chunk in payload["chunks"]:
            namespaced = copy.deepcopy(chunk)
            namespaced["raw_chunk_id"] = chunk["chunk_id"]
            namespaced["chunk_id"] = namespace_chunk_id(matter_id, chunk["chunk_id"])
            if namespaced["chunk_id"] in seen_ids:
                raise ValueError(f"duplicate merged chunk id: {namespaced['chunk_id']}")
            seen_ids.add(namespaced["chunk_id"])
            merged_chunks.append(namespaced)

    return {
        "schema_version": "portfolio-1.0",
        "matter_id": "multi-case-demo",
        "matter_name": "Professional Demo Portfolio",
        "source_manifests": manifests,
        "matter_ids": matter_ids,
        "matter_names": matter_names,
        "chunk_count": len(merged_chunks),
        "chunks": merged_chunks,
    }


def merge_case_vectors(case_roots: list[Path]) -> tuple[list[str], np.ndarray]:
    if not case_roots:
        raise ValueError("no professional case folders found to merge")

    all_ids: list[str] = []
    matrices: list[np.ndarray] = []

    for case_root in case_roots:
        payload = load_case_payload(case_root)
        matter_id = payload["matter_id"]
        data = np.load(case_embeddings_path(case_root), allow_pickle=True)
        ids = [namespace_chunk_id(matter_id, str(value)) for value in data["ids"]]
        if len(ids) != data["vectors"].shape[0]:
            raise ValueError(f"embedding row count mismatch for {case_root}")
        all_ids.extend(ids)
        matrices.append(data["vectors"])

    return all_ids, np.concatenate(matrices, axis=0)
