"""OllamaProvider tests. Every test injects a fake ``http_client`` callable,
so nothing here contacts a real Ollama server or makes any network I/O -
matching the fake/local/Anthropic provider testing convention already used
in this suite. `test_no_default_http_client_is_ever_constructed` further
guards against any test in this module accidentally falling through to the
real transport.
"""

from __future__ import annotations

import io
import urllib.error
from typing import Any

import pytest

from app.services.ai.ollama_provider import OllamaProvider
from app.services.ai.provider import AiProviderError

_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"status": {"type": "string"}},
    "required": ["status"],
}


class _FakeHttpClient:
    def __init__(
        self,
        *,
        response: dict[str, Any] | None = None,
        exception: Exception | None = None,
    ) -> None:
        self._response = response
        self._exception = exception
        self.calls: list[dict[str, Any]] = []

    def __call__(self, url: str, payload: dict[str, Any], *, timeout: float) -> dict[str, Any]:
        self.calls.append({"url": url, "payload": payload, "timeout": timeout})
        if self._exception is not None:
            raise self._exception
        assert self._response is not None
        return self._response


def _provider(
    client: _FakeHttpClient,
    *,
    base_url: str = "http://localhost:11434",
    model: str = "qwen3.5:4b",
    timeout_seconds: int = 60,
) -> OllamaProvider:
    return OllamaProvider(
        base_url=base_url,
        model=model,
        timeout_seconds=timeout_seconds,
        http_client=client,
    )


def _response(content: str) -> dict[str, Any]:
    return {"message": {"role": "assistant", "content": content}}


class _SequencedFakeHttpClient:
    """Returns/raises one outcome per call, in order - used to simulate a
    grammar-compilation failure on the first request followed by a
    successful (or also-failing) fallback request. Every call is recorded,
    so tests can assert on each request's payload independently."""

    def __init__(self, outcomes: list[dict[str, Any] | Exception]) -> None:
        self._outcomes = list(outcomes)
        self.calls: list[dict[str, Any]] = []

    def __call__(self, url: str, payload: dict[str, Any], *, timeout: float) -> dict[str, Any]:
        self.calls.append({"url": url, "payload": payload, "timeout": timeout})
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _grammar_http_error(message: str = "failed to parse grammar: unexpected token") -> Exception:
    """A real urllib.error.HTTPError with a readable body, matching exactly
    what the real Ollama transport raises for this confirmed failure mode -
    not a hand-rolled stand-in, so these tests exercise the same
    HTTPError.read()-based classification path production code uses."""
    body = f'{{"error":"{message}"}}'.encode()
    return urllib.error.HTTPError(
        "http://localhost:11434/api/chat", 400, "Bad Request", None, io.BytesIO(body)
    )


def _non_grammar_http_400(message: str = "invalid request: model field is required") -> Exception:
    body = f'{{"error":"{message}"}}'.encode()
    return urllib.error.HTTPError(
        "http://localhost:11434/api/chat", 400, "Bad Request", None, io.BytesIO(body)
    )


def test_provider_name_and_model_name() -> None:
    provider = _provider(_FakeHttpClient(response=_response("{}")))
    assert provider.provider_name == "ollama"
    assert provider.model_name == "qwen3.5:4b"


def test_valid_structured_response_is_returned_as_is() -> None:
    payload = '{"status": "Satisfied"}'
    client = _FakeHttpClient(response=_response(payload))
    provider = _provider(client)

    result = provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert result == payload


def test_configured_url_and_model_are_used() -> None:
    client = _FakeHttpClient(response=_response("{}"))
    provider = _provider(client, base_url="http://localhost:11434", model="qwen3.5:4b")

    provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert len(client.calls) == 1
    assert client.calls[0]["url"] == "http://localhost:11434/api/chat"
    assert client.calls[0]["payload"]["model"] == "qwen3.5:4b"


def test_base_url_trailing_slash_does_not_produce_a_double_slash_path() -> None:
    client = _FakeHttpClient(response=_response("{}"))
    provider = _provider(client, base_url="http://localhost:11434/")

    provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert client.calls[0]["url"] == "http://localhost:11434/api/chat"


def test_configured_timeout_is_forwarded_to_the_http_client() -> None:
    client = _FakeHttpClient(response=_response("{}"))
    provider = _provider(client, timeout_seconds=45)

    provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert client.calls[0]["timeout"] == 45.0


def test_think_is_always_false() -> None:
    client = _FakeHttpClient(response=_response("{}"))
    provider = _provider(client)

    provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert client.calls[0]["payload"]["think"] is False


def test_stream_is_always_false() -> None:
    client = _FakeHttpClient(response=_response("{}"))
    provider = _provider(client)

    provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert client.calls[0]["payload"]["stream"] is False


def test_temperature_is_always_zero() -> None:
    client = _FakeHttpClient(response=_response("{}"))
    provider = _provider(client)

    provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert client.calls[0]["payload"]["options"] == {"temperature": 0}


def test_json_schema_is_passed_through_the_format_field_unchanged() -> None:
    client = _FakeHttpClient(response=_response("{}"))
    provider = _provider(client)

    provider.generate_structured(system="be concise", prompt="prompt", schema=_SCHEMA)

    payload = client.calls[0]["payload"]
    assert payload["format"] == _SCHEMA
    assert payload["messages"] == [
        {"role": "system", "content": "be concise"},
        {"role": "user", "content": "prompt"},
    ]


def test_malformed_json_text_is_still_returned_for_the_shared_validator_to_reject() -> None:
    """OllamaProvider does not itself parse/validate the model's JSON output -
    the shared semantic_validation schema (extra="forbid", strict) is the
    single authoritative rejection point for every provider, so malformed
    text is passed through unchanged rather than duplicated here."""
    client = _FakeHttpClient(response=_response("not valid json"))
    provider = _provider(client)

    result = provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert result == "not valid json"


@pytest.mark.parametrize(
    "message",
    [
        {"role": "assistant", "content": ""},
        {"role": "assistant", "content": "   "},
        {"role": "assistant"},
        {},
    ],
)
def test_empty_response_fails_safely(message: dict[str, Any]) -> None:
    client = _FakeHttpClient(response={"message": message})
    provider = _provider(client)

    with pytest.raises(AiProviderError, match="empty response"):
        provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"message": "not-a-dict"},
        {"message": None},
    ],
)
def test_malformed_response_envelope_fails_safely(response: dict[str, Any]) -> None:
    client = _FakeHttpClient(response=response)
    provider = _provider(client)

    with pytest.raises(AiProviderError):
        provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)


def test_thinking_content_is_never_read_or_returned() -> None:
    """think=false is always sent, and even if a response somehow still
    included a "thinking" field, it must never be read, stored, or
    returned - only message.content."""
    client = _FakeHttpClient(
        response={
            "message": {
                "role": "assistant",
                "content": '{"status": "Satisfied"}',
                "thinking": "private reasoning that must never surface",
            }
        }
    )
    provider = _provider(client)

    result = provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert result == '{"status": "Satisfied"}'
    assert "private reasoning" not in result


def test_timeout_fails_safely_without_leaking_details() -> None:
    client = _FakeHttpClient(exception=TimeoutError("read timed out"))
    provider = _provider(client)

    with pytest.raises(AiProviderError, match="timed out") as excinfo:
        provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert excinfo.value.__cause__ is None


def test_connection_failure_fails_safely() -> None:
    import urllib.error

    client = _FakeHttpClient(exception=urllib.error.URLError("connection refused"))
    provider = _provider(client)

    with pytest.raises(AiProviderError, match="connection failed") as excinfo:
        provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert excinfo.value.__cause__ is None


def test_unavailable_model_fails_safely() -> None:
    import urllib.error

    http_error = urllib.error.HTTPError(
        "http://localhost:11434/api/chat", 404, "Not Found", None, None
    )
    client = _FakeHttpClient(exception=http_error)
    provider = _provider(client)

    with pytest.raises(AiProviderError, match="HTTP 404") as excinfo:
        provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert excinfo.value.__cause__ is None


def test_generic_transport_exception_also_fails_safely() -> None:
    client = _FakeHttpClient(exception=ConnectionRefusedError("refused"))
    provider = _provider(client)

    with pytest.raises(AiProviderError) as excinfo:
        provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert excinfo.value.__cause__ is None


def test_omitting_http_client_wires_the_default_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every other test in this module injects a fake http_client and never
    touches the default transport, so real network I/O never happens in this
    suite. This test instead proves the *wiring* is correct - that omitting
    http_client really does fall back to _default_http_client - without ever
    opening a real socket, by replacing that one function with a fake."""
    calls: list[str] = []

    def _fake_default(url: str, payload: dict[str, Any], *, timeout: float) -> dict[str, Any]:
        calls.append(url)
        return _response('{"status": "Satisfied"}')

    monkeypatch.setattr("app.services.ai.ollama_provider._default_http_client", _fake_default)
    provider = OllamaProvider(base_url="http://localhost:11434", model="qwen3.5:4b")

    result = provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert result == '{"status": "Satisfied"}'
    assert calls == ["http://localhost:11434/api/chat"]


# --- Grammar-compilation compatibility fallback (Ollama 0.32.5 / qwen3.5:4b) ---
#
# Confirmed real failure: passing the full JSON Schema in `format` gets HTTP
# 400 "Failed to initialize samplers: failed to parse grammar." These tests
# use real urllib.error.HTTPError instances with a readable body (via
# _grammar_http_error/_non_grammar_http_400), exercising the exact same
# HTTPError.read()-based classification path the real transport uses -
# nothing here is a network call (no socket is ever opened; the HTTPError is
# constructed directly), matching this module's convention throughout.


def test_schema_request_succeeds_without_any_fallback() -> None:
    client = _SequencedFakeHttpClient([_response('{"status": "Satisfied"}')])
    provider = _provider(client)

    result = provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert result == '{"status": "Satisfied"}'
    assert len(client.calls) == 1
    assert client.calls[0]["payload"]["format"] == _SCHEMA


def test_exact_grammar_error_triggers_exactly_one_fallback_attempt() -> None:
    client = _SequencedFakeHttpClient([_grammar_http_error(), _response('{"status": "Satisfied"}')])
    provider = _provider(client)

    result = provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert result == '{"status": "Satisfied"}'
    assert len(client.calls) == 2


def test_grammar_error_variant_message_also_triggers_fallback() -> None:
    client = _SequencedFakeHttpClient(
        [
            _grammar_http_error("Failed to initialize samplers: bad grammar"),
            _response('{"status": "Satisfied"}'),
        ]
    )
    provider = _provider(client)

    result = provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert result == '{"status": "Satisfied"}'
    assert len(client.calls) == 2


def test_fallback_request_uses_format_json() -> None:
    client = _SequencedFakeHttpClient([_grammar_http_error(), _response('{"status": "Satisfied"}')])
    provider = _provider(client)

    provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert client.calls[0]["payload"]["format"] == _SCHEMA
    assert client.calls[1]["payload"]["format"] == "json"


def test_fallback_keeps_think_false() -> None:
    client = _SequencedFakeHttpClient([_grammar_http_error(), _response('{"status": "Satisfied"}')])
    provider = _provider(client)

    provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert client.calls[1]["payload"]["think"] is False


def test_fallback_keeps_stream_false() -> None:
    client = _SequencedFakeHttpClient([_grammar_http_error(), _response('{"status": "Satisfied"}')])
    provider = _provider(client)

    provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert client.calls[1]["payload"]["stream"] is False


def test_fallback_keeps_temperature_zero() -> None:
    client = _SequencedFakeHttpClient([_grammar_http_error(), _response('{"status": "Satisfied"}')])
    provider = _provider(client)

    provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert client.calls[1]["payload"]["options"] == {"temperature": 0}


def test_fallback_prompt_is_unchanged_and_system_contains_the_supplied_schema() -> None:
    client = _SequencedFakeHttpClient([_grammar_http_error(), _response('{"status": "Satisfied"}')])
    provider = _provider(client)

    provider.generate_structured(system="be concise", prompt="original prompt", schema=_SCHEMA)

    fallback_messages = client.calls[1]["payload"]["messages"]
    assert fallback_messages[1] == {"role": "user", "content": "original prompt"}
    fallback_system = fallback_messages[0]["content"]
    assert fallback_system.startswith("be concise")
    assert "JSON" in fallback_system
    assert "Markdown" in fallback_system
    # The compact-serialized schema (or at least its distinguishing content)
    # must actually be present, not just referenced.
    assert '"status"' in fallback_system
    assert "required" in fallback_system


def test_raw_http_error_body_never_appears_in_the_raised_exception() -> None:
    secret_marker = "internal-trace-id-should-never-leak-93f7a2"
    # The fallback attempt itself also fails (a different, non-grammar HTTP
    # 400 this time), so its raw body - which also carries the marker - is
    # what actually reaches the raised exception's message, if anything did.
    client = _SequencedFakeHttpClient(
        [
            _grammar_http_error(f"failed to parse grammar ({secret_marker})"),
            _non_grammar_http_400(f"unexpected internal detail {secret_marker}"),
        ]
    )
    provider = _provider(client)

    with pytest.raises(AiProviderError) as excinfo:
        provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert secret_marker not in str(excinfo.value)
    assert excinfo.value.__cause__ is None
    # Also confirm nothing about the exception's own attributes carries it.
    assert secret_marker not in repr(excinfo.value)


def test_unrelated_http_400_does_not_trigger_a_fallback() -> None:
    client = _SequencedFakeHttpClient([_non_grammar_http_400()])
    provider = _provider(client)

    with pytest.raises(AiProviderError, match="HTTP 400") as excinfo:
        provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert len(client.calls) == 1
    assert excinfo.value.__cause__ is None


@pytest.mark.parametrize("status_code", [404, 500])
def test_http_404_and_500_do_not_trigger_a_fallback(status_code: int) -> None:
    http_error = urllib.error.HTTPError(
        "http://localhost:11434/api/chat", status_code, "Error", None, None
    )
    client = _SequencedFakeHttpClient([http_error])
    provider = _provider(client)

    with pytest.raises(AiProviderError, match=f"HTTP {status_code}"):
        provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert len(client.calls) == 1


def test_timeout_does_not_trigger_a_fallback() -> None:
    client = _SequencedFakeHttpClient([TimeoutError("read timed out")])
    provider = _provider(client)

    with pytest.raises(AiProviderError, match="timed out"):
        provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert len(client.calls) == 1


def test_connection_failure_does_not_trigger_a_fallback() -> None:
    client = _SequencedFakeHttpClient([urllib.error.URLError("connection refused")])
    provider = _provider(client)

    with pytest.raises(AiProviderError, match="connection failed"):
        provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert len(client.calls) == 1


def test_fallback_response_content_is_returned_exactly() -> None:
    payload = '{"status": "Partially Satisfied"}'
    client = _SequencedFakeHttpClient([_grammar_http_error(), _response(payload)])
    provider = _provider(client)

    result = provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert result == payload


def test_malformed_fallback_output_is_still_returned_for_the_shared_validator_to_reject() -> None:
    """OllamaProvider never parses/validates the fallback attempt's output
    either - malformed JSON-mode text is passed through unchanged, exactly
    like the primary attempt, for app.services.rules.semantic_validation to
    reject."""
    client = _SequencedFakeHttpClient([_grammar_http_error(), _response("not valid json")])
    provider = _provider(client)

    result = provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert result == "not valid json"


def test_second_grammar_failure_on_the_fallback_itself_is_not_retried_again() -> None:
    client = _SequencedFakeHttpClient([_grammar_http_error(), _grammar_http_error()])
    provider = _provider(client)

    with pytest.raises(AiProviderError) as excinfo:
        provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    # Exactly two attempts total (primary + one fallback) - never a third.
    assert len(client.calls) == 2
    assert excinfo.value.__cause__ is None


def test_no_thinking_content_is_read_from_the_fallback_response() -> None:
    client = _SequencedFakeHttpClient(
        [
            _grammar_http_error(),
            {
                "message": {
                    "role": "assistant",
                    "content": '{"status": "Satisfied"}',
                    "thinking": "private reasoning that must never surface",
                }
            },
        ]
    )
    provider = _provider(client)

    result = provider.generate_structured(system="sys", prompt="prompt", schema=_SCHEMA)

    assert result == '{"status": "Satisfied"}'
    assert "private reasoning" not in result
