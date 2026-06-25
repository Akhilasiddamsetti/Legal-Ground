import argparse
import json
import re
from pathlib import Path

from legal_ground import config
from legal_ground.retrieval.corpus_layout import case_chunks_path, case_metadata_path

ROOT = config.REPO_ROOT
DEFAULT_CORPUS_DIR = config.DEFAULT_CORPUS_DIR

PAGE_RE = re.compile(r"^## Page (\d+)$", re.M)
EMAIL_RE = re.compile(r"^### Email (\d+)$", re.M)
TRANSCRIPT_RE = re.compile(r"^### Page (\d+), Lines (\d+-\d+)$", re.M)
SECTION_RE = re.compile(r"^### (.+)$", re.M)


def split_pages(document_text: str) -> list[tuple[int, str]]:
    page_start = PAGE_RE.search(document_text)
    body = document_text[page_start.start() :] if page_start else document_text
    page_matches = list(PAGE_RE.finditer(body))
    pages: list[tuple[int, str]] = []

    for index, match in enumerate(page_matches):
        start = match.end()
        end = page_matches[index + 1].start() if index + 1 < len(page_matches) else len(body)
        page_number = int(match.group(1))
        page_text = body[start:end].strip()
        pages.append((page_number, page_text))

    return pages


def base_chunk(doc: dict, matter_id: str, matter_name: str, chunk_index: int) -> dict:
    return {
        "matter_id": matter_id,
        "matter_name": matter_name,
        "doc_id": doc["doc_id"],
        "doc_title": doc["title"],
        "doc_type": doc["doc_type"],
        "source_path": doc["source_path"],
        "source_kind": doc["source_kind"],
        "created_date": doc["created_date"],
        "chunk_index": chunk_index,
        "citation_label": doc["citation_label"],
        "participants": doc["participants"],
        "tags": doc["tags"],
        "access_scope": doc["access_scope"],
        "related_docs": doc.get("related_docs", []),
        "exhibit_number": doc.get("exhibit_number"),
    }


def build_page_chunks(doc: dict, matter_id: str, matter_name: str, page_sections: list[tuple[int, str]]) -> list[dict]:
    chunks: list[dict] = []

    for chunk_index, (page_number, page_text) in enumerate(page_sections, start=1):
        section_titles = SECTION_RE.findall(page_text)
        section_title = " | ".join(section_titles) if section_titles else f"Page {page_number}"
        chunk = base_chunk(doc, matter_id, matter_name, chunk_index)
        chunk.update(
            {
                "chunk_id": f"{doc['doc_id']}-p{page_number}",
                "chunk_type": "page",
                "page_number": page_number,
                "page_marker": f"Page {page_number}",
                "line_range": None,
                "section_title": section_title,
                "citation": {
                    "display_text": f"{doc['citation_label']}, Page {page_number}",
                    "page_number": page_number,
                    "line_range": None,
                    "section_title": section_title,
                },
                "text": page_text,
                "search_text": f"{doc['title']}\nPage {page_number}\n{page_text}",
            }
        )
        chunks.append(chunk)

    return chunks


def build_transcript_chunks(doc: dict, matter_id: str, matter_name: str, page_sections: list[tuple[int, str]]) -> list[dict]:
    chunks: list[dict] = []

    for chunk_index, (page_number, page_text) in enumerate(page_sections, start=1):
        transcript_match = TRANSCRIPT_RE.search(page_text)
        line_range = transcript_match.group(2) if transcript_match else None
        section_title = transcript_match.group(0).replace("### ", "") if transcript_match else f"Page {page_number}"
        chunk_text = page_text[transcript_match.end() :].strip() if transcript_match else page_text.strip()
        chunk = base_chunk(doc, matter_id, matter_name, chunk_index)
        chunk.update(
            {
                "chunk_id": f"{doc['doc_id']}-p{page_number}-l{line_range.replace('-', 'to')}",
                "chunk_type": "transcript_block",
                "page_number": page_number,
                "page_marker": f"Page {page_number}",
                "line_range": line_range,
                "section_title": section_title,
                "citation": {
                    "display_text": f"{doc['citation_label']}, Page {page_number}, Lines {line_range}",
                    "page_number": page_number,
                    "line_range": line_range,
                    "section_title": section_title,
                },
                "text": chunk_text,
                "search_text": f"{doc['title']}\n{section_title}\n{chunk_text}",
            }
        )
        chunks.append(chunk)

    return chunks


def build_email_chunks(doc: dict, matter_id: str, matter_name: str, page_sections: list[tuple[int, str]]) -> list[dict]:
    chunks: list[dict] = []
    chunk_index = 1

    for page_number, page_text in page_sections:
        email_matches = list(EMAIL_RE.finditer(page_text))

        for index, email_match in enumerate(email_matches):
            start = email_match.end()
            end = email_matches[index + 1].start() if index + 1 < len(email_matches) else len(page_text)
            email_number = int(email_match.group(1))
            chunk_text = page_text[start:end].strip()

            subject_match = re.search(r"^- Subject: (.+)$", chunk_text, re.M)
            date_match = re.search(r"^- Date: (.+)$", chunk_text, re.M)
            from_match = re.search(r"^- From: (.+)$", chunk_text, re.M)
            to_match = re.search(r"^- To: (.+)$", chunk_text, re.M)
            cc_match = re.search(r"^- Cc: (.+)$", chunk_text, re.M)

            chunk = base_chunk(doc, matter_id, matter_name, chunk_index)
            chunk.update(
                {
                    "chunk_id": f"{doc['doc_id']}-p{page_number}-email-{email_number}",
                    "chunk_type": "email",
                    "page_number": page_number,
                    "page_marker": f"Page {page_number}",
                    "line_range": None,
                    "section_title": f"Email {email_number}",
                    "citation": {
                        "display_text": f"{doc['citation_label']}, Page {page_number}, Email {email_number}",
                        "page_number": page_number,
                        "line_range": None,
                        "section_title": f"Email {email_number}",
                    },
                    "email_number": email_number,
                    "email_date": date_match.group(1) if date_match else None,
                    "email_from": from_match.group(1) if from_match else None,
                    "email_to": [item.strip() for item in to_match.group(1).split(",")] if to_match else [],
                    "email_cc": [item.strip() for item in cc_match.group(1).split(",")] if cc_match else [],
                    "email_subject": subject_match.group(1) if subject_match else None,
                    "text": chunk_text,
                    "search_text": f"{doc['title']}\nEmail {email_number}\n{chunk_text}",
                }
            )
            chunks.append(chunk)
            chunk_index += 1

    return chunks


def build_chunks(corpus_dir: Path = DEFAULT_CORPUS_DIR) -> dict:
    corpus_dir = corpus_dir.resolve()
    metadata_path = case_metadata_path(corpus_dir)
    manifest = json.loads(metadata_path.read_text())
    matter_id = manifest["matter_id"]
    matter_name = manifest["matter_name"]
    chunks: list[dict] = []

    for doc in manifest["documents"]:
        document_text = (corpus_dir / doc["filename"]).read_text().strip()
        page_sections = split_pages(document_text)

        if doc["doc_type"] == "email_chain":
            doc_chunks = build_email_chunks(doc, matter_id, matter_name, page_sections)
        elif doc["doc_type"].startswith("deposition_transcript"):
            doc_chunks = build_transcript_chunks(doc, matter_id, matter_name, page_sections)
        else:
            doc_chunks = build_page_chunks(doc, matter_id, matter_name, page_sections)

        chunks.extend(doc_chunks)

    return {
        "schema_version": "1.0",
        "matter_id": matter_id,
        "matter_name": matter_name,
        "source_manifest": metadata_path.relative_to(ROOT).as_posix(),
        "chunk_count": len(chunks),
        "chunking_rules": {
            "page_docs": "Chunk non-transcript, non-email documents by page marker.",
            "transcript_docs": "Chunk transcript documents by page and explicit line range block.",
            "email_docs": "Chunk email chains one email message at a time.",
        "citation_policy": "Each chunk carries page-based or page-and-line-based citation metadata.",
        },
        "chunks": chunks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build retrieval-ready chunks for a corpus directory.")
    parser.add_argument(
        "--corpus-dir",
        default=str(DEFAULT_CORPUS_DIR),
        help="Corpus directory or case root containing source Markdown files and metadata.",
    )
    args = parser.parse_args()

    corpus_dir = Path(args.corpus_dir).resolve()
    output_path = case_chunks_path(corpus_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_chunks(corpus_dir)
    output_path.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"Wrote {payload['chunk_count']} chunks to {output_path}")


if __name__ == "__main__":
    main()
