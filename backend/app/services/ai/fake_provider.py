"""Deterministic scripted AI provider for tests."""

from __future__ import annotations

import json
from collections import deque
from collections.abc import Sequence
from typing import Any

from app.services.ai.provider import AiProviderError


class FakeAiProvider:
    """Returns scripted outputs, or a conservative complete Not Verified response."""

    def __init__(
        self,
        *,
        model: str = "fake-semantic-v2",
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
            source_ids = [str(value) for value in envelope["required_source_evidence_ids"]]
            items = [
                {
                    "source_evidence_id": evidence_id,
                    "target_evidence_ids": [],
                    "status": "Not Verified",
                    "reasoning": (
                        "The scripted test provider does not make an academic semantic judgment."
                    ),
                }
                for evidence_id in source_ids
            ]
            return json.dumps(
                {
                    "rule_id": envelope["rule_id"],
                    "requirement_id": envelope["requirement_id"],
                    "status": "Not Verified",
                    "evidence_ids": source_ids,
                    "explanation": (
                        "The deterministic test provider returned a complete conservative result."
                    ),
                    "recommendation_id": None,
                    "items": items,
                    "provider": self.provider_name,
                    "model": self.model_name,
                    "prompt_template_version": envelope["prompt_template_version"],
                    "kb_version": envelope["kb_version"],
                }
            )
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise AiProviderError("Fake provider received an invalid prompt envelope.") from exc
