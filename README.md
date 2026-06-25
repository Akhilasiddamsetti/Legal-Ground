# Learning Curve

A secure, access-controlled RAG assistant for legal **deposition preparation**. It
answers questions strictly from approved matter documents, with source citations,
and abstains when the evidence is insufficient. Built as an installable
`learning_curve` package.

## Install

```powershell
python -m venv venv
venv\Scripts\python.exe -m pip install -e ".[dev]"
```

This installs the package plus the console entry points below. (Plain `pip install .`
omits the dev tools — ruff, mypy, pytest.)

## Run the web app

```powershell
learning-curve-web --aws-region us-east-1
```

Then open `http://127.0.0.1:8000`. By default it loads the whole portfolio (all case
folders under `sample-docs/`) and lets you switch matters in the UI.

## Run the assistant (CLI)

```powershell
learning-curve-ask "What did the witness say about the failed inspection?" --aws-region us-east-1
```

## Retrieval-only search (no LLM, no AWS)

```powershell
learning-curve-search "What did the witness say about the failed inspection?" --with-vectors
learning-curve-search "Who gave the final approval to release the shipment?" --all-cases --matter redcliff-v-sterling --with-vectors
```

## Evaluate retrieval against the gold set

```powershell
learning-curve-eval --with-vectors --fail-under 0.75
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
docker build -t learning-curve .
docker run -p 8000:8000 -e AWS_REGION=us-east-1 \
  -e AWS_ACCESS_KEY_ID=... -e AWS_SECRET_ACCESS_KEY=... learning-curve
```

The image bundles the corpus and pre-downloads the embedding model, so retrieval runs
offline; only the Bedrock answer call needs AWS credentials at run time.

## Configuration (env vars)

| Variable | Default | Purpose |
|---|---|---|
| `LC_CORPUS_DIR` | `./sample-docs` | Corpus / matter document root |
| `LC_LOG_DIR` | `./logs` | Where exchange logs are written |
| `LC_HOST` / `LC_PORT` | `127.0.0.1` / `8000` | Web server bind |
| `AWS_REGION` | — | Bedrock region (required for live answers) |
| `BEDROCK_MODEL` | Claude Haiku 4.5 profile | Override the model |

## Demo matters

The professional case folders live under `sample-docs/<matter-id>/`:
`acme-v-northridge` (reference case), `beacon-v-summit`, `forge-v-axis`,
`harbor-v-ironcrest`, `redcliff-v-sterling`, `valewood-v-triton`.

Rebuild one case's retrieval files:

```powershell
lc-build-chunks --corpus-dir sample-docs/acme-v-northridge
lc-build-embeddings --corpus-dir sample-docs/acme-v-northridge
```

## Project layout

```
src/learning_curve/
  config.py            env-driven settings & paths
  security/access.py   deny-by-default matter+role access control
  retrieval/           engine.py · bm25.py · vectors.py · embeddings.py · corpus_layout.py · portfolio.py
  assistant/           assistant.py · prompt.py · llm.py · logbook.py
  web/                 app.py · runtime.py · documents.py · templates/ · static/
  cli/                 ask.py · search.py
  eval/                run_eval.py · metrics.py · grade_answers.py · gold_set.json
  tools/               build_chunks.py · build_embeddings.py · generate_demo_cases.py
tests/                 pytest suite (imports learning_curve.*)
sample-docs/           demo corpus (override with LC_CORPUS_DIR)
docs/                  plans, scope notes, ticket
```

## Development

```powershell
pytest                 # run the suite
ruff check src tests   # lint
mypy src               # type check
```
