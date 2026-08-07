"""Per-analysis sticky AI failover.

Each new analysis starts at the primary Gemini model.  Once an availability
failure occurs, that analysis is pinned to the next lower tier for all
remaining AI work.  A later/new analysis starts from primary again.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from app.services.ai.provider import AiProvider, AiProviderError, AiRouteTier

RouteChanged = Callable[[AiRouteTier], None]


def _schema_for_provider(schema: dict[str, Any], provider: AiProvider) -> dict[str, Any]:
    """Rewrite provenance consts for the provider that actually serves a call."""

    routed = deepcopy(schema)
    properties = routed.get("properties")
    if not isinstance(properties, dict):
        return routed
    provider_schema = properties.get("provider")
    if isinstance(provider_schema, dict):
        provider_schema["const"] = provider.provider_name
        provider_schema.pop("enum", None)
    model_schema = properties.get("model")
    if isinstance(model_schema, dict):
        model_schema["const"] = provider.model_name
        model_schema.pop("enum", None)
    return routed


class StickyFailoverAiProvider:
    """AiProvider that downgrades only on genuine availability failures."""

    def __init__(
        self,
        *,
        primary: AiProvider,
        fallback: AiProvider,
        local: AiProvider,
        initial_tier: AiRouteTier = AiRouteTier.PRIMARY,
        on_route_changed: RouteChanged | None = None,
    ) -> None:
        self._providers: dict[AiRouteTier, AiProvider] = {
            AiRouteTier.PRIMARY: primary,
            AiRouteTier.FALLBACK: fallback,
            AiRouteTier.LOCAL: local,
        }
        self._active_tier = initial_tier
        self._on_route_changed = on_route_changed

    @property
    def active_tier(self) -> AiRouteTier:
        return self._active_tier

    @property
    def _active_provider(self) -> AiProvider:
        return self._providers[self._active_tier]

    @property
    def provider_name(self) -> str:
        return self._active_provider.provider_name

    @property
    def model_name(self) -> str:
        return self._active_provider.model_name

    def _downgrade(self) -> bool:
        if self._active_tier is AiRouteTier.PRIMARY:
            self._active_tier = AiRouteTier.FALLBACK
        elif self._active_tier is AiRouteTier.FALLBACK:
            self._active_tier = AiRouteTier.LOCAL
        else:
            return False
        if self._on_route_changed is not None:
            self._on_route_changed(self._active_tier)
        return True

    def generate_structured(self, *, system: str, prompt: str, schema: dict[str, Any]) -> str:
        while True:
            provider = self._active_provider
            try:
                return provider.generate_structured(
                    system=system,
                    prompt=prompt,
                    schema=_schema_for_provider(schema, provider),
                )
            except AiProviderError as exc:
                if not exc.is_availability_failure or not self._downgrade():
                    raise
