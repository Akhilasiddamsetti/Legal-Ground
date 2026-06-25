"""Lexical tokenization for BM25 retrieval.

CANONICAL_TOKENS is intentionally empty: hand-built synonym collapsing distorted
legally-distinct terms. Semantic matching is handled by the vector arm when enabled.
"""

from __future__ import annotations

import re

TOKEN_RE = re.compile(r"[a-z0-9]+")
STOPWORDS = {
    "about",
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "did",
    "do",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "them",
    "there",
    "these",
    "this",
    "those",
    "to",
    "was",
    "what",
    "when",
    "which",
    "who",
    "will",
    "with",
}
CANONICAL_TOKENS: dict[str, str] = {}


def normalize_token(token: str) -> str:
    token = token.lower()
    token = CANONICAL_TOKENS.get(token, token)
    if len(token) > 4 and token.endswith("ing"):
        token = token[:-3]
    elif len(token) > 3 and token.endswith("ed"):
        token = token[:-2]
    elif len(token) > 4 and token.endswith("es"):
        token = token[:-2]
    elif len(token) > 3 and token.endswith("s"):
        token = token[:-1]
    token = CANONICAL_TOKENS.get(token, token)
    return token


def tokenize(text: str) -> list[str]:
    tokens = []
    for raw in TOKEN_RE.findall(text.lower()):
        token = normalize_token(raw)
        if token and token not in STOPWORDS:
            tokens.append(token)
    return tokens
