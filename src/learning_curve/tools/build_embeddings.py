import argparse
import json
from pathlib import Path

import numpy as np

from learning_curve import config
from learning_curve.retrieval.corpus_layout import case_chunks_path, case_embeddings_path
from learning_curve.retrieval.embeddings import SentenceTransformerEmbedder

ROOT = config.REPO_ROOT
DEFAULT_CORPUS_DIR = config.DEFAULT_CORPUS_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description="Build vector embeddings for a corpus directory.")
    parser.add_argument(
        "--corpus-dir",
        default=str(DEFAULT_CORPUS_DIR),
        help="Corpus directory or case root containing retrieval files.",
    )
    parser.add_argument("--chunks", help="Explicit path to chunks.json.")
    parser.add_argument("--output", help="Explicit output path for embeddings.npz.")
    parser.add_argument(
        "--allow-download",
        action="store_true",
        help="Allow the embedding model loader to reach Hugging Face if the model is not already cached.",
    )
    args = parser.parse_args()

    corpus_dir = Path(args.corpus_dir).resolve()
    chunks_path = Path(args.chunks) if args.chunks else case_chunks_path(corpus_dir)
    output_path = Path(args.output) if args.output else case_embeddings_path(corpus_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    chunks = json.loads(chunks_path.read_text())["chunks"]
    ids = [chunk["chunk_id"] for chunk in chunks]
    texts = [chunk["search_text"] for chunk in chunks]
    vectors = SentenceTransformerEmbedder(local_files_only=not args.allow_download).embed_texts(texts)
    np.savez(output_path, ids=np.array(ids, dtype=object), vectors=vectors)
    print(f"Wrote {vectors.shape[0]} embeddings ({vectors.shape[1]}-dim) to {output_path}")


if __name__ == "__main__":
    main()
