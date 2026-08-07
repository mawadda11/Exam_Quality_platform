"""AI provider adapter: a provider-neutral interface (per docs/ARCHITECTURE.md's
"AI provider adapter: structured semantic evaluation" and "External providers
hidden behind interfaces for testing and replacement").

The Protocol deliberately returns a plain string, not a parsed/validated
object: different providers have different native mechanisms for structured
output (tool-use, JSON mode, or plain-text prompting), and pushing parsing
here would leak provider-specific detail into every evaluator. Every caller
must independently validate whatever comes back (app.services.rules.
semantic_validation) - CLAUDE.md's "treat model output as untrusted input"
applies regardless of which provider produced it or what it claims to
guarantee.

Provider failures remain infrastructure concerns rather than academic
statuses. A higher-level per-analysis router may transparently retry a request
on a lower-priority provider only when ``AiFailureKind.AVAILABILITY`` is
reported. Authentication, configuration, response-validation, and programming
failures are never hidden by failover.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol


class AiFailureKind(StrEnum):
    """Stable machine-readable provider failure categories."""

    AVAILABILITY = "availability"
    AUTHENTICATION = "authentication"
    CONFIGURATION = "configuration"
    RESPONSE = "response"
    UNEXPECTED = "unexpected"


class AiRouteTier(StrEnum):
    """Sticky provider tier selected for one analysis."""

    PRIMARY = "primary"
    FALLBACK = "fallback"
    LOCAL = "local"


class AiProviderError(RuntimeError):
    """Provider integration failure; never an academic evaluation status."""

    def __init__(
        self,
        message: str,
        *,
        kind: AiFailureKind = AiFailureKind.UNEXPECTED,
    ) -> None:
        super().__init__(message)
        self.kind = kind

    @property
    def is_availability_failure(self) -> bool:
        return self.kind is AiFailureKind.AVAILABILITY


class AiProvider(Protocol):
    @property
    def provider_name(self) -> str: ...

    @property
    def model_name(self) -> str: ...

    def generate_structured(self, *, system: str, prompt: str, schema: dict[str, Any]) -> str:
        """Returns a JSON string intended to conform to `schema`. Providers
        may use whatever native mechanism improves the odds of that being
        true (e.g. tool-use), but this is a best-effort nudge, not a
        guarantee - callers must still validate independently."""
        ...
