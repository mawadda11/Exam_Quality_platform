from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.assessment_record import AssessmentRecord
from app.models.clo import Clo
from app.models.evidence import Evidence
from app.models.extraction_review_revision import ExtractionReviewRevision
from app.models.question import Question
from app.models.topic import Topic
from app.schemas.extraction_review import (
    ExtractionReviewAssessmentRecord,
    ExtractionReviewClo,
    ExtractionReviewEvidence,
    ExtractionReviewGeometry,
    ExtractionReviewQuestion,
    ExtractionReviewSnapshot,
    ExtractionReviewTopic,
)

INITIAL_REVIEW_REVISION = 1


def _geometry(value: dict[str, Any] | None) -> ExtractionReviewGeometry | None:
    if value is None:
        return None
    return ExtractionReviewGeometry.model_validate(value)


def _validate_stored_snapshot(value: dict[str, Any]) -> ExtractionReviewSnapshot:
    """Validate database JSON through Pydantic's strict JSON boundary."""
    return ExtractionReviewSnapshot.model_validate_json(json.dumps(value))


def _build_snapshot(session: Session, analysis_id: UUID) -> ExtractionReviewSnapshot:
    questions = list(
        session.execute(
            select(Question)
            .where(Question.analysis_id == analysis_id)
            .order_by(Question.sequence, Question.page_number, Question.id)
        ).scalars()
    )
    evidence = list(
        session.execute(
            select(Evidence)
            .where(Evidence.analysis_id == analysis_id)
            .order_by(
                Evidence.source_document,
                Evidence.page_number,
                Evidence.item_reference,
                Evidence.id,
            )
        ).scalars()
    )
    clos = list(
        session.execute(
            select(Clo)
            .where(Clo.analysis_id == analysis_id)
            .order_by(Clo.page_number, Clo.code, Clo.id)
        ).scalars()
    )
    topics = list(
        session.execute(
            select(Topic)
            .where(Topic.analysis_id == analysis_id)
            .order_by(Topic.page_number, Topic.code, Topic.text, Topic.id)
        ).scalars()
    )
    assessment_records = list(
        session.execute(
            select(AssessmentRecord)
            .where(AssessmentRecord.analysis_id == analysis_id)
            .order_by(
                AssessmentRecord.page_number,
                AssessmentRecord.method,
                AssessmentRecord.id,
            )
        ).scalars()
    )

    return ExtractionReviewSnapshot(
        schema_version=1,
        questions=[
            ExtractionReviewQuestion(
                source_record_id=question.id,
                included=True,
                parent_source_record_id=question.parent_question_id,
                number_label=question.number_label,
                question_text=question.question_text,
                page_number=question.page_number,
                marks=question.marks,
                sequence=question.sequence,
                extraction_confidence=question.confidence,
                geometry=_geometry(question.geometry),
            )
            for question in questions
        ],
        evidence=[
            ExtractionReviewEvidence(
                source_record_id=item.id,
                included=True,
                question_source_record_id=item.question_id,
                source_document=item.source_document,
                evidence_type=item.evidence_type,
                page_number=item.page_number,
                item_reference=item.item_reference,
                extracted_text=item.extracted_text,
                extraction_confidence=item.confidence,
                geometry=_geometry(item.geometry),
            )
            for item in evidence
        ],
        clos=[
            ExtractionReviewClo(
                source_record_id=clo.id,
                included=True,
                code=clo.code,
                text=clo.text,
                program_outcome_reference=clo.program_outcome_reference,
                page_number=clo.page_number,
                extraction_confidence=clo.confidence,
                geometry=_geometry(clo.geometry),
            )
            for clo in clos
        ],
        topics=[
            ExtractionReviewTopic(
                source_record_id=topic.id,
                included=True,
                code=topic.code,
                text=topic.text,
                expected_hours=topic.expected_hours,
                page_number=topic.page_number,
                extraction_confidence=topic.confidence,
                geometry=_geometry(topic.geometry),
            )
            for topic in topics
        ],
        assessment_records=[
            ExtractionReviewAssessmentRecord(
                source_record_id=record.id,
                included=True,
                method=record.method,
                activity=record.activity,
                percentage=record.percentage,
                page_number=record.page_number,
                extraction_confidence=record.confidence,
                geometry=_geometry(record.geometry),
            )
            for record in assessment_records
        ],
    )


def materialize_initial_review_revision(
    session: Session,
    analysis_id: UUID,
) -> ExtractionReviewRevision:
    """Create revision 1 once, without overwriting a concurrent winner.

    The nested transaction contains the uniqueness race. If its INSERT loses,
    only the savepoint is rolled back, leaving the outer transaction usable
    for the required requery and eventual review-ready transition.
    """

    statement = select(ExtractionReviewRevision).where(
        ExtractionReviewRevision.analysis_id == analysis_id,
        ExtractionReviewRevision.revision_number == INITIAL_REVIEW_REVISION,
    )
    existing = session.execute(statement).scalar_one_or_none()
    if existing is not None:
        _validate_stored_snapshot(existing.snapshot)
        return existing

    snapshot = _build_snapshot(session, analysis_id)
    revision = ExtractionReviewRevision(
        analysis_id=analysis_id,
        revision_number=INITIAL_REVIEW_REVISION,
        snapshot=snapshot.model_dump(mode="json"),
    )

    try:
        with session.begin_nested():
            session.add(revision)
            session.flush()
    except IntegrityError:
        existing = session.execute(statement).scalar_one_or_none()
        if existing is None:
            raise
        _validate_stored_snapshot(existing.snapshot)
        return existing

    return revision
