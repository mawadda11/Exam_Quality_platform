"""The one real AiProvider implementation (docs decision: local-first for
OCR, but no equivalent local option exists for semantic evaluation - see the
milestone's approved architecture). Uses forced tool-use, Anthropic's
documented mechanism for getting structured output, rather than prompting
for JSON and hoping - but per app.services.ai.provider's contract, this is
still only a best-effort nudge; app.services.rules.semantic_validation
independently validates whatever comes back.

Network/auth/rate-limit errors from the Anthropic SDK are deliberately not
caught here - they propagate as exceptions, which the existing pipeline
exception-safety net (app.services.processing.runner) already converts into
a safe processing failure. That is the correct outcome for an infrastructure
problem, and must not be silently turned into an academic "Not Verified"
conclusion (CLAUDE.md: "Processing failures are not academic statuses").
"""

from __future__ import annotations

import json
from typing import Any

import anthropic

_TOOL_NAME = "submit_evaluation"
_MAX_TOKENS = 1024


class AiProviderError(RuntimeError):
    """Raised when the provider responds but produces no usable structured
    output (e.g. no tool_use block despite forced tool_choice) - a genuine
    integration/infrastructure problem, not an academic judgment, so this
    propagates to the same safe-failure pipeline path as any other
    uncaught exception."""


class AnthropicAiProvider:
    def __init__(self, *, api_key: str, model: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def generate_structured(self, *, system: str, prompt: str, schema: dict[str, Any]) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=_MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            tools=[
                {
                    "name": _TOOL_NAME,
                    "description": "Submit the structured evaluation result.",
                    "input_schema": schema,
                }
            ],
            tool_choice={"type": "tool", "name": _TOOL_NAME},
        )

        for block in response.content:
            if block.type == "tool_use":
                return json.dumps(block.input)

        raise AiProviderError(
            "Anthropic response contained no tool_use block despite forced tool_choice."
        )
