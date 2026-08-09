"""Optional, fully local Ollama AiProvider adapter (docs/RAG_AND_AI_DESIGN.md:
"the provider factory also supports the Anthropic and Ollama adapters for
optional manual use"; evaluators depend only on the provider interface, so no
Ollama-specific logic belongs outside this module).

Talks to a locally reachable Ollama server's HTTP API (``/api/chat``) with
``stream=false``, ``think=false``, ``options.temperature=0``, and the
existing JSON Schema passed straight through the ``format`` field - the same
schema every other provider receives, so this stays a thin transport adapter
rather than a second place that understands the semantic contract.
app.services.rules.semantic_validation independently and strictly validates
whatever text comes back, exactly as it does for every other provider; this
module never parses or judges the model's JSON content itself.

``think=false`` means Ollama should not emit a separate reasoning/thinking
field at all, and this module never reads one even if a future model or
Ollama version includes it regardless - only ``message.content`` is ever
read, matching CLAUDE.md's "never request, persist, or display private model
chain-of-thought."

Error handling mirrors AnthropicAiProvider/the established provider
convention: a response with no usable content is not "malformed JSON" the
shared validator can retry - it is raised directly as AiProviderError
(uncaught by the evaluator's retry loop, which only retries schema-validation
failures). Connection failures, timeouts, and non-2xx HTTP responses (e.g. an
unpulled/unavailable model) are re-raised as a new, fixed-message
AiProviderError with the original exception explicitly not chained (``from
None``) and without interpolating the raw response body, so nothing from the
transport layer - which could echo request/response internals - ever reaches
``logger.exception()`` in the pipeline's failure handler. This translation
happens in ``generate_structured`` itself (around whichever ``http_client`` is
in use), not only in the default transport, so an injected test client's
exceptions are translated exactly the same way as the real one's.

Grammar-compilation compatibility fallback (Ollama 0.32.5 / qwen3.5:4b): some
Ollama/model combinations cannot compile a full JSON-Schema `format` payload
into their sampling grammar and reject the request with HTTP 400 ("Failed to
initialize samplers: failed to parse grammar"). This is a narrow, confirmed
transport-compatibility failure, not a semantic-validation concern, so it is
detected and handled entirely inside this module: on that *specific*
confirmed condition only, `generate_structured` retries exactly once with
`format="json"` (Ollama's simpler, non-grammar-compiled JSON mode) and the
same schema restated as text inside the system instruction instead. Every
other failure (timeout, connection failure, model unavailable, an unrelated
HTTP 400, HTTP 404/500, a malformed response envelope) is not retried here.
The fallback attempt's raw output still goes through the exact same shared
Pydantic/governance validation as the primary attempt - this module never
parses or judges it, and invalid JSON-mode output is rejected by
app.services.rules.semantic_validation and the evaluator's own bounded retry
loop exactly like any other malformed provider output. See
docs/RAG_AND_AI_DESIGN.md for the governance framing of this fallback.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Protocol

from app.services.ai.provider import AiProviderError

_CHAT_PATH = "/api/chat"

# Confirmed, sanitized Ollama error substrings for a grammar-compilation
# failure (observed with Ollama 0.32.5 / qwen3.5:4b). Matched case-
# insensitively against a bounded slice of the error body - see
# _is_grammar_compilation_failure. Deliberately narrow: matching anything
# broader risks silently masking a genuine schema/config problem behind a
# fallback instead of surfacing it.
_GRAMMAR_FAILURE_MARKERS = (
    "failed to parse grammar",
    "failed to initialize samplers",
)
# Bytes read from an HTTP 400 error body solely to classify the failure
# (never stored, logged, or included in any exception) - comfortably larger
# than Ollama's short JSON error payloads, but still bounded rather than an
# unbounded read of a potentially large response.
_ERROR_CLASSIFICATION_READ_LIMIT = 4096

_FALLBACK_INSTRUCTION_TEMPLATE = (
    "\n\nThe structured output mode for this request was not accepted by the "
    "model runtime, so you must instead respond with exactly one JSON object "
    "and nothing else: no Markdown code fences, no prose before or after the "
    "JSON, no explanation. The JSON object must conform exactly to this JSON "
    "Schema:\n{schema}"
)


class _OllamaGrammarCompilationError(Exception):
    """Internal-only signal that Ollama rejected the request with HTTP 400
    and a confirmed grammar-compilation failure message. Carries no response
    content - its existence is the only information it conveys. Caught
    exclusively inside generate_structured to trigger exactly one bounded
    fallback attempt; must never propagate out of this module or be logged."""


class _OllamaHttpClient(Protocol):
    def __call__(self, url: str, payload: dict[str, Any], *, timeout: float) -> dict[str, Any]: ...


def _default_http_client(url: str, payload: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    """Raw HTTP transport. Deliberately does not translate exceptions - that
    is OllamaProvider.generate_structured's job, so it applies uniformly
    whether this default client or an injected test client raises."""
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise AiProviderError("Ollama returned an unexpected response shape.")
    return parsed


def _is_grammar_compilation_failure(exc: urllib.error.HTTPError) -> bool:
    """Bounded, best-effort classification only. Reads at most
    _ERROR_CLASSIFICATION_READ_LIMIT bytes of the HTTP 400 error body solely
    to check for the two confirmed Ollama grammar-failure markers, then
    discards it - the checked text is never returned, logged, stored, or
    included in any exception raised by this module."""
    if exc.code != 400:
        return False
    try:
        body = exc.read(_ERROR_CLASSIFICATION_READ_LIMIT)
    except Exception:
        return False
    try:
        text = body.decode("utf-8", errors="replace").casefold()
    except Exception:
        return False
    return any(marker in text for marker in _GRAMMAR_FAILURE_MARKERS)


def _fallback_system_instruction(system: str, schema: dict[str, Any]) -> str:
    """The same rule-governed output schema every provider receives (never
    user document/exam/TP-153 content - see app.services.rules.
    semantic_evaluators' prompt assembly), restated compactly as text since
    format="json" mode does not accept a schema object. Not logged here or
    anywhere else in this module."""
    compact_schema = json.dumps(schema, separators=(",", ":"), sort_keys=True)
    return system + _FALLBACK_INSTRUCTION_TEMPLATE.format(schema=compact_schema)


class OllamaProvider:
    """AiProvider backed by a locally reachable Ollama server's HTTP API.

    ``http_client`` is injectable so tests exercise this class against a
    plain fake callable, instead of patching internals of the real HTTP
    stack or requiring a running Ollama server. No test in this codebase may
    construct the default client against a real network address.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: int = 60,
        http_client: _OllamaHttpClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._http_client = http_client or _default_http_client

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    def _build_payload(
        self, *, system: str, prompt: str, format_value: dict[str, Any] | str
    ) -> dict[str, Any]:
        return {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "think": False,
            "format": format_value,
            "options": {"temperature": 0},
        }

    def _send(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._http_client(
                f"{self._base_url}{_CHAT_PATH}",
                payload,
                timeout=float(self._timeout_seconds),
            )
        except AiProviderError:
            raise
        except _OllamaGrammarCompilationError:
            raise
        except TimeoutError:
            raise AiProviderError("Ollama request timed out.") from None
        except urllib.error.HTTPError as exc:
            if _is_grammar_compilation_failure(exc):
                raise _OllamaGrammarCompilationError() from None
            raise AiProviderError(f"Ollama request failed (HTTP {exc.code}).") from None
        except urllib.error.URLError:
            raise AiProviderError(
                "Ollama connection failed; confirm the Ollama server is running and reachable."
            ) from None
        except json.JSONDecodeError:
            raise AiProviderError("Ollama returned a response that was not valid JSON.") from None
        except Exception as exc:
            raise AiProviderError(
                f"Ollama request failed unexpectedly ({exc.__class__.__name__})."
            ) from None

    def generate_structured(self, *, system: str, prompt: str, schema: dict[str, Any]) -> str:
        payload = self._build_payload(system=system, prompt=prompt, format_value=schema)
        try:
            response = self._send(payload)
        except _OllamaGrammarCompilationError:
            # Exactly one bounded fallback: format="json" (Ollama's simpler
            # mode, not GBNF-grammar-compiled) plus the same schema restated
            # as text. stream/think/temperature are unchanged - only
            # `format` and `system` differ from the first request.
            fallback_payload = self._build_payload(
                system=_fallback_system_instruction(system, schema),
                prompt=prompt,
                format_value="json",
            )
            try:
                response = self._send(fallback_payload)
            except _OllamaGrammarCompilationError:
                # The one permitted fallback attempt also hit a grammar
                # failure (format="json" should not trigger this at all) -
                # never retried a second time; surfaced as an ordinary
                # provider failure instead.
                raise AiProviderError("Ollama rejected the fallback JSON-mode request.") from None

        message = response.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        # Deliberately not read: any "thinking"/"reasoning" field the server
        # might include. Only the final response content is ever inspected.
        if not isinstance(content, str) or not content.strip():
            raise AiProviderError("Ollama returned an empty response.")
        return content
