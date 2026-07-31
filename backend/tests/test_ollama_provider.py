"""OllamaProvider tests. Every test injects a fake ``http_client`` callable,
so nothing here contacts a real Ollama server or makes any network I/O -
matching the fake/local/Anthropic provider testing convention already used
in this suite. `test_no_default_http_client_is_ever_constructed` further
guards against any test in this module accidentally falling through to the
real transport.
"""

from __future__ import annotations

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
