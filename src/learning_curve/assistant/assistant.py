"""Orchestrates grounded, access-scoped question answering."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from learning_curve.assistant.llm import LLM
from learning_curve.assistant.logbook import log_exchange
from learning_curve.assistant.prompt import ABSTAIN_SENTINEL, build_system_prompt, build_user_prompt
from learning_curve.security.access import Principal

_CITATION_RE = re.compile(r"\[(\d+)\]")
_ABSTAIN_MESSAGE = "There is not enough information in the approved documents to answer this."


@dataclass
class AssistantAnswer:
    text: str
    abstained: bool
    citations: list[dict] = field(default_factory=list)
    evidence_chunk_ids: list[str] = field(default_factory=list)


class Assistant:
    def __init__(self, engine, llm: LLM, top_k: int = 5) -> None:
        self._engine = engine
        self._llm = llm
        self._top_k = top_k

    def answer(
        self,
        question: str,
        principal: Principal,
        log_dir: Path | None = None,
    ) -> AssistantAnswer:
        results = self._engine.search(question, principal, top_k=self._top_k)
        if not results:
            result_answer = AssistantAnswer(text=_ABSTAIN_MESSAGE, abstained=True)
            return self._log_and_return(result_answer, question, principal, log_dir)

        evidence = [result["chunk"] for result in results]
        evidence_ids = [chunk["chunk_id"] for chunk in evidence]

        reply = self._llm.complete(
            build_system_prompt(),
            build_user_prompt(question, evidence),
        ).strip()

        if self._is_abstention_reply(reply):
            result_answer = AssistantAnswer(
                text=_ABSTAIN_MESSAGE,
                abstained=True,
                evidence_chunk_ids=evidence_ids,
            )
            return self._log_and_return(result_answer, question, principal, log_dir)

        citations = []
        for marker in sorted({int(value) for value in _CITATION_RE.findall(reply)}):
            if 1 <= marker <= len(evidence):
                chunk = evidence[marker - 1]
                citations.append(
                    {
                        "marker": marker,
                        "display_text": chunk["citation"]["display_text"],
                        "chunk_id": chunk["chunk_id"],
                    }
                )

        result_answer = AssistantAnswer(
            text=reply,
            abstained=False,
            citations=citations,
            evidence_chunk_ids=evidence_ids,
        )
        return self._log_and_return(result_answer, question, principal, log_dir)

    @staticmethod
    def _is_abstention_reply(reply: str) -> bool:
        return reply.startswith(ABSTAIN_SENTINEL)

    def _log_and_return(
        self,
        result_answer: AssistantAnswer,
        question: str,
        principal: Principal,
        log_dir: Path | None,
    ) -> AssistantAnswer:
        if log_dir is not None:
            matter_ids = sorted(principal.matter_ids)
            log_exchange(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_id": principal.user_id,
                    "role": principal.role,
                    "matter_ids": matter_ids,
                    "matter_id": matter_ids[0] if matter_ids else "unknown-matter",
                    "question": question,
                    "answer": result_answer.text,
                    "abstained": result_answer.abstained,
                    "citations": result_answer.citations,
                },
                log_dir,
            )
        return result_answer
