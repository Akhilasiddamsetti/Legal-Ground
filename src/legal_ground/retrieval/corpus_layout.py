from __future__ import annotations

from pathlib import Path


def case_metadata_path(corpus_dir: Path) -> Path:
    corpus_dir = Path(corpus_dir)
    case_layout = corpus_dir / "_meta" / "metadata.json"
    return case_layout if case_layout.exists() else corpus_dir / "metadata.json"


def case_chunks_path(corpus_dir: Path) -> Path:
    corpus_dir = Path(corpus_dir)
    if (corpus_dir / "_meta" / "metadata.json").exists():
        return corpus_dir / "_retrieval" / "chunks.json"
    return corpus_dir / "chunks.json"


def case_embeddings_path(corpus_dir: Path) -> Path:
    corpus_dir = Path(corpus_dir)
    if (corpus_dir / "_meta" / "metadata.json").exists():
        return corpus_dir / "_retrieval" / "embeddings.npz"
    return corpus_dir / "embeddings.npz"

