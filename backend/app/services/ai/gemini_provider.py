"""Optional Gemini AiProvider adapter using the official ``google-genai`` SDK
(``google-generativeai`` is the deprecated legacy SDK and must never be
used). Mirrors the established provider convention (docs/RAG_AND_AI_DESIGN.md
"the provider factory also supports the Anthropic, Ollama, and Gemini
adapters for optional manual use"): evaluators depend only on the
AiProvider interface, so no Gemini-specific logic belongs outside this
module, and Gemini may only interpret already-governed relationships within
the same validated, strictly-schema'd contract as every other provider.

Uses Gemini's native structured-output mechanism
(``response_mime_type="application/json"`` plus ``response_json_schema``,
which receives a transport-compatible projection of the exact governed JSON
Schema dict `generate_structured` receives) rather than prompting for JSON and hoping - but
per app.services.ai.provider's contract this is still only a best-effort
nudge; app.services.rules.semantic_validation independently and strictly
validates whatever text comes back, exactly as it does for every other
provider. This module never parses or judges the model's JSON content
itself, and deliberately never sends ``temperature``, ``top_p``, ``top_k``,
or ``candidate_count`` - governed deterministic scoring/aggregation must
never be perturbed by, or made to depend on, sampling configuration.

Only ``system``/``prompt``/``schema`` - the governed evidence text and rule
schema the existing semantic pipeline already prepared - are ever sent.
Nothing here reads or transmits uploaded PDF bytes; the pipeline itself has
no raw PDF bytes available at the semantic-evaluation stage, only already-
extracted evidence text (see app.services.rules.semantic_evaluators).

Error handling mirrors AnthropicAiProvider/OllamaProvider: every failure is
translated into a *fixed*, sanitized ``AiProviderError`` message with the
original exception explicitly not chained (``from None``) and without
interpolating the API key, prompt, document text, or raw response/error
body - so nothing from the transport or SDK layer ever reaches
``logger.exception()`` in the pipeline's failure handler. This adapter itself performs no
automatic fallback; the per-analysis routing layer may wrap it and fail over
only for sanitized availability failures.
"""

from __future__ import annotations

from typing import Any, Protocol

import httpx

try:
    from google import genai
    from google.genai import errors, types
except ImportError:  # Local-only mode and automated tests must not require the SDK.
    genai = None  # type: ignore[assignment]

    class _UnavailableGoogleErrors:
        class APIError(Exception):
            def __init__(self, code: int = 500) -> None:
                super().__init__("Gemini SDK is unavailable.")
                self.code = code

    class _UnavailableGoogleTypes:
        class GenerateContentConfig:
            def __init__(self, **kwargs: Any) -> None:
                for key, value in kwargs.items():
                    setattr(self, key, value)

    errors = _UnavailableGoogleErrors()  # type: ignore[assignment]
    types = _UnavailableGoogleTypes()  # type: ignore[assignment]

from app.services.ai.gemini_schema import normalize_gemini_json_schema
from app.services.ai.provider import AiFailureKind, AiProviderError


class _GenerateContentResponse(Protocol):
    @property
    def text(self) -> str | None: ...


class _ModelsClient(Protocol):
    def generate_content(
        self, *, model: str, contents: str, config: Any
    ) -> _GenerateContentResponse: ...


class _GenaiClient(Protocol):
    @property
    def models(self) -> _ModelsClient: ...


def _default_client(api_key: str) -> _GenaiClient:
    if genai is None:
        raise AiProviderError(
            "Gemini SDK is unavailable; install the optional google-genai dependency."
        )
    return genai.Client(api_key=api_key)


class GeminiProvider:
    """AiProvider backed by the official ``google-genai`` SDK.

    ``client`` is injectable so tests exercise this class against a plain
    fake object implementing the minimal ``_GenaiClient`` surface, instead
    of patching internals of the real SDK or requiring network access. No
    test in this codebase may construct the default client against a real
    network address.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        client: _GenaiClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._client = client

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model

    def _client_instance(self) -> _GenaiClient:
        if self._client is None:
            try:
                self._client = _default_client(self._api_key)
            except Exception as exc:
                raise AiProviderError(
                    f"Gemini client could not be constructed ({exc.__class__.__name__})."
                ) from None
        return self._client

    def generate_structured(self, *, system: str, prompt: str, schema: dict[str, Any]) -> str:
        client = self._client_instance()
        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_json_schema=normalize_gemini_json_schema(schema),
        )
        try:
            response = client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=config,
            )
        except errors.APIError as exc:
            raise _sanitized_api_error(exc.code) from None
        except (TimeoutError, httpx.TimeoutException):
            raise AiProviderError(
                "Gemini request timed out.", kind=AiFailureKind.AVAILABILITY
            ) from None
        except (OSError, httpx.TransportError):
            # Covers connection and HTTP transport/protocol failures (DNS,
            # refused, unreachable, dropped/invalid remote protocol).  The
            # google-genai SDK uses httpx underneath, whose RemoteProtocolError
            # is a TransportError rather than an OSError.  These are
            # availability failures and must activate per-analysis failover.
            raise AiProviderError(
                "Gemini connection failed; confirm network access to the Gemini API.",
                kind=AiFailureKind.AVAILABILITY,
            ) from None
        except Exception as exc:
            raise AiProviderError(
                f"Gemini request failed unexpectedly ({exc.__class__.__name__})."
            ) from None

        try:
            text = response.text
        except Exception:
            raise AiProviderError("Gemini returned an unexpected response shape.") from None

        if not isinstance(text, str) or not text.strip():
            raise AiProviderError("Gemini returned an empty response.")
        return text


def _sanitized_api_error(status_code: int) -> AiProviderError:
    """Fixed, sanitized messages only - never the SDK's own error body/
    message text (which could echo request details)."""
    if status_code in (401, 403):
        return AiProviderError(
            "Gemini authentication failed; verify GEMINI_API_KEY.",
            kind=AiFailureKind.AUTHENTICATION,
        )
    if status_code == 429:
        return AiProviderError(
            "Gemini quota or rate limit exceeded.",
            kind=AiFailureKind.AVAILABILITY,
        )
    if status_code == 404:
        return AiProviderError(
            "Gemini request failed: the configured model may be unavailable (HTTP 404).",
            kind=AiFailureKind.CONFIGURATION,
        )
    if status_code in (500, 502, 503, 504):
        return AiProviderError(
            f"Gemini API request failed (HTTP {status_code}).",
            kind=AiFailureKind.AVAILABILITY,
        )
    return AiProviderError(
        f"Gemini API request failed (HTTP {status_code}).",
        kind=AiFailureKind.UNEXPECTED,
    )
