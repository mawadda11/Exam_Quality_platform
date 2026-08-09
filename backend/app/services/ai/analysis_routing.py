"""Persistence and construction for per-analysis sticky AI routing."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.domain import ProcessingStage
from app.models.processing_event import ProcessingEvent
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.local_provider import LocalSemanticProvider
from app.services.ai.provider import AiProvider, AiRouteTier
from app.services.ai.sticky_failover import StickyFailoverAiProvider

_ROUTE_MARKERS = {
    AiRouteTier.FALLBACK: "__AI_ROUTE__:gemini_fallback",
    AiRouteTier.LOCAL: "__AI_ROUTE__:local_fallback",
}
_ROUTE_BY_MARKER = {value: key for key, value in _ROUTE_MARKERS.items()}


def analysis_ai_route(session: Session, analysis_id: UUID) -> AiRouteTier:
    """Return the lowest sticky tier ever selected for this analysis."""

    markers = set(
        session.execute(
            select(ProcessingEvent.message).where(
                ProcessingEvent.analysis_id == analysis_id,
                ProcessingEvent.message.in_(tuple(_ROUTE_BY_MARKER)),
            )
        ).scalars()
    )
    if _ROUTE_MARKERS[AiRouteTier.LOCAL] in markers:
        return AiRouteTier.LOCAL
    if _ROUTE_MARKERS[AiRouteTier.FALLBACK] in markers:
        return AiRouteTier.FALLBACK
    return AiRouteTier.PRIMARY


def record_analysis_ai_route(
    session: Session,
    *,
    analysis_id: UUID,
    stage: ProcessingStage,
    tier: AiRouteTier,
) -> None:
    """Append one hidden audit marker when an analysis downgrades AI tier.

    The marker is stored as an internal event message with no ``error_code`` or
    failed stage, so it cannot be mistaken for a processing failure.
    """

    if tier is AiRouteTier.PRIMARY:
        return
    current = analysis_ai_route(session, analysis_id)
    rank = {
        AiRouteTier.PRIMARY: 0,
        AiRouteTier.FALLBACK: 1,
        AiRouteTier.LOCAL: 2,
    }
    if rank[tier] <= rank[current]:
        return
    session.add(
        ProcessingEvent(
            analysis_id=analysis_id,
            stage=stage,
            message=_ROUTE_MARKERS[tier],
            failed_stage=None,
            error_code=None,
            retryable=False,
        )
    )


def build_analysis_semantic_provider(
    settings: Settings,
    session: Session,
    *,
    analysis_id: UUID,
    stage: ProcessingStage,
) -> AiProvider | None:
    """Build the Gemini→Gemini fallback→local chain for one analysis.

    ``None`` means the configured provider is not Gemini or failover is disabled,
    so the caller should keep using its ordinary configured runtime provider.
    """

    if not settings.ai_failover_enabled:
        return None
    if settings.ai_provider.strip().casefold() != "gemini":
        return None

    api_key = settings.gemini_api_key.get_secret_value()
    primary = GeminiProvider(api_key=api_key, model=settings.ai_model)
    fallback = GeminiProvider(api_key=api_key, model=settings.gemini_fallback_model)
    local = LocalSemanticProvider(model=settings.ai_local_fallback_model)

    return StickyFailoverAiProvider(
        primary=primary,
        fallback=fallback,
        local=local,
        initial_tier=analysis_ai_route(session, analysis_id),
        on_route_changed=lambda tier: record_analysis_ai_route(
            session,
            analysis_id=analysis_id,
            stage=stage,
            tier=tier,
        ),
    )
