"""Settings-based AI provider construction."""

from __future__ import annotations

from app.core.config import Settings
from app.services.ai.anthropic_provider import AnthropicAiProvider
from app.services.ai.fake_provider import FakeAiProvider
from app.services.ai.provider import AiProvider


class AiProviderConfigurationError(RuntimeError):
    """Invalid provider configuration is an infrastructure failure."""


def build_ai_provider(settings: Settings) -> AiProvider:
    provider = settings.ai_provider.strip().casefold()
    if provider == "fake":
        if settings.app_env.strip().casefold() == "production":
            raise AiProviderConfigurationError(
                "The fake AI provider is not permitted in production."
            )
        return FakeAiProvider(model=settings.ai_model)
    if provider == "anthropic":
        if not settings.ai_api_key.strip():
            raise AiProviderConfigurationError("AI_API_KEY is required when AI_PROVIDER=anthropic.")
        if not settings.ai_model.strip():
            raise AiProviderConfigurationError("AI_MODEL is required when AI_PROVIDER=anthropic.")
        return AnthropicAiProvider(api_key=settings.ai_api_key, model=settings.ai_model)
    raise AiProviderConfigurationError(f"Unsupported AI_PROVIDER: {settings.ai_provider!r}.")
