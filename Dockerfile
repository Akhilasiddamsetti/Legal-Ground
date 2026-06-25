# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

# Install the package first for better layer caching.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

# Pre-download the embedding model so retrieval runs offline at request time
# (the search path loads it with local_files_only=True).
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Bundle the demo corpus. Override LC_CORPUS_DIR (and mount a volume) for real data.
COPY sample-docs ./sample-docs

ENV LC_HOST=0.0.0.0 \
    LC_PORT=8000 \
    LC_CORPUS_DIR=/app/sample-docs \
    LC_LOG_DIR=/app/logs

EXPOSE 8000

# Live answers require AWS Bedrock: pass AWS_REGION and credentials at `docker run`
# (e.g. -e AWS_REGION=us-east-1 -e AWS_ACCESS_KEY_ID=... -e AWS_SECRET_ACCESS_KEY=...).
CMD ["learning-curve-web"]
