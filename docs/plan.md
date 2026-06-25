# Plan For The Deposition Prep AI Assistant

## Why this file exists

This file breaks the big ticket into smaller tasks so we can work through them one step at a time.

The goal is to keep the work simple, clear, and easy to track.

## Main goal

Build a secure AI assistant that helps attorneys prepare for depositions by searching approved case documents and answering with clear source citations.

## How we will work

We will not try to build everything at once.

We will work in phases:

1. Understand the exact problem.
2. Confirm security and data rules.
3. Prepare the documents.
4. Build search and retrieval.
5. Build the assistant.
6. Test accuracy and security.
7. Run a pilot with real users.
8. Document results and decide what to do next.

We should finish one phase before moving deeply into the next one.

## Update — Review outcome (2026-06-23)

This plan was reviewed against the ticket by two independent reviewers (Claude and Codex). They agreed on the same conclusion:

> The phase structure is good, but the plan was a project-management plan, not yet an engineering plan. It under-specified the three things that actually decide whether *this* product works.

We are keeping all eight phases below. We are adding four things the review said were missing, and we are breaking the real engineering work into detailed step-by-step sub-plans (see "Detailed sub-plans" near the end of this file).

### The four things we are adding

1. **Evaluation is now a gating workstream, not a late phase.**
   "Measure accuracy" is not enough. Before we trust any answer, we need a labeled gold set and named metrics (retrieval recall@k, citation correctness, answer groundedness) with pass/fail gates tied to the ticket targets (≥90% of factual answers supported by their cited source, ≥95% citation accuracy). Reality check from research: the best *commercial* legal-AI tools still hallucinate 17–33% of the time, so those targets are only reachable with strict grounding plus abstention on a clean corpus.

2. **The assistant must follow a written grounding contract.**
   Answer only from retrieved evidence. Cite every factual claim. Surface conflicts instead of silently picking one version. Abstain when support is missing or contradictory. Never obey instructions found inside a document.

3. **Security must name its enforcement mechanism.**
   "Metadata filters" is too thin. Access is enforced at retrieval time, deny-by-default, by checking the caller's identity (matter + role) against each chunk's `access_scope`. Unauthorized chunks are filtered out *before* scoring, so they can never appear in results or context.

4. **Prompt injection needs a defense, not just a test.**
   Retrieved document text is treated as untrusted data, not instructions. We isolate it in the prompt, and we test malicious *documents*, not just malicious user prompts.

### What the code actually looks like today (plan ≠ repo)

- Phase 1 (scope) and Phase 3 (documents) are effectively done: `phase1-scope-note.md`, `sample-docs/`, `chunks.json`.
- Phase 4 (retrieval) took a shortcut that diverges from this plan: `scripts/search_chunks.py` is **keyword-only** (BM25 + hand-coded boosts), with **no embeddings and no hybrid search**, and its scoring is **overfit** to the 10 sample questions (e.g. a hardcoded Exhibit 12 boost, doc-id-specific boosts). It also has **no access control** in the search path, and its synonym map collapses legally distinct terms (`approve`/`approval` → `release`). That is a fine learning v0, but it must be rebuilt before it can serve the ticket.
- Phases 5–8 have not started (no LLM call, auth, or logging exists yet).

## Phase 1: Understand the problem and limit the scope

### Why this matters

This ticket is too big if we treat it as "build an AI product for all legal work."

We need to make the first version small and realistic.

### Subtasks

- Pick one pilot matter only.
- Pick one document source only.
- Pick one user group only.
- Write down the top 10 real questions attorneys want the system to answer.
- Decide what "success" means for the pilot.
- Decide what is out of scope for version 1.

### Output of this phase

- A short scope note
- A list of real attorney questions
- A list of success metrics

### Done when

- Everyone agrees on one pilot matter
- Everyone agrees on one document source
- Everyone agrees on the first set of supported use cases

## Phase 2: Confirm security, permissions, and approvals

### Why this matters

This is a legal document system. Security is not optional.

If access control is weak, the whole project fails even if the AI answers well.

### Subtasks

- Confirm that the client allows AI use for this matter.
- Confirm what data can and cannot be used.
- Confirm retention and logging rules.
- Confirm who is allowed to access the matter.
- Confirm how ethical walls will be enforced.
- Pick the approved model and hosting environment.
- Pick the approved identity system for login.

### Output of this phase

- Security checklist
- Access rules
- Approved architecture direction

### Done when

- Security stakeholders approve the pilot approach
- We know exactly who can access the system
- We know where logs can be stored and for how long

## Phase 3: Prepare the document collection

### Why this matters

The assistant is only as good as the documents we feed into it.

Bad text extraction or missing metadata will cause bad answers and bad citations.

### Subtasks

- Identify the approved documents for the pilot matter.
- Collect pleadings, transcripts, exhibits, discovery responses, and other allowed files.
- Extract text from each file.
- Clean up OCR issues where possible.
- Remove duplicate files.
- Store useful metadata for each file.
- Add source links so users can open the original document.

### Important metadata to capture

- Matter ID
- Document name
- Document type
- Source location
- Page number
- Transcript line number if available
- Exhibit number if available
- Access rules

### Output of this phase

- A clean pilot document set
- Extracted text
- Metadata for search and citation

### Done when

- We have a trusted set of approved documents
- We can trace each text chunk back to the original file
- We can open the original source from stored metadata

## Phase 4: Build the retrieval and search layer

> **Detailed plans:** [plans/02-access-control.md](plans/02-access-control.md) (enforce access first) then [plans/03-retrieval-rebuild.md](plans/03-retrieval-rebuild.md) (remove overfit heuristics, add embeddings + hybrid).

### Why this matters

This is the part that finds the right evidence before the model writes an answer.

If retrieval is weak, the model will either miss facts or guess.

### Subtasks

- Decide how to split documents into chunks.
- Generate embeddings for the chunks.
- Build vector search.
- Build keyword search.
- Combine both into hybrid search.
- Add metadata filters for matter-level access.
- Make sure only approved documents can be retrieved.
- Return the best matching passages with citation data.

### Output of this phase

- A working retrieval pipeline
- Search results that include source and citation information

### Done when

- A user question returns relevant document passages
- Results stay inside the approved matter
- Each result has enough metadata for a citation

## Phase 5: Build the assistant itself

> **Detailed plan:** [plans/04-assistant-grounding.md](plans/04-assistant-grounding.md) (answer flow, grounding contract, abstention, injection defense, logging).

### Why this matters

This is where search results become a usable answer for attorneys.

The assistant must answer clearly, stay grounded in evidence, and avoid pretending when evidence is missing.

### Subtasks

- Add user authentication.
- Enforce authorization before retrieval runs.
- Create system instructions for the assistant.
- Build the question and answer flow.
- Pass retrieved evidence into the model.
- Format answers in plain language.
- Add citations to every factual answer.
- Add links to the original source documents.
- Add "insufficient evidence" behavior.
- Log prompts and responses according to policy.

### Output of this phase

- A working assistant that can answer pilot questions
- Source citations on every factual answer

### Done when

- Users can log in
- Users only see what they are allowed to see
- Answers include citations
- The assistant refuses to invent unsupported facts

## Phase 6: Test quality and security

> **Detailed plan:** [plans/01-evaluation-harness.md](plans/01-evaluation-harness.md). This is started **first** (not last): it is the gate the other steps are measured against.

### Why this matters

We should not trust the system just because it runs.

We need proof that it is accurate, safe, and useful.

### Subtasks

- Create a test set of real legal questions.
- Write expected answers and expected sources.
- Include easy questions.
- Include hard questions.
- Include ambiguous questions.
- Include unanswerable questions.
- Measure factual accuracy.
- Measure citation accuracy.
- Test for hallucinations.
- Test for prompt injection.
- Test unauthorized access attempts.
- Test PII and privileged-data handling.
- Record failures and fix the main problems.

### Output of this phase

- Evaluation report
- Security test results
- List of known weaknesses

### Done when

- We can measure answer quality with evidence
- We know where the assistant is weak
- Major security problems are fixed or clearly documented

## Phase 7: Run the pilot

### Why this matters

The system is only useful if real attorneys find it helpful in real work.

### Subtasks

- Choose a small pilot group.
- Give them access.
- Train them on how to use the tool.
- Explain the tool's limits.
- Collect usage data.
- Collect feedback from each pilot user.
- Measure whether prep time goes down.
- Track where users trust the system and where they do not.

### Output of this phase

- Pilot usage data
- User feedback
- Time-saving evidence

### Done when

- Pilot users complete testing
- We have clear feedback from real users
- We can say whether the tool saved meaningful time

## Phase 8: Document everything and make a decision

### Why this matters

A pilot is not complete until the results are written down and the next decision is clear.

### Subtasks

- Write technical documentation.
- Write a simple user guide.
- Write an operations runbook.
- Summarize accuracy, risks, and lessons learned.
- Summarize adoption and time saved.
- Recommend one of these options:
  - Move toward production
  - Revise and run another pilot
  - Stop the project

### Output of this phase

- Technical docs
- User guide
- Runbook
- Final recommendation

### Done when

- The team understands what was built
- The risks are documented
- Leadership has enough information to decide what happens next

## Suggested order for the engineering work

This is the order I would use:

1. Lock the pilot scope.
2. Lock the security rules.
3. Prepare and clean the pilot documents.
4. Build retrieval.
5. Build the first assistant flow.
6. Add citations and source links.
7. Add logging and access checks.
8. Run evaluation tests.
9. Fix the biggest quality and security issues.
10. Run the pilot.
11. Write the final recommendation.

## What we should not do too early

- Do not build a fancy UI first.
- Do not support many matters at once in version 1.
- Do not connect to every document system on day one.
- Do not optimize for scale before we prove usefulness.
- Do not trust model answers without citation testing.

## First milestone for us

Our first milestone should be this:

"A logged-in pilot user can ask one question about one approved matter, and the system returns an answer with citations from approved source documents only."

If we can do that well, the rest becomes much easier to plan.

## Detailed sub-plans

The real engineering work (Phases 4–6) is broken into four step-by-step plans. Each one is small enough to finish on its own, ends in something testable, and is written so it can be executed task-by-task. Do them in this order — each builds on the one before:

| Step | Plan | Goal | Depends on |
|------|------|------|------------|
| 1 | [plans/01-evaluation-harness.md](plans/01-evaluation-harness.md) | A gold set + a script that measures retrieval quality, so every later change is graded, not guessed. | nothing (run it against today's searcher first) |
| 2 | [plans/02-access-control.md](plans/02-access-control.md) | A caller identity (matter + role) and a deny-by-default access filter inside `search()`. | step 1 (to prove it didn't break recall) |
| 3 | [plans/03-retrieval-rebuild.md](plans/03-retrieval-rebuild.md) | Remove the overfit boosts and lossy synonyms; add embeddings + hybrid (RRF) search. | steps 1–2 (gate on the harness; keep the access filter) |
| 4 | [plans/04-assistant-grounding.md](plans/04-assistant-grounding.md) | The actual assistant: grounded answers, citations, abstention, injection defense, logging. Extends the harness to grade answers. | steps 1–3 |

**Why this order:** the review's single most important recommendation was "make evaluation concrete *now*, not later." Step 1 builds the gate. Step 2 is the smallest safe code change. Step 3 is the biggest retrieval change and must be proven against the gate. Step 4 turns retrieval into a usable, safe assistant.

## Next step

Phase 1 is already done (`phase1-scope-note.md`). Our immediate task is **Step 1 above**: build the evaluation harness in [plans/01-evaluation-harness.md](plans/01-evaluation-harness.md) and run it against the current `search_chunks.py` to get a baseline.

## Phase 1 Detailed Execution Plan

This section explains exactly how we should complete Phase 1 in simple steps.

The purpose of Phase 1 is to reduce confusion before any real building starts.

If we finish Phase 1 well, then the later engineering work becomes much easier and much safer.

### Step 1: Choose the pilot matter

We need to choose one matter only for the first version.

We should not pick the biggest or hardest matter.

We should pick a matter that:

- has clear approval to use for the pilot
- has enough useful documents
- has a small number of known users
- is important enough to test real value
- is not too complex for a first attempt

### Step 2: Choose the first document source

We need to decide where the assistant will read documents from in version 1.

We should pick only one source first.

Examples:

- SharePoint
- one approved DMS workspace
- one matter folder approved by the firm

The main idea is simple:

one source is easier to secure, easier to test, and easier to debug.

### Step 3: Choose the first user group

We need to decide who the first users are.

This should be a very small group.

For example:

- 3 to 5 attorneys
- or 1 practice team working on the pilot matter

These users should be people who:

- actually do deposition preparation
- are willing to test the system
- can give clear feedback

### Step 4: Collect the real questions users care about

We need to talk to the users and write down real questions they would ask during deposition prep.

We do not want fake demo questions.

We want real questions like:

- Create a chronology of events.
- Show inconsistent statements.
- Find testimony about a specific exhibit.
- Show what topics have not yet been covered.

We should collect around 10 good questions for the first version.

### Step 5: Decide what version 1 will and will not do

This is where we draw boundaries.

Version 1 should do a few useful things well.

Version 1 should not try to do everything.

For example, version 1 may support:

- asking questions about one matter
- retrieving answers from approved documents
- showing citations and source links

Version 1 may not support:

- multiple matters
- all document systems
- advanced workflows like filing or drafting final legal advice

### Step 6: Define success in simple measurable terms

We need to define how we will decide whether Phase 1 and later the pilot are successful.

Success should be measurable, not vague.

Examples:

- users can answer common deposition-prep questions faster
- answers are supported by source documents
- citations point to the right source
- unauthorized users cannot see restricted matter content

### Step 7: Write the scope note

At the end of Phase 1, we should write one short scope note.

That note should answer these questions:

- What matter are we piloting?
- Who are the first users?
- What document source are we using?
- What exact questions are we supporting first?
- What is out of scope?
- How will we measure success?

### What we need to ask the business team in Phase 1

These are the plain-English questions we should get answered:

- Which matter should be the pilot matter?
- Is the client okay with AI being used for this matter?
- Which documents are approved for the pilot?
- Where do those documents live today?
- Who should be allowed to use the assistant?
- What are the top questions attorneys want answered?
- What would make attorneys say the pilot was helpful?
- What would make the firm say the pilot should not continue?

### Deliverables for Phase 1

When Phase 1 is finished, we should have:

- one chosen pilot matter
- one chosen document source
- one chosen pilot user group
- one list of top attorney questions
- one simple list of version 1 features
- one simple list of out-of-scope items
- one clear set of success measures
- one short scope note

### Simple checklist for us

- Pick the pilot matter.
- Pick the first document source.
- Pick the first user group.
- Gather 10 real user questions.
- Define version 1 scope.
- Define out-of-scope items.
- Define success measures.
- Write the scope note.

### Done means Phase 1 is complete when

- we know exactly what we are building first
- we know exactly who it is for
- we know exactly which documents it will use
- we know exactly how success will be measured
- we have written this down clearly enough that engineering can start Phase 2 without guessing
