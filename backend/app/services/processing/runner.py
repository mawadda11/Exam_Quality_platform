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
from app.services.processing.stages import STAGE_HANDLERS, WORK_STAGES

logger = logging.getLogger(__name__)

# Never expose exception details to the client or persist them - only this
# fixed, generic message. Full details go to the server-side log only.
SAFE_FAILURE_MESSAGE = "Processing failed due to an internal error. Please try again later."


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

        try:
            for stage in WORK_STAGES:
                STAGE_HANDLERS[stage](analysis, session, settings)
                _transition(session, analysis, stage)
            _transition(session, analysis, ProcessingStage.COMPLETED)
        except Exception:
            logger.exception("Processing failed for analysis %s", analysis_id)
            _transition(session, analysis, ProcessingStage.FAILED, message=SAFE_FAILURE_MESSAGE)
