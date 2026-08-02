from __future__ import annotations

from typing import Any

import pytest

from app.services.ai import gemini_provider as module
from app.services.ai.provider import AiProviderError


class FakeResponse:
    def __init__(self, text: str | None) -> None:
        self._text = text

    @property
    def text(self) -> str | None:
        return self._text


class BrokenResponse:
    @property
    def text(self) -> str:
        raise RuntimeError("broken response")


class FakeModels:
    def __init__(
        self,
        *,
        response: Any = None,
        exc: BaseException | None = None,
    ) -> None:
        self.response = response
        self.exc = exc
        self.calls: list[dict[str, Any]] = []

    def generate_content(
        self,
        *,
        model: str,
        contents: str,
        config: Any,
    ) -> Any:
        self.calls.append(
            {
                "model": model,
                "contents": contents,
                "config": config,
            }
        )
        if self.exc is not None:
            raise self.exc
        return self.response


class FakeClient:
    def __init__(self, models: FakeModels) -> None:
        self.models = models


def make_provider(
    *,
    response: Any = None,
    exc: BaseException | None = None,
) -> tuple[module.GeminiProvider, FakeModels]:
    models = FakeModels(response=response, exc=exc)
    provider = module.GeminiProvider(
        api_key="private-test-key",
        model="gemini-3.6-flash",
        client=FakeClient(models),
    )
    return provider, models


def test_provider_identity() -> None:
    provider, _ = make_provider(response=FakeResponse('{"ok":true}'))

    assert provider.provider_name == "gemini"
    assert provider.model_name == "gemini-3.6-flash"


def test_generate_structured_uses_exact_contract() -> None:
    schema = {
        "type": "object",
        "properties": {"ok": {"type": "boolean"}},
        "required": ["ok"],
        "additionalProperties": False,
    }
    provider, models = make_provider(response=FakeResponse('{"ok":true}'))

    result = provider.generate_structured(
        system="Return structured JSON.",
        prompt="Synthetic test.",
        schema=schema,
    )

    assert result == '{"ok":true}'
    assert len(models.calls) == 1

    call = models.calls[0]
    assert call["model"] == "gemini-3.6-flash"
    assert call["contents"] == "Synthetic test."

    config = call["config"]
    assert config.system_instruction == "Return structured JSON."
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema == schema

    assert getattr(config, "temperature", None) is None
    assert getattr(config, "top_p", None) is None
    assert getattr(config, "top_k", None) is None
    assert getattr(config, "candidate_count", None) is None


def test_returns_response_text_exactly() -> None:
    provider, _ = make_provider(response=FakeResponse('{"value":"accepted"}'))

    result = provider.generate_structured(
        system="System",
        prompt="Prompt",
        schema={"type": "object"},
    )

    assert result == '{"value":"accepted"}'


@pytest.mark.parametrize("text", [None, "", "   "])
def test_empty_response_fails_safely(text: str | None) -> None:
    provider, _ = make_provider(response=FakeResponse(text))

    with pytest.raises(AiProviderError, match="Gemini returned an empty response"):
        provider.generate_structured(
            system="System",
            prompt="Prompt",
            schema={"type": "object"},
        )


def test_unexpected_response_shape_fails_safely() -> None:
    provider, _ = make_provider(response=BrokenResponse())

    with pytest.raises(
        AiProviderError,
        match="Gemini returned an unexpected response shape",
    ):
        provider.generate_structured(
            system="System",
            prompt="Prompt",
            schema={"type": "object"},
        )


def test_timeout_is_sanitized() -> None:
    provider, _ = make_provider(exc=TimeoutError("private prompt text"))

    with pytest.raises(AiProviderError, match="Gemini request timed out") as caught:
        provider.generate_structured(
            system="System",
            prompt="Prompt",
            schema={"type": "object"},
        )

    assert "private prompt text" not in str(caught.value)


def test_network_failure_is_sanitized() -> None:
    provider, _ = make_provider(exc=OSError("private network detail"))

    with pytest.raises(AiProviderError, match="Gemini connection failed") as caught:
        provider.generate_structured(
            system="System",
            prompt="Prompt",
            schema={"type": "object"},
        )

    assert "private network detail" not in str(caught.value)


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (401, "Gemini authentication failed"),
        (403, "Gemini authentication failed"),
        (404, "configured model may be unavailable"),
        (429, "Gemini quota or rate limit exceeded"),
        (500, "Gemini API request failed"),
    ],
)
def test_api_errors_are_sanitized(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    expected: str,
) -> None:
    class FakeAPIError(Exception):
        def __init__(self, code: int) -> None:
            super().__init__("private-key private-prompt raw-provider-body")
            self.code = code

    monkeypatch.setattr(module.errors, "APIError", FakeAPIError)

    provider, _ = make_provider(exc=FakeAPIError(status_code))

    with pytest.raises(AiProviderError, match=expected) as caught:
        provider.generate_structured(
            system="System",
            prompt="Prompt",
            schema={"type": "object"},
        )

    message = str(caught.value)
    assert "private-key" not in message
    assert "private-prompt" not in message
    assert "raw-provider-body" not in message


def test_unexpected_failure_is_sanitized() -> None:
    provider, _ = make_provider(exc=ValueError("private document text"))

    with pytest.raises(AiProviderError, match="ValueError") as caught:
        provider.generate_structured(
            system="System",
            prompt="Prompt",
            schema={"type": "object"},
        )

    assert "private document text" not in str(caught.value)


def test_default_client_is_lazy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    models = FakeModels(response=FakeResponse('{"ok":true}'))

    def fake_default_client(api_key: str) -> FakeClient:
        calls.append(api_key)
        return FakeClient(models)

    monkeypatch.setattr(module, "_default_client", fake_default_client)

    provider = module.GeminiProvider(
        api_key="private-test-key",
        model="gemini-3.6-flash",
    )

    assert calls == []

    result = provider.generate_structured(
        system="System",
        prompt="Prompt",
        schema={"type": "object"},
    )

    assert result == '{"ok":true}'
    assert calls == ["private-test-key"]


def test_const_keywords_are_converted_to_single_value_enum() -> None:
    schema = {
        "type": "object",
        "properties": {
            "provider": {
                "type": "string",
                "const": "gemini",
            },
            "model": {
                "type": "string",
                "const": "gemini-3.6-flash",
            },
        },
        "required": ["provider", "model"],
        "additionalProperties": False,
    }
    provider, models = make_provider(
        response=FakeResponse('{"provider":"gemini","model":"gemini-3.6-flash"}')
    )

    provider.generate_structured(
        system="System",
        prompt="Prompt",
        schema=schema,
    )

    sent_schema = models.calls[0]["config"].response_json_schema

    assert sent_schema["properties"]["provider"] == {
        "type": "string",
        "enum": ["gemini"],
    }
    assert sent_schema["properties"]["model"] == {
        "type": "string",
        "enum": ["gemini-3.6-flash"],
    }

    # The authoritative input schema must remain unchanged.
    assert schema["properties"]["provider"]["const"] == "gemini"
    assert schema["properties"]["model"]["const"] == "gemini-3.6-flash"
    assert "enum" not in schema["properties"]["provider"]
