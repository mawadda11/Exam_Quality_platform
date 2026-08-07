from __future__ import annotations

import logging
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.domain import ProcessingStage, QuestionPreparationMode
from app.db.session import session_scope
from app.models.analysis import Analysis
from app.models.processing_event import ProcessingEvent
from app.services.extraction.preparation_mode import question_preparation_mode_for_analysis
from app.services.processing.stages import (
    POST_CONFIRMATION_STAGES,
    PRE_REVIEW_STAGES,
    STAGE_HANDLERS,
    run_extracting_exam,
    run_materializing_review,
)

logger = logging.getLogger(__name__)

SAFE_FAILURE_MESSAGES: dict[ProcessingStage, str] = {
    ProcessingStage.VALIDATING: (
        "The stored files could not be validated. Check that both PDFs are available, then retry."
    ),
    ProcessingStage.EXTRACTING_EXAM: (
        "The examination could not be extracted. Review the PDF and retry."
    ),
    ProcessingStage.EXTRACTING_TP153: (
        "The TP-153 Course Specification could not be extracted. Review the PDF and retry."
    ),
    ProcessingStage.BUILDING_EVIDENCE: (
        "The confirmed extraction could not be converted into analysis evidence. "
        "Retry the analysis."
    ),
    ProcessingStage.RETRIEVING_KNOWLEDGE: (
        "The controlled knowledge base could not be prepared. Retry the analysis."
    ),
    ProcessingStage.APPLYING_RULES: (
        "The governed evaluation could not be completed. Retry the analysis."
    ),
    ProcessingStage.GENERATING_REPORT: "The analysis could not be finalized. Retry the analysis.",
}

ERROR_CODES: dict[ProcessingStage, str] = {
    ProcessingStage.VALIDATING: "FILE_VALIDATION_FAILED",
    ProcessingStage.EXTRACTING_EXAM: "EXAM_EXTRACTION_FAILED",
    ProcessingStage.EXTRACTING_TP153: "TP153_EXTRACTION_FAILED",
    ProcessingStage.BUILDING_EVIDENCE: "EVIDENCE_BUILD_FAILED",
    ProcessingStage.RETRIEVING_KNOWLEDGE: "KNOWLEDGE_RETRIEVAL_FAILED",
    ProcessingStage.APPLYING_RULES: "RULE_EVALUATION_FAILED",
    ProcessingStage.GENERATING_REPORT: "FINALIZATION_FAILED",
}

STAGE_SUCCESS_MESSAGES: dict[ProcessingStage, str] = {
    ProcessingStage.VALIDATING: "The uploaded files were validated.",
    ProcessingStage.EXTRACTING_EXAM: "The examination was extracted.",
    ProcessingStage.EXTRACTING_TP153: "The Course Specification was extracted.",
    ProcessingStage.BUILDING_EVIDENCE: "The confirmed extraction was converted into evidence.",
    ProcessingStage.RETRIEVING_KNOWLEDGE: (
        "The versioned knowledge base is ready for semantic retrieval."
    ),
    ProcessingStage.APPLYING_RULES: "Deterministic and approved semantic rules were applied.",
    ProcessingStage.GENERATING_REPORT: "The analysis result was finalized.",
}

REVIEW_READY_MESSAGE = "Extraction is ready for review."
COMPLETED_MESSAGE = "Analysis completed successfully."


def _transition(
    session: Session,
    analysis: Analysis,
    stage: ProcessingStage,
    message: str | None = None,
    *,
    failed_stage: ProcessingStage | None = None,
    error_code: str | None = None,
    retryable: bool = False,
) -> None:
    analysis.state = stage
    session.add(
        ProcessingEvent(
            analysis_id=analysis.id,
            stage=stage,
            message=message,
            failed_stage=failed_stage,
            error_code=error_code,
            retryable=retryable,
        )
    )
    session.commit()


def _record_failure(
    session: Session,
    analysis: Analysis,
    analysis_id: UUID,
    failed_stage: ProcessingStage,
    *,
    context: str,
) -> None:
    logger.exception(
        "%s failed for analysis %s at stage %s",
        context,
        analysis_id,
        failed_stage.value,
    )
    session.rollback()
    session.refresh(analysis)
    _transition(
        session,
        analysis,
        ProcessingStage.FAILED,
        message=SAFE_FAILURE_MESSAGES[failed_stage],
        failed_stage=failed_stage,
        error_code=ERROR_CODES[failed_stage],
        retryable=True,
    )


def run_analysis_pipeline(
    analysis_id: UUID,
    preparation_mode: QuestionPreparationMode | None = None,
) -> None:
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

        effective_preparation_mode = (
            preparation_mode or question_preparation_mode_for_analysis(analysis)
        )

        current_stage = ProcessingStage.VALIDATING
        try:
            for current_stage in PRE_REVIEW_STAGES:
                handler = STAGE_HANDLERS[current_stage]
                if (
                    current_stage is ProcessingStage.EXTRACTING_EXAM
                    and handler is run_extracting_exam
                ):
                    run_extracting_exam(
                        analysis,
                        session,
                        settings,
                        preparation_mode=effective_preparation_mode,
                    )
                else:
                    handler(analysis, session, settings)
                _transition(
                    session,
                    analysis,
                    current_stage,
                    message=STAGE_SUCCESS_MESSAGES.get(current_stage),
                )
            run_materializing_review(analysis, session, settings)
            _transition(
                session,
                analysis,
                ProcessingStage.REVIEW_READY,
                message=REVIEW_READY_MESSAGE,
            )
        except Exception:
            _record_failure(
                session, analysis, analysis_id, current_stage, context="Initial processing"
            )


def run_post_confirmation_pipeline(analysis_id: UUID, confirmed_review_id: UUID) -> None:
    settings = get_settings()
    with session_scope() as session:
        analysis = session.execute(
            select(Analysis).where(Analysis.id == analysis_id)
        ).scalar_one_or_none()
        if analysis is None:
            logger.error(
                "Analysis %s not found when continuing the confirmed pipeline.",
                analysis_id,
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

        current_stage = ProcessingStage.BUILDING_EVIDENCE
        try:
            for current_stage in POST_CONFIRMATION_STAGES:
                STAGE_HANDLERS[current_stage](analysis, session, settings)
                if current_stage == ProcessingStage.BUILDING_EVIDENCE:
                    # Confirmation already recorded the BUILDING_EVIDENCE audit event,
                    # but the stage's writes still need their own durable boundary so
                    # a later-stage failure can safely resume without rebuilding or
                    # losing confirmed evidence.
                    session.commit()
                    continue
                _transition(
                    session,
                    analysis,
                    current_stage,
                    message=STAGE_SUCCESS_MESSAGES.get(current_stage),
                )
            _transition(
                session,
                analysis,
                ProcessingStage.COMPLETED,
                message=COMPLETED_MESSAGE,
            )
        except Exception:
            _record_failure(
                session,
                analysis,
                analysis_id,
                current_stage,
                context="Post-confirmation processing",
            )


def run_retry_pipeline(
    analysis_id: UUID,
    retry_from: ProcessingStage,
    confirmed_review_id: UUID | None,
) -> None:
    """Resume a failed pipeline from its durable failed-stage boundary.

    Each stage is transactionally committed only after it succeeds. The failed
    stage's partial writes are rolled back by the original worker, so resuming
    from that exact stage preserves completed work and avoids duplicate source
    records.
    """

    settings = get_settings()
    with session_scope() as session:
        analysis = session.execute(
            select(Analysis).where(Analysis.id == analysis_id)
        ).scalar_one_or_none()
        if analysis is None:
            logger.error("Analysis %s not found when retrying the pipeline.", analysis_id)
            return
        if analysis.state != retry_from:
            logger.warning(
                "Analysis %s is no longer at retry boundary %s; duplicate retry ignored.",
                analysis_id,
                retry_from.value,
            )
            return

        if retry_from in PRE_REVIEW_STAGES:
            start_index = PRE_REVIEW_STAGES.index(retry_from)
            stages: Sequence[ProcessingStage] = PRE_REVIEW_STAGES[start_index:]
            current_stage = retry_from
            try:
                preparation_mode = question_preparation_mode_for_analysis(analysis)
                for current_stage in stages:
                    handler = STAGE_HANDLERS[current_stage]
                    if (
                        current_stage is ProcessingStage.EXTRACTING_EXAM
                        and handler is run_extracting_exam
                    ):
                        run_extracting_exam(
                            analysis,
                            session,
                            settings,
                            preparation_mode=preparation_mode,
                        )
                    else:
                        handler(analysis, session, settings)
                    _transition(
                        session,
                        analysis,
                        current_stage,
                        message=STAGE_SUCCESS_MESSAGES.get(current_stage),
                    )
                run_materializing_review(analysis, session, settings)
                _transition(
                    session,
                    analysis,
                    ProcessingStage.REVIEW_READY,
                    message=REVIEW_READY_MESSAGE,
                )
            except Exception:
                _record_failure(
                    session, analysis, analysis_id, current_stage, context="Retry processing"
                )
            return

        if retry_from not in POST_CONFIRMATION_STAGES or confirmed_review_id is None:
            logger.error(
                "Analysis %s has an invalid post-confirmation retry boundary.", analysis_id
            )
            return
        if analysis.confirmed_review_id != confirmed_review_id:
            logger.warning(
                "Analysis %s confirmed review changed before retry; retry ignored.", analysis_id
            )
            return

        start_index = POST_CONFIRMATION_STAGES.index(retry_from)
        post_stages: Sequence[ProcessingStage] = POST_CONFIRMATION_STAGES[start_index:]
        current_stage = retry_from
        try:
            for current_stage in post_stages:
                STAGE_HANDLERS[current_stage](analysis, session, settings)
                _transition(
                    session,
                    analysis,
                    current_stage,
                    message=STAGE_SUCCESS_MESSAGES.get(current_stage),
                )
            _transition(
                session,
                analysis,
                ProcessingStage.COMPLETED,
                message=COMPLETED_MESSAGE,
            )
        except Exception:
            _record_failure(
                session, analysis, analysis_id, current_stage, context="Retry processing"
            )
