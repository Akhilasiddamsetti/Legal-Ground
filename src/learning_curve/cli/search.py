"""CLI: retrieval-only search over a corpus (no LLM call)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from learning_curve import config
from learning_curve.retrieval.corpus_layout import case_chunks_path, case_embeddings_path
from learning_curve.retrieval.embeddings import SentenceTransformerEmbedder
from learning_curve.retrieval.engine import ChunkSearchEngine, build_preview, load_payload
from learning_curve.retrieval.portfolio import discover_case_roots, merge_case_payloads, merge_case_vectors
from learning_curve.retrieval.vectors import VectorIndex
from learning_curve.security.access import Principal


def print_human_results(query: str, results: list[dict], preview_chars: int) -> None:
    print(f"Query: {query}")
    print(f"Results: {len(results)}")

    for index, result in enumerate(results, start=1):
        chunk = result["chunk"]
        print()
        print(f"{index}. {chunk['citation']['display_text']}")
        print(f"   score: {result['score']:.3f}")
        print(f"   doc: {chunk['doc_title']} ({chunk['doc_type']})")
        print(f"   chunk_id: {chunk['chunk_id']}")
        print(f"   section: {chunk['section_title']}")
        print(f"   preview: {build_preview(chunk['text'], preview_chars)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Search retrieval-ready sample chunks.")
    parser.add_argument("query", help="User question or search query.")
    parser.add_argument("--corpus-dir", help="Case root for single-case mode, or portfolio root when used with --all-cases.")
    parser.add_argument("--all-cases", action="store_true", help="Load all professional case folders under the portfolio root.")
    parser.add_argument("--chunks", help="Path to chunks.json.")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to return.")
    parser.add_argument("--preview-chars", type=int, default=220, help="Preview length for printed results.")
    parser.add_argument("--role", default="pilot_user", help="Caller role.")
    parser.add_argument("--matter", default="acme-v-northridge", help="Caller matter id.")
    parser.add_argument("--user", default="local-cli", help="Caller user id.")
    parser.add_argument("--with-vectors", action="store_true", help="Load embeddings and run hybrid retrieval.")
    parser.add_argument("--embeddings", help="Path to embeddings.npz for hybrid retrieval.")
    parser.add_argument("--json", action="store_true", help="Print results as JSON.")
    args = parser.parse_args()

    corpus_dir = Path(args.corpus_dir).resolve() if args.corpus_dir else config.DEFAULT_CORPUS_DIR
    if args.all_cases and args.chunks:
        parser.error("--all-cases cannot be combined with --chunks.")
    if args.all_cases and args.embeddings:
        parser.error("--all-cases cannot be combined with --embeddings.")

    if args.all_cases:
        case_roots = discover_case_roots(corpus_dir)
        if not case_roots:
            parser.error(f"No professional case folders found under {corpus_dir}.")
        payload = merge_case_payloads(case_roots)
        if args.with_vectors:
            ids, matrix = merge_case_vectors(case_roots)
            engine = ChunkSearchEngine(
                payload,
                vector_index=VectorIndex(ids, matrix),
                embedder=SentenceTransformerEmbedder(),
            )
        else:
            engine = ChunkSearchEngine(payload)
    else:
        chunks_path = Path(args.chunks) if args.chunks else case_chunks_path(corpus_dir)
        embeddings_path = Path(args.embeddings) if args.embeddings else case_embeddings_path(corpus_dir)
        payload = load_payload(chunks_path)
        if args.with_vectors:
            engine = ChunkSearchEngine(
                payload,
                vector_index=VectorIndex.load(embeddings_path),
                embedder=SentenceTransformerEmbedder(),
            )
        else:
            engine = ChunkSearchEngine(payload)

    principal = Principal(user_id=args.user, role=args.role, matter_ids=frozenset({args.matter}))
    results = engine.search(args.query, principal, top_k=args.top_k)

    if args.json:
        print(json.dumps(results, indent=2))
        return

    print_human_results(args.query, results, args.preview_chars)


if __name__ == "__main__":
    main()
