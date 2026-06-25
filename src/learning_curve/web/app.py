from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

import learning_curve.web.documents as documents_mod
from learning_curve import config
from learning_curve.web.runtime import (
    AppRuntime,
    build_live_runtime,
    build_principal,
    evidence_cards_from_answer,
    read_recent_logs,
)

# Web assets are bundled inside the package (learning_curve/web/{templates,static}),
# so they resolve identically from source, pip-installed, or in a container.
WEB_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(WEB_DIR / "templates"))
FAVICON_PATH = WEB_DIR / "static" / "favicon.svg"

# Starter "quick ask" prompts shown on an empty thread. Drawn from the pilot
# question set; the third is intentionally an abstention case for demos.
SUGGESTED_QUESTIONS = [
    {"full": "What did the witness say about the failed inspection?", "short": "Failed inspection"},
    {"full": "Who gave the final approval to release the shipment?", "short": "Final approval"},
    {"full": "How much did Acme pay North Ridge under the inspection contract?", "short": "Contract amount"},
]


def _default_role(roles: list[str]) -> str:
    if "pilot_user" in roles:
        return "pilot_user"
    return roles[0] if roles else "pilot_user"


class AskRequest(BaseModel):
    question: str
    matter: str
    role: str


def create_app(runtime: AppRuntime) -> FastAPI:
    app = FastAPI(title="Stakeholder Demo Assistant")
    app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> FileResponse:
        # Browsers auto-request /favicon.ico at the site root, which is outside the
        # /static mount. Serve the on-brand SVG here so that default probe resolves
        # (the <link> in index.html is the primary declaration). Cached aggressively
        # since the icon effectively never changes.
        return FileResponse(
            FAVICON_PATH,
            media_type="image/svg+xml",
            headers={"Cache-Control": "public, max-age=31536000, immutable"},
        )

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "matter_count": len(runtime.allowed_matters),
            "role_count": len(runtime.allowed_roles),
        }

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        return TEMPLATES.TemplateResponse(
            request,
            "index.html",
            {
                "app_title": "Learning Curve — Case Workspace",
                "matters": runtime.allowed_matters,
                "roles": runtime.allowed_roles,
                "cases": runtime.cases,
                "documents": runtime.documents,
                "suggestions": SUGGESTED_QUESTIONS,
                "user": {
                    "name": "Pilot User",
                    "org": "Litigation Practice Group",
                    "initials": "PU",
                    "role": _default_role(runtime.allowed_roles),
                },
            },
        )

    @app.post("/ask")
    def ask_turn(payload: AskRequest) -> dict:
        question = payload.question.strip()
        if not question:
            raise HTTPException(status_code=400, detail="Question cannot be empty.")
        if payload.matter not in runtime.allowed_matters:
            raise HTTPException(status_code=400, detail=f"Unknown matter: {payload.matter}")
        if payload.role not in runtime.allowed_roles:
            raise HTTPException(status_code=400, detail=f"Unknown role: {payload.role}")

        principal = build_principal(payload.matter, payload.role, user_id=runtime.default_user_id)
        try:
            answer = runtime.assistant.answer(question, principal, log_dir=runtime.log_dir)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Assistant request failed: {exc}") from exc

        log_path, recent_logs = read_recent_logs(runtime.log_dir, payload.matter)
        return {
            "answer_text": answer.text,
            "abstained": answer.abstained,
            "citations": answer.citations,
            "evidence_chunk_ids": answer.evidence_chunk_ids,
            "debug": {
                "request_timestamp": datetime.now(timezone.utc).isoformat(),
                "matter": payload.matter,
                "role": payload.role,
                "evidence_cards": evidence_cards_from_answer(runtime.engine, answer),
                "citation_map": answer.citations,
                "log_path": log_path,
                "recent_logs": recent_logs,
            },
        }

    @app.get("/documents/{matter}/{doc_id}")
    def open_document(matter: str, doc_id: str, role: str = Query(...)) -> dict:
        if matter not in runtime.allowed_matters:
            raise HTTPException(status_code=400, detail=f"Unknown matter: {matter}")
        if role not in runtime.allowed_roles:
            raise HTTPException(status_code=400, detail=f"Unknown role: {role}")
        try:
            return documents_mod.load_document_source(matter, doc_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Unknown document: {doc_id}") from exc

    @app.get("/threads/{matter}")
    def thread_history(matter: str, role: str = Query(...), limit: int = 20) -> dict:
        if matter not in runtime.allowed_matters:
            raise HTTPException(status_code=400, detail=f"Unknown matter: {matter}")
        if role not in runtime.allowed_roles:
            raise HTTPException(status_code=400, detail=f"Unknown role: {role}")
        _, rows = read_recent_logs(runtime.log_dir, matter, limit=limit)
        turns = [
            {
                "question": row.get("question", ""),
                "answer": row.get("answer", ""),
                "abstained": row.get("abstained", False),
                "citations": row.get("citations", []),
                "timestamp": row.get("timestamp", ""),
                "role": row.get("role", ""),
            }
            for row in rows
        ]
        return {"turns": turns}

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the stakeholder web UI.")
    parser.add_argument("--host", default=config.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=config.DEFAULT_PORT)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--corpus-dir", help="Case root for single-case mode, or portfolio root when used with --all-cases.")
    parser.add_argument("--all-cases", action="store_true", help="Load all professional case folders under the portfolio root.")
    parser.add_argument("--aws-region", default=config.DEFAULT_AWS_REGION)
    parser.add_argument("--aws-profile", default=config.DEFAULT_AWS_PROFILE)
    parser.add_argument("--bedrock-model", default=config.DEFAULT_BEDROCK_MODEL)
    args = parser.parse_args()

    all_cases = args.all_cases or args.corpus_dir is None
    runtime = build_live_runtime(
        top_k=args.top_k,
        corpus_dir=Path(args.corpus_dir) if args.corpus_dir else None,
        all_cases=all_cases,
        aws_region=args.aws_region,
        aws_profile=args.aws_profile,
        bedrock_model=args.bedrock_model,
    )
    app = create_app(runtime)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
