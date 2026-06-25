# Legal Ground

A secure, access-controlled RAG assistant for legal **deposition preparation**. It
answers questions strictly from approved matter documents, with source citations,
and abstains when the evidence is insufficient. Built as an installable
`legal_ground` package.

## Highlights

- **Security-first retrieval.** A deny-by-default access filter scopes documents by
  matter and role *before* any scoring, so unauthorized content never reaches the
  model, the citations, the evidence drawer, or the logs.
- **Grounded answers with citations.** Every factual claim cites a source passage; the
  assistant surfaces conflicts between sources and abstains when the evidence genuinely
  does not support an answer — no invented facts.
- **Hybrid retrieval.** Okapi BM25 plus an optional dense-vector arm
  (`all-MiniLM-L6-v2`) fused with reciprocal-rank fusion, with a lexical floor so a
  strong keyword match is never diluted out of the results.
- **Multi-case workspace.** Six synthetic litigation matters, per-case suggested
  questions, an evidence drawer, and an in-app source viewer.
- **Runs on AWS Bedrock** (Claude Haiku 4.5 by default), fully environment-configurable,
  with a Docker image and an offline retrieval-only mode for development.


## Install

```powershell
python -m venv venv
venv\Scripts\python.exe -m pip install -e ".[dev]"
```

This installs the package plus the console entry points below. (Plain `pip install .`
omits the dev tools — ruff, mypy, pytest.)

## Run the web app

```powershell
legal-ground-web --aws-region us-east-1
```

Then open `http://127.0.0.1:8000`. By default it loads the whole portfolio (all case
folders under `sample-docs/`) and lets you switch matters in the UI.

## Run the assistant (CLI)

```powershell
legal-ground-ask "What did the witness say about the failed inspection?" --aws-region us-east-1
```

## Retrieval-only search (no LLM, no AWS)

```powershell
legal-ground-search "What did the witness say about the failed inspection?" --with-vectors
legal-ground-search "Who gave the final approval to release the shipment?" --all-cases --matter redcliff-v-sterling --with-vectors
```

## Evaluate retrieval against the gold set

```powershell
legal-ground-eval --with-vectors --fail-under 0.75
```

## AWS Bedrock setup (required for live answers)

The assistant calls Claude on AWS Bedrock. Confirm your identity and region access:

```powershell
aws sts get-caller-identity
```

Make sure your region has access to the Anthropic model in Bedrock. The default is the
global Claude Haiku 4.5 inference profile; override with `--bedrock-model` or the
`BEDROCK_MODEL` env var. All knobs are environment-overridable (see Configuration).

## Docker

```bash
docker build -t legal-ground .
docker run -p 8000:8000 -e AWS_REGION=us-east-1 \
  -e AWS_ACCESS_KEY_ID=... -e AWS_SECRET_ACCESS_KEY=... legal-ground
```

The image bundles the corpus and pre-downloads the embedding model, so retrieval runs
offline; only the Bedrock answer call needs AWS credentials at run time.

## Deploy & share a demo link

**Temporary public link (no hosting).** Run the helper script to start the app locally
and expose it through a Cloudflare quick tunnel — handy for a live demo or interview:

```powershell
.\run-demo.ps1            # prints a public https://<random>.trycloudflare.com link
```

The link is live only while the script runs, and Bedrock is billed per question, so
keep it up only during the demo. (Requires `cloudflared`:
`winget install --id Cloudflare.cloudflared`.)

**Always-on hosting (AWS App Runner).** Deploy straight from GitHub with no Docker and
keyless Bedrock access via an IAM role — see
[`deploy/DEPLOY-APPRUNNER.md`](deploy/DEPLOY-APPRUNNER.md).

## Configuration (env vars)

| Variable | Default | Purpose |
|---|---|---|
| `LG_CORPUS_DIR` | `./sample-docs` | Corpus / matter document root |
| `LG_LOG_DIR` | `./logs` | Where exchange logs are written |
| `LG_HOST` / `LG_PORT` | `127.0.0.1` / `8000` | Web server bind |
| `AWS_REGION` | — | Bedrock region (required for live answers) |
| `BEDROCK_MODEL` | Claude Haiku 4.5 profile | Override the model |

## Demo matters

The professional case folders live under `sample-docs/<matter-id>/`:
`acme-v-northridge` (reference case), `beacon-v-summit`, `forge-v-axis`,
`harbor-v-ironcrest`, `redcliff-v-sterling`, `valewood-v-triton`.

Rebuild one case's retrieval files:

```powershell
legal-ground-build-chunks --corpus-dir sample-docs/acme-v-northridge
legal-ground-build-embeddings --corpus-dir sample-docs/acme-v-northridge
```

## Project layout

```
src/legal_ground/
  config.py            env-driven settings & paths
  security/access.py   deny-by-default matter+role access control
  retrieval/           engine.py · bm25.py · vectors.py · embeddings.py · corpus_layout.py · portfolio.py
  assistant/           assistant.py · prompt.py · llm.py · logbook.py
  web/                 app.py · runtime.py · documents.py · templates/ · static/
  cli/                 ask.py · search.py
  eval/                run_eval.py · metrics.py · grade_answers.py · gold_set.json
  tools/               build_chunks.py · build_embeddings.py · generate_demo_cases.py
tests/                 pytest suite (imports legal_ground.*)
sample-docs/           demo corpus (override with LG_CORPUS_DIR)
docs/                  plans, scope notes, ticket
```

## Development

```powershell
pytest                 # run the suite
ruff check src tests   # lint
mypy src               # type check
```
