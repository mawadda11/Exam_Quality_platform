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
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Protocol

from app.services.ai.provider import AiProviderError

_CHAT_PATH = "/api/chat"


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

    def generate_structured(self, *, system: str, prompt: str, schema: dict[str, Any]) -> str:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "think": False,
            "format": schema,
            "options": {"temperature": 0},
        }
        try:
            response = self._http_client(
                f"{self._base_url}{_CHAT_PATH}",
                payload,
                timeout=float(self._timeout_seconds),
            )
        except AiProviderError:
            raise
        except TimeoutError:
            raise AiProviderError("Ollama request timed out.") from None
        except urllib.error.HTTPError as exc:
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

        message = response.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        # Deliberately not read: any "thinking"/"reasoning" field the server
        # might include. Only the final response content is ever inspected.
        if not isinstance(content, str) or not content.strip():
            raise AiProviderError("Ollama returned an empty response.")
        return content
