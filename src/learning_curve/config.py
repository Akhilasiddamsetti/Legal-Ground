"""Central configuration and path resolution.

All deployment knobs live here and are environment-overridable so the app runs
identically from source, pip-installed, or in a container (12-factor style).
"""

from __future__ import annotations

import os
from pathlib import Path

# src/learning_curve/config.py -> parents[0]=learning_curve, [1]=src, [2]=repo root
PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parents[1]


def _env_path(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value) if value else default


# Corpus (the matter document set). Repo-relative in dev; set LC_CORPUS_DIR in prod.
DEFAULT_CORPUS_DIR = _env_path("LC_CORPUS_DIR", REPO_ROOT / "sample-docs")
DEFAULT_LOG_DIR = _env_path("LC_LOG_DIR", REPO_ROOT / "logs")

# Web server
DEFAULT_HOST = os.environ.get("LC_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("LC_PORT", "8000"))

# Model / cloud (Bedrock). Region is required for live calls.
DEFAULT_AWS_REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
DEFAULT_AWS_PROFILE = os.environ.get("AWS_PROFILE")
DEFAULT_BEDROCK_MODEL = os.environ.get("BEDROCK_MODEL")
