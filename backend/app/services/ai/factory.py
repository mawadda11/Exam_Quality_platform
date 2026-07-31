"""Settings-based AI provider construction."""

from __future__ import annotations

from typing import Any, cast

from app.core.config import Settings
from app.services.ai.fake_provider import FakeAiProvider
from app.services.ai.local_provider import LocalSemanticProvider
from app.services.ai.provider import AiProvider

# Kept as a patchable module attribute for focused factory tests. The real
# adapter is imported lazily so development/test installations that use the
# local or fake provider do not require the external SDK at import time.
AnthropicAiProvider: Any = None
OllamaProvider: Any = None


class AiProviderConfigurationError(RuntimeError):
    """Invalid provider configuration is an infrastructure failure."""


def build_ai_provider(settings: Settings) -> AiProvider:
    provider = settings.ai_provider.strip().casefold()
    environment = settings.app_env.strip().casefold()
    if provider == "fake":
        if environment == "production":
            raise AiProviderConfigurationError(
                "The fake AI provider is not permitted in production."
            )
        return FakeAiProvider(model=settings.ai_model)
    if provider == "local":
        if environment == "production":
            raise AiProviderConfigurationError(
                "The local semantic baseline is not permitted in production."
            )
        return LocalSemanticProvider(model=settings.ai_model)
    if provider == "anthropic":
        if not settings.ai_api_key.strip():
            raise AiProviderConfigurationError("AI_API_KEY is required when AI_PROVIDER=anthropic.")
        if not settings.ai_model.strip():
            raise AiProviderConfigurationError("AI_MODEL is required when AI_PROVIDER=anthropic.")
        provider_cls = AnthropicAiProvider
        if provider_cls is None:
            from app.services.ai.anthropic_provider import AnthropicAiProvider as provider_cls
        return cast(
            AiProvider,
            provider_cls(api_key=settings.ai_api_key, model=settings.ai_model),
        )
    if provider == "ollama":
        if not settings.ollama_base_url.strip():
            raise AiProviderConfigurationError(
                "OLLAMA_BASE_URL is required when AI_PROVIDER=ollama."
            )
        if not settings.ai_model.strip():
            raise AiProviderConfigurationError("AI_MODEL is required when AI_PROVIDER=ollama.")
        provider_cls = OllamaProvider
        if provider_cls is None:
            from app.services.ai.ollama_provider import OllamaProvider as provider_cls
        return cast(
            AiProvider,
            provider_cls(
                base_url=settings.ollama_base_url,
                model=settings.ai_model,
                timeout_seconds=settings.ollama_timeout_seconds,
            ),
        )
    raise AiProviderConfigurationError(f"Unsupported AI_PROVIDER: {settings.ai_provider!r}.")
