"""Deterministic AI provider for tests and safe local development."""

from __future__ import annotations

import json
from collections import deque
from collections.abc import Sequence
from typing import Any

from app.services.ai.anthropic_provider import AiProviderError


class FakeAiProvider:
    """Returns scripted outputs, or a conservative Not Verified response.

    The default response is derived only from trusted prompt-envelope fields
    created by the application. It never attempts a semantic conclusion and
    never performs network I/O.
    """

    def __init__(
        self,
        *,
        model: str = "fake-semantic-v1",
        responses: Sequence[str | Exception] = (),
    ) -> None:
        self._model = model
        self._responses: deque[str | Exception] = deque(responses)
        self.calls: list[dict[str, object]] = []

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def model_name(self) -> str:
        return self._model

    def generate_structured(self, *, system: str, prompt: str, schema: dict[str, Any]) -> str:
        self.calls.append({"system": system, "prompt": prompt, "schema": schema})
        if self._responses:
            response = self._responses.popleft()
            if isinstance(response, Exception):
                raise response
            return response

        try:
            envelope = json.loads(prompt)
            evidence_ids = [item["id"] for item in envelope.get("evidence", [])]
            return json.dumps(
                {
                    "rule_id": envelope["rule_id"],
                    "requirement_id": envelope["requirement_id"],
                    "status": "Not Verified",
                    "confidence": 0.0,
                    "evidence_ids": evidence_ids,
                    "explanation": (
                        "The deterministic local test provider does not make an academic "
                        "semantic judgment."
                    ),
                    "recommendation_id": None,
                    "provider": self.provider_name,
                    "model": self.model_name,
                    "prompt_template_version": envelope["prompt_template_version"],
                    "kb_version": envelope["kb_version"],
                }
            )
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise AiProviderError("Fake provider received an invalid prompt envelope.") from exc
