"""Provider-agnostic LLM adapter."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Protocol

from anthropic import AnthropicBedrock

# Default Bedrock model when neither --bedrock-model nor BEDROCK_MODEL is set.
# Claude Haiku 4.5 via the global (cross-region) inference profile.
DEFAULT_BEDROCK_MODEL_ID = "global.anthropic.claude-haiku-4-5-20251001-v1:0"


class LLM(Protocol):
    def complete(self, system: str, user: str) -> str:
        """Return the model's text response."""


class StubLLM:
    def __init__(self, responder: Callable[[str, str], str]) -> None:
        self._responder = responder

    def complete(self, system: str, user: str) -> str:
        return self._responder(system, user)


class BedrockLLM:
    def __init__(
        self,
        model: str | None = None,
        max_tokens: int = 1024,
        aws_region: str | None = None,
        aws_profile: str | None = None,
    ) -> None:
        resolved_region = aws_region or os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
        if not resolved_region:
            raise ValueError(
                "AWS region is required for Bedrock. Set AWS_REGION or AWS_DEFAULT_REGION, "
                "or pass aws_region explicitly."
            )

        resolved_profile = aws_profile or os.environ.get("AWS_PROFILE")

        self._client = AnthropicBedrock(
            aws_region=resolved_region,
            aws_profile=resolved_profile,
        )
        self._model = model or os.environ.get("BEDROCK_MODEL", DEFAULT_BEDROCK_MODEL_ID)
        self._max_tokens = max_tokens

    @property
    def model(self) -> str:
        """The resolved Bedrock model id actually used for requests."""
        return self._model

    def complete(self, system: str, user: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in response.content if block.type == "text")
