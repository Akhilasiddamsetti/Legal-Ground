"""Shared runtime construction for CLI and web entrypoints."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from legal_ground import config
from legal_ground.assistant.assistant import Assistant, AssistantAnswer
from legal_ground.assistant.llm import LLM, BedrockLLM
from legal_ground.retrieval import ChunkSearchEngine, VectorIndex, build_preview
from legal_ground.retrieval.corpus_layout import case_chunks_path, case_embeddings_path, case_metadata_path
from legal_ground.retrieval.embeddings import SentenceTransformerEmbedder
from legal_ground.retrieval.portfolio import (
    discover_case_roots,
    load_case_metadata,
    merge_case_payloads,
    merge_case_vectors,
)
from legal_ground.security.access import Principal

ROOT = config.REPO_ROOT
DEFAULT_CORPUS_DIR = config.DEFAULT_CORPUS_DIR
DEFAULT_CHUNKS_PATH = DEFAULT_CORPUS_DIR / "chunks.json"
DEFAULT_EMBEDDINGS_PATH = DEFAULT_CORPUS_DIR / "embeddings.npz"
DEFAULT_LOG_DIR = config.DEFAULT_LOG_DIR


@dataclass
class AppRuntime:
    payload: dict
    engine: ChunkSearchEngine
    assistant: Assistant
    allowed_matters: list[str]
    allowed_roles: list[str]
    log_dir: Path
    default_user_id: str = "web-demo"
    # Workspace display metadata (matter name, document list) for the Case Workspace UI.
    cases: list[dict] = field(default_factory=list)
    documents: list[dict] = field(default_factory=list)
    # Resolved LLM model id (e.g. the Bedrock model), surfaced at startup + in the UI.
    model_label: str = ""


def load_payload_file(chunks_path: Path = DEFAULT_CHUNKS_PATH) -> dict:
    return json.loads(chunks_path.read_text())


def resolve_corpus_paths(
    *,
    corpus_dir: Path | None = None,
    chunks_path: Path | None = None,
    embeddings_path: Path | None = None,
) -> tuple[Path, Path]:
    base_dir = Path(corpus_dir) if corpus_dir else DEFAULT_CORPUS_DIR
    resolved_chunks = Path(chunks_path) if chunks_path else case_chunks_path(base_dir)
    resolved_embeddings = Path(embeddings_path) if embeddings_path else case_embeddings_path(base_dir)
    return resolved_chunks, resolved_embeddings


def derive_access_options(payload: dict) -> tuple[list[str], list[str]]:
    matters: set[str] = set()
    roles: set[str] = set()
    for chunk in payload["chunks"]:
        scope = chunk.get("access_scope")
        if not isinstance(scope, dict):
            continue
        matter_id = scope.get("matter_id")
        if isinstance(matter_id, str) and matter_id:
            matters.add(matter_id)
        allowed_roles = scope.get("allowed_roles", [])
        if isinstance(allowed_roles, list):
            for role in allowed_roles:
                if isinstance(role, str) and role:
                    roles.add(role)
    return sorted(matters), sorted(roles)


def _humanize_doc_type(doc_type: str) -> str:
    return doc_type.replace("_", " ").title() if doc_type else "Document"


def _documents_from_manifest(raw: dict) -> list[dict]:
    matter_id = raw.get("matter_id")
    matter_name = raw.get("matter_name")
    return [
        {
            "matter_id": matter_id,
            "matter_name": matter_name,
            "doc_id": doc.get("doc_id"),
            "title": doc.get("title") or doc.get("doc_id") or "Untitled",
            "type": _humanize_doc_type(doc.get("doc_type", "")),
            "date": doc.get("created_date", ""),
            "citation_label": doc.get("citation_label") or doc.get("title") or "",
        }
        for doc in raw.get("documents", [])
    ]


# Which generated demo questions to surface as "quick ask" chips, in display order.
# These numbers map to the consistent template in tools/generate_demo_cases.py
# (_meta/demo-questions.md). The full question text is always case-specific; the
# short chip label is derived per case below, so each case reads differently.
SUGGESTION_NUMBERS: list[int] = [1, 2, 3, 4, 5, 7, 9, 11]


def _short_label(num: int, question: str) -> str:
    """A concise, case-relatable chip label derived from the full question."""
    if num == 2:
        m = re.search(r"Exhibit\s+(\d+)", question)
        return f"Exhibit {m.group(1)} sighting" if m else "Exhibit sighting"
    if num == 3:
        m = re.search(r"suggests\s+(.+?)\s+may have approved", question)
        return f"Did {m.group(1)} approve?" if m else "Who approved shipment?"
    return {
        1: "Chronology",
        4: "Release form timing",
        5: "Defect severity",
        7: "Customer pressure",
        9: "Contradictions",
        11: "Final approval",
    }.get(num, f"Question {num}")


def load_case_suggestions(case_root: Path) -> list[dict]:
    """Read a case's _meta/demo-questions.md and return its quick-ask prompts.

    Returns {"full", "short"} dicts in SUGGESTION_NUMBERS order. The full text is
    case-specific (real dates, exhibit/truck numbers, party names); the short label
    is derived per case. Empty if the file is missing, so callers can fall back.
    """
    qpath = Path(case_root) / "_meta" / "demo-questions.md"
    if not qpath.exists():
        return []
    by_num: dict[int, str] = {}
    for match in re.finditer(r"^\s*(\d+)\.\s+(.*\S)\s*$", qpath.read_text(encoding="utf-8"), re.MULTILINE):
        by_num[int(match.group(1))] = match.group(2).strip()

    picks = [
        {"full": by_num[n], "short": _short_label(n, by_num[n])}
        for n in SUGGESTION_NUMBERS
        if n in by_num
    ]
    if picks:
        return picks
    # Fallback: first few questions found, with generic labels.
    ordered = [by_num[k] for k in sorted(by_num)][:5]
    return [{"full": q, "short": f"Question {i + 1}"} for i, q in enumerate(ordered)]


def load_workspace_meta(corpus_dir: Path = DEFAULT_CORPUS_DIR) -> dict:
    """Load matter-level display metadata from one corpus directory."""
    meta_path = case_metadata_path(corpus_dir)
    if not meta_path.exists():
        return {"matter_id": None, "matter_name": None, "documents": [], "suggestions": []}
    raw = json.loads(meta_path.read_text(encoding="utf-8"))
    return {
        "matter_id": raw.get("matter_id"),
        "matter_name": raw.get("matter_name"),
        "documents": _documents_from_manifest(raw),
        "suggestions": load_case_suggestions(corpus_dir),
    }


def build_case_card(
    matter_id: str,
    matter_name: str,
    doc_count: int,
    suggestions: list[dict] | None = None,
) -> dict:
    return {
        "id": matter_id,
        "name": matter_name,
        "doc_count": doc_count,
        "doc_label": f"{doc_count} document" + ("" if doc_count == 1 else "s"),
        "status": "Active",
        "suggestions": suggestions or [],
    }


def build_cases(allowed_matters: list[str], metas: list[dict]) -> list[dict]:
    """Build workspace case cards from loaded metadata."""
    meta_by_matter = {meta.get("matter_id"): meta for meta in metas if meta.get("matter_id")}
    cases = []
    for matter_id in allowed_matters:
        meta = meta_by_matter.get(matter_id)
        doc_count = len(meta["documents"]) if meta else 0
        name = meta["matter_name"] if meta and meta.get("matter_name") else matter_id
        suggestions = meta.get("suggestions", []) if meta else []
        cases.append(build_case_card(matter_id, name, doc_count, suggestions))
    return cases


def build_hybrid_engine(
    payload: dict,
    embeddings_path: Path = DEFAULT_EMBEDDINGS_PATH,
    vector_index: VectorIndex | None = None,
) -> ChunkSearchEngine:
    return ChunkSearchEngine(
        payload,
        vector_index=vector_index or VectorIndex.load(embeddings_path),
        embedder=SentenceTransformerEmbedder(),
    )


def load_portfolio_workspace(case_roots: list[Path]) -> tuple[list[dict], list[dict]]:
    metas: list[dict] = []
    documents: list[dict] = []
    for case_root in case_roots:
        raw = load_case_metadata(case_root)
        meta = {
            "matter_id": raw.get("matter_id"),
            "matter_name": raw.get("matter_name"),
            "documents": _documents_from_manifest(raw),
            "suggestions": load_case_suggestions(case_root),
        }
        metas.append(meta)
        documents.extend(meta["documents"])
    return metas, documents


def build_runtime_from_llm(
    llm: LLM,
    *,
    top_k: int = 5,
    corpus_dir: Path | None = None,
    chunks_path: Path | None = None,
    embeddings_path: Path | None = None,
    all_cases: bool = False,
    log_dir: Path = DEFAULT_LOG_DIR,
    default_user_id: str = "web-demo",
) -> AppRuntime:
    if all_cases:
        portfolio_root = Path(corpus_dir) if corpus_dir else DEFAULT_CORPUS_DIR
        case_roots = discover_case_roots(portfolio_root)
        if not case_roots:
            raise ValueError(f"no professional case folders found under {portfolio_root}")

        payload = merge_case_payloads(case_roots)
        ids, matrix = merge_case_vectors(case_roots)
        engine = build_hybrid_engine(payload, vector_index=VectorIndex(ids, matrix))
        matters, roles = derive_access_options(payload)
        metas, documents = load_portfolio_workspace(case_roots)
        return AppRuntime(
            payload=payload,
            engine=engine,
            assistant=Assistant(engine, llm, top_k=top_k),
            allowed_matters=matters,
            allowed_roles=roles,
            log_dir=Path(log_dir),
            default_user_id=default_user_id,
            cases=build_cases(matters, metas),
            documents=documents,
            model_label=getattr(llm, "model", ""),
        )

    chunks_path, embeddings_path = resolve_corpus_paths(
        corpus_dir=corpus_dir,
        chunks_path=chunks_path,
        embeddings_path=embeddings_path,
    )
    payload = load_payload_file(chunks_path)
    engine = build_hybrid_engine(payload, embeddings_path=embeddings_path)
    assistant = Assistant(engine, llm, top_k=top_k)
    matters, roles = derive_access_options(payload)
    meta = load_workspace_meta(corpus_dir or DEFAULT_CORPUS_DIR)
    return AppRuntime(
        payload=payload,
        engine=engine,
        assistant=assistant,
        allowed_matters=matters,
        allowed_roles=roles,
        log_dir=Path(log_dir),
        default_user_id=default_user_id,
        cases=build_cases(matters, [meta]),
        documents=meta["documents"],
        model_label=getattr(llm, "model", ""),
    )


def build_live_runtime(
    *,
    top_k: int = 5,
    aws_region: str | None = None,
    aws_profile: str | None = None,
    bedrock_model: str | None = None,
    corpus_dir: Path | None = None,
    chunks_path: Path | None = None,
    embeddings_path: Path | None = None,
    all_cases: bool = False,
    log_dir: Path = DEFAULT_LOG_DIR,
    default_user_id: str = "web-demo",
) -> AppRuntime:
    llm = BedrockLLM(
        model=bedrock_model,
        aws_region=aws_region,
        aws_profile=aws_profile,
    )
    return build_runtime_from_llm(
        llm,
        top_k=top_k,
        corpus_dir=corpus_dir,
        chunks_path=chunks_path,
        embeddings_path=embeddings_path,
        all_cases=all_cases,
        log_dir=log_dir,
        default_user_id=default_user_id,
    )


def build_principal(
    matter: str,
    role: str,
    *,
    user_id: str = "local-cli",
) -> Principal:
    return Principal(user_id=user_id, role=role, matter_ids=frozenset({matter}))


def evidence_cards_from_answer(engine: ChunkSearchEngine, answer: AssistantAnswer) -> list[dict]:
    cards = []
    for chunk_id in answer.evidence_chunk_ids:
        chunk = engine.by_id[chunk_id]
        cards.append(
            {
                "chunk_id": chunk["chunk_id"],
                "display_text": chunk["citation"]["display_text"],
                "doc_title": chunk["doc_title"],
                "section_title": chunk["section_title"],
                "preview": build_preview(chunk["text"], 280),
                "tags": chunk.get("tags", []),
            }
        )
    return cards


def read_recent_logs(log_dir: Path, matter_id: str, limit: int = 5) -> tuple[str, list[dict]]:
    path = Path(log_dir) / f"{matter_id}.log.jsonl"
    if not path.exists():
        return str(path), []

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return str(path), rows[-limit:]
