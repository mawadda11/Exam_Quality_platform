from __future__ import annotations

import pytest

from app.core.config import Settings
from app.services.ai.factory import AiProviderConfigurationError, build_ai_provider
from app.services.ai.fake_provider import FakeAiProvider
from app.services.knowledge_base.factory import (
    VectorStoreConfigurationError,
    build_vector_store,
)
from app.services.knowledge_base.vector_store import InMemoryVectorStore


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "secret_key": "test-secret-key-not-for-production",
        "database_url": "sqlite:///:memory:",
        "ai_provider": "fake",
        "ai_model": "fake-semantic-v1",
        "vector_store_provider": "memory",
    }
    values.update(overrides)
    return Settings(**values)


def test_fake_provider_is_selected_without_network_io() -> None:
    provider = build_ai_provider(_settings())
    assert isinstance(provider, FakeAiProvider)
    assert provider.provider_name == "fake"
    assert provider.model_name == "fake-semantic-v1"


def test_fake_provider_is_rejected_in_production() -> None:
    with pytest.raises(AiProviderConfigurationError, match="not permitted"):
        build_ai_provider(_settings(app_env="production"))


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"ai_provider": "unsupported"}, "Unsupported AI_PROVIDER"),
        ({"ai_provider": "anthropic", "ai_api_key": ""}, "AI_API_KEY"),
        (
            {"ai_provider": "anthropic", "ai_api_key": "test-key", "ai_model": " "},
            "AI_MODEL",
        ),
    ],
)
def test_invalid_provider_configuration_is_an_infrastructure_error(
    overrides: dict[str, object], message: str
) -> None:
    with pytest.raises(AiProviderConfigurationError, match=message):
        build_ai_provider(_settings(**overrides))


def test_anthropic_adapter_is_constructed_through_the_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str] = {}

    class StubProvider:
        provider_name = "anthropic"
        model_name = "model"

        def __init__(self, *, api_key: str, model: str) -> None:
            captured.update(api_key=api_key, model=model)

        def generate_structured(
            self, *, system: str, prompt: str, schema: dict[str, object]
        ) -> str:
            raise AssertionError("No live provider call is allowed in this test.")

    monkeypatch.setattr(
        "app.services.ai.factory.AnthropicAiProvider",
        StubProvider,
    )
    provider = build_ai_provider(
        _settings(
            ai_provider="anthropic",
            ai_api_key="test-key",
            ai_model="claude-test",
        )
    )
    assert provider.provider_name == "anthropic"
    assert captured == {"api_key": "test-key", "model": "claude-test"}


def test_memory_vector_store_is_selected_for_tests() -> None:
    assert isinstance(build_vector_store(_settings()), InMemoryVectorStore)


def test_unknown_vector_store_configuration_fails_explicitly() -> None:
    with pytest.raises(VectorStoreConfigurationError, match="Unsupported"):
        build_vector_store(_settings(vector_store_provider="unknown"))
