from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.domain import ProcessingStage
from app.db.session import session_scope
from app.models.analysis import Analysis
from app.models.processing_event import ProcessingEvent
from app.services.processing.stages import (
    POST_CONFIRMATION_STAGES,
    PRE_REVIEW_STAGES,
    STAGE_HANDLERS,
    run_materializing_review,
)

logger = logging.getLogger(__name__)

# Never expose exception details to the client or persist them - only this
# fixed, generic message. Full details go to the server-side log only.
SAFE_FAILURE_MESSAGE = "Processing failed due to an internal error. Please try again later."

STAGE_SUCCESS_MESSAGES: dict[ProcessingStage, str] = {
    ProcessingStage.RETRIEVING_KNOWLEDGE: (
        "The versioned knowledge base is ready for semantic retrieval."
    ),
    ProcessingStage.APPLYING_RULES: ("Deterministic and approved semantic rules were applied."),
}

REVIEW_READY_MESSAGE = "Extraction is ready for review."
COMPLETED_MESSAGE = "Analysis completed successfully."


def _transition(
    session: Session, analysis: Analysis, stage: ProcessingStage, message: str | None = None
) -> None:
    analysis.state = stage
    session.add(ProcessingEvent(analysis_id=analysis.id, stage=stage, message=message))
    session.commit()


def run_analysis_pipeline(analysis_id: UUID) -> None:
    """Background job entry point. Opens its own DB session - the request's
    session is already closed by the time a background task runs."""
    settings = get_settings()
    with session_scope() as session:
        analysis = session.execute(
            select(Analysis).where(Analysis.id == analysis_id)
        ).scalar_one_or_none()
        if analysis is None:
            logger.error("Analysis %s not found when starting the pipeline.", analysis_id)
            return
        if analysis.state not in (ProcessingStage.QUEUED, ProcessingStage.VALIDATING):
            logger.warning(
                "Analysis %s is already in state %s; duplicate pipeline execution ignored.",
                analysis_id,
                analysis.state.value,
            )
            return

        try:
            for stage in PRE_REVIEW_STAGES:
                STAGE_HANDLERS[stage](analysis, session, settings)
                _transition(
                    session,
                    analysis,
                    stage,
                    message=STAGE_SUCCESS_MESSAGES.get(stage),
                )
            run_materializing_review(analysis, session, settings)
            _transition(
                session,
                analysis,
                ProcessingStage.REVIEW_READY,
                message=REVIEW_READY_MESSAGE,
            )
        except Exception:
            logger.exception("Processing failed for analysis %s", analysis_id)
            # Discard any uncommitted rows from the failed stage before
            # recording the safe failure transition; never commit partial
            # semantic output merely because failure handling itself commits.
            session.rollback()
            session.refresh(analysis)
            _transition(session, analysis, ProcessingStage.FAILED, message=SAFE_FAILURE_MESSAGE)


def run_post_confirmation_pipeline(analysis_id: UUID, confirmed_review_id: UUID) -> None:
    """Continue an exactly confirmed review through downstream processing.

    The confirmation route atomically claims BUILDING_EVIDENCE before scheduling this worker.
    Passing the exact revision identifier prevents a delayed or duplicated task from processing a
    different confirmation boundary.
    """
    settings = get_settings()
    with session_scope() as session:
        analysis = session.execute(
            select(Analysis).where(Analysis.id == analysis_id)
        ).scalar_one_or_none()
        if analysis is None:
            logger.error(
                "Analysis %s not found when continuing the confirmed pipeline.", analysis_id
            )
            return
        if (
            analysis.state != ProcessingStage.BUILDING_EVIDENCE
            or analysis.confirmed_review_id != confirmed_review_id
        ):
            logger.warning(
                "Analysis %s is not at the requested confirmed continuation boundary; "
                "duplicate pipeline execution ignored.",
                analysis_id,
            )
            return

        try:
            for stage in POST_CONFIRMATION_STAGES:
                STAGE_HANDLERS[stage](analysis, session, settings)
                # Confirmation already claimed BUILDING_EVIDENCE and recorded its event.
                # Do not duplicate that audit event when the continuation worker starts.
                if stage == ProcessingStage.BUILDING_EVIDENCE:
                    continue
                _transition(
                    session,
                    analysis,
                    stage,
                    message=STAGE_SUCCESS_MESSAGES.get(stage),
                )
            _transition(
                session,
                analysis,
                ProcessingStage.COMPLETED,
                message=COMPLETED_MESSAGE,
            )
        except Exception:
            logger.exception("Post-confirmation processing failed for analysis %s", analysis_id)
            session.rollback()
            session.refresh(analysis)
            _transition(session, analysis, ProcessingStage.FAILED, message=SAFE_FAILURE_MESSAGE)
