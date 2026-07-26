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

Genuine infrastructure failures (network errors, auth failures, rate limits)
must propagate as exceptions, not be swallowed into a return value - the
existing pipeline exception-safety net (app.services.processing.runner)
already converts any uncaught exception into a safe processing failure, and
conflating that with an academic "Not Verified" conclusion would violate
CLAUDE.md's "Processing failures are not academic statuses."
"""

from __future__ import annotations

from typing import Any, Protocol


class AiProviderError(RuntimeError):
    """Provider integration failure; never an academic evaluation status."""


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
