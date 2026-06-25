# Consult: Review of new/uncommitted changes (deposition-prep RAG prototype)

Date: 2026-06-23
Tool: ask-codex (Codex MCP, model gpt-5.x-codex, sandbox read-only)
Thread: 019ef7b9-fdb0-71a0-965d-626e9450424e

## Problem framed

User asked for Codex's independent take on the new/uncommitted work in the repo:
`plan.md` (8-phase plan), `phase1-scope-note.md`, `sample-docs/` (synthetic legal pack
+ chunks.json), `scripts/build_sample_chunks.py`, `scripts/search_chunks.py`, modified
`README.md` — judged against the `Ticket` (secure matter-scoped RAG deposition assistant
with hard acceptance criteria: >=90% factual support, >=95% citation accuracy, no
fabrication, prompt-injection resistance, matter-level access control, hybrid search).

## Claude's take (anchor, formed before consulting)

Plan is a strong skeleton but not yet an engineering plan. Under-specifies the three things
that decide success: (1) evaluation methodology vs the 90/95 targets, (2) grounding /
anti-hallucination + abstention design, (3) security enforcement mechanism + injection
defense. Retrieval (`search_chunks.py`) is keyword-only (BM25 + heuristics), no embeddings,
and overfit to the 10 sample questions (hardcoded Exhibit 12 / doc_id boosts) — won't
generalize. Plan and repo have diverged (Phase 1/3 done; Phase 4 took a different path than
written). Research context: Stanford RegLab study — commercial legal RAG tools still
hallucinate 17-33%; the 90/95 targets are reachable only with strict grounding + abstention
on a clean corpus.

## Codex's reply (verbatim summary)

- Probe failed (Windows sandbox helper `codex-windows-sandbox-setup.exe` not found) -> no
  native reads; reviewed from pasted excerpts.
- Coherent as a single-matter learning prototype; NOT yet coherent as a ticket-satisfying
  implementation. Strongest part = synthetic corpus design (intentional contradictions +
  one unresolved question = right cases for grounding/abstention).
- Plan has good bones (phase order, "don't overbuild early", first milestone) but Phase 6 is
  too underspecified vs Ticket:48-60. Needs: definition of "supported by source", "correct
  citation" + granularity, dataset size/composition, who labels/adjudicates, how
  contradictions are scored, how unanswerables are scored, pass/fail gates tied to thresholds.
- Anti-hallucination: "add citations" + "insufficient evidence" necessary but not sufficient.
  Require: answer only from retrieved evidence; surface conflicts instead of silently picking;
  abstain when support missing/contradictory; evaluate claim-to-citation support.
- Security: "metadata filters" too thin. Spell out enforcement point, Entra->matter mapping,
  ACL flow into index/retrieval, deny-by-default, where prompts/responses/chunks/embeddings
  live.
- Prompt injection: plan describes testing, not mitigation. Add control strategy (retrieved
  text as data not instructions; system-prompt isolation; malicious-document tests).
- Code divergences: not hybrid (no vector imports), BM25+heuristics only
  (search_chunks.py:168-259); no visible matter/user authz in search path
  (search_chunks.py:168-210); overfit synonym map collapses legally-distinct terms
  (approve/approved/approval->release, deposition->witness) (search_chunks.py:52-95) +
  corpus-specific boosts (search_chunks.py:212-259); no answer-gen layer yet, so
  anti-fabrication + injection criteria are unimplemented intent.
- Single most important change: make evaluation concrete NOW — turn Phase 6 into a gating
  harness with an attorney-reviewed gold set covering answerable / contradictory /
  unanswerable / access-denied / prompt-injection cases, gold passages per answerable case,
  explicit scoring rules. Code corollary: remove corpus-specific boosts + add explicit
  matter_id/user-scope filtering in search().

## Reconciliation

Strong convergence — no material disagreement. Two independent reviews reached the same
top-3 gaps and the same #1 recommendation (build the eval/gating harness now; de-overfit the
retriever).

New insight Codex contributed beyond Claude's take: the synonym map collapses legally-distinct
terms. Verified vs source (search_chunks.py:53-55,60,90). Notably `approve/approval -> release`
erases exactly the distinction in the corpus's one intentional unresolved question
("who gave final approval to release the shipment", sample-docs/README.md:48).

## Verification of Codex code claims (against actual source)

- approve/approved/approval->release, deposition->witness: VERIFIED search_chunks.py:53-55,60,90
- no embeddings/vector imports: VERIFIED search_chunks.py:1-5 (stdlib only)
- no authz filter in search(): VERIFIED search_chunks.py:168-181
- corpus-specific heuristic boosts (Exhibit 12, doc_id-specific): VERIFIED search_chunks.py:231-257
- no LLM/auth/logging code yet: VERIFIED (repo contains only the two scripts)
