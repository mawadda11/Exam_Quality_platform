from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.domain import ProcessingStage
from app.models.analysis import Analysis
from app.models.assessment_record import AssessmentRecord
from app.models.clo import Clo
from app.models.evidence import Evidence
from app.models.extraction_review_revision import ExtractionReviewRevision
from app.models.processing_event import ProcessingEvent
from app.models.question import Question
from app.models.topic import Topic
from app.schemas.extraction_review import (
    ExtractionReviewAssessmentRecord,
    ExtractionReviewQuestion,
    ExtractionReviewResponse,
    ExtractionReviewSnapshot,
    ExtractionReviewWarning,
)
from app.services.extraction.review_snapshot import INITIAL_REVIEW_REVISION

LOW_EXTRACTION_CONFIDENCE = 0.75


class ExtractionReviewError(RuntimeError):
    """Base class for safe review-workflow conflicts."""


class ExtractionReviewNotReadyError(ExtractionReviewError):
    pass


class ExtractionReviewClosedError(ExtractionReviewError):
    pass


class ExtractionReviewRevisionNotFoundError(ExtractionReviewError):
    pass


class ExtractionReviewStaleRevisionError(ExtractionReviewError):
    pass


class ExtractionReviewSourceFaithfulnessError(ExtractionReviewError):
    pass


@dataclass(frozen=True)
class ConfirmedReview:
    revision_id: UUID
    revision_number: int


def _validate_stored_snapshot(value: dict[str, Any]) -> ExtractionReviewSnapshot:
    return ExtractionReviewSnapshot.model_validate_json(json.dumps(value))


def _snapshot(revision: ExtractionReviewRevision) -> ExtractionReviewSnapshot:
    return _validate_stored_snapshot(revision.snapshot)


def _revision_by_number(
    session: Session, analysis_id: UUID, revision_number: int
) -> ExtractionReviewRevision | None:
    return session.execute(
        select(ExtractionReviewRevision).where(
            ExtractionReviewRevision.analysis_id == analysis_id,
            ExtractionReviewRevision.revision_number == revision_number,
        )
    ).scalar_one_or_none()


def _revision_by_id(
    session: Session, analysis_id: UUID, revision_id: UUID
) -> ExtractionReviewRevision | None:
    return session.execute(
        select(ExtractionReviewRevision).where(
            ExtractionReviewRevision.analysis_id == analysis_id,
            ExtractionReviewRevision.id == revision_id,
        )
    ).scalar_one_or_none()


def latest_review_revision(session: Session, analysis_id: UUID) -> ExtractionReviewRevision:
    revision = session.execute(
        select(ExtractionReviewRevision)
        .where(ExtractionReviewRevision.analysis_id == analysis_id)
        .order_by(ExtractionReviewRevision.revision_number.desc())
        .limit(1)
    ).scalar_one_or_none()
    if revision is None:
        raise ExtractionReviewNotReadyError(
            "Extraction review is not available until source extraction has completed."
        )
    _snapshot(revision)
    return revision


def _original_review_revision(session: Session, analysis_id: UUID) -> ExtractionReviewRevision:
    revision = _revision_by_number(session, analysis_id, INITIAL_REVIEW_REVISION)
    if revision is None:
        raise ExtractionReviewNotReadyError(
            "The original machine-extraction review revision is unavailable."
        )
    _snapshot(revision)
    return revision


def _record_map(items: Iterable[Any]) -> dict[UUID, Any]:
    return {item.source_record_id: item for item in items}


def _assert_same_record_ids(
    *, collection: str, original_items: Iterable[Any], candidate_items: Iterable[Any]
) -> None:
    original_ids = set(_record_map(original_items))
    candidate_ids = set(_record_map(candidate_items))
    if original_ids == candidate_ids:
        return
    added = sorted(str(value) for value in candidate_ids - original_ids)
    removed = sorted(str(value) for value in original_ids - candidate_ids)
    details: list[str] = []
    if added:
        details.append(f"added IDs: {', '.join(added)}")
    if removed:
        details.append(f"missing IDs: {', '.join(removed)}")
    raise ExtractionReviewSourceFaithfulnessError(
        f"{collection} must preserve the complete machine-extraction source-record set "
        f"({'; '.join(details)})."
    )


def _assert_immutable_fields(
    *,
    collection: str,
    original_items: Iterable[Any],
    candidate_items: Iterable[Any],
    fields: tuple[str, ...],
) -> None:
    original_by_id = _record_map(original_items)
    for candidate in candidate_items:
        original = original_by_id[candidate.source_record_id]
        changed = [
            field
            for field in fields
            if getattr(candidate, field) != getattr(original, field)
        ]
        if changed:
            raise ExtractionReviewSourceFaithfulnessError(
                f"{collection} record {candidate.source_record_id} changed immutable source "
                f"anchor fields: {', '.join(changed)}."
            )


def _assessment_summary(record: ExtractionReviewAssessmentRecord) -> str:
    parts = [f"Method: {record.method}"]
    if record.activity:
        parts.append(f"Activity: {record.activity}")
    if record.percentage is not None:
        parts.append(f"Percentage: {record.percentage}%")
    return " | ".join(parts)


def _normalize_related_evidence(
    candidate: ExtractionReviewSnapshot,
    original: ExtractionReviewSnapshot,
) -> ExtractionReviewSnapshot:
    """Keep duplicated evidence summaries aligned with corrected source entities.

    Review clients submit one complete snapshot, but entity text is also represented by traceable
    Evidence rows. Normalizing those duplicated fields centrally prevents a corrected question/CLO
    from being evaluated against stale evidence text while preserving all immutable source anchors.
    """

    normalized = candidate.model_copy(deep=True)
    candidate_questions = _record_map(normalized.questions)
    for evidence in normalized.evidence:
        if evidence.question_source_record_id is None:
            continue
        question = candidate_questions[evidence.question_source_record_id]
        if not question.included:
            evidence.included = False
        if evidence.evidence_type == "question_text":
            evidence.item_reference = question.number_label
            evidence.extracted_text = question.question_text
        elif evidence.evidence_type == "marks":
            evidence.item_reference = question.number_label

    normalized_evidence = _record_map(normalized.evidence)

    original_clos = _record_map(original.clos)
    candidate_clos = _record_map(normalized.clos)
    original_topics = _record_map(original.topics)
    candidate_topics = _record_map(normalized.topics)
    original_records = _record_map(original.assessment_records)
    candidate_records = _record_map(normalized.assessment_records)

    for original_evidence in original.evidence:
        candidate_evidence = normalized_evidence[original_evidence.source_record_id]
        if original_evidence.evidence_type == "clo":
            matches = [
                item
                for item in original_clos.values()
                if item.page_number == original_evidence.page_number
                and item.code == original_evidence.item_reference
                and item.geometry == original_evidence.geometry
            ]
            if len(matches) == 1:
                clo = candidate_clos[matches[0].source_record_id]
                if not clo.included:
                    candidate_evidence.included = False
                candidate_evidence.item_reference = clo.code
                candidate_evidence.extracted_text = clo.text
        elif original_evidence.evidence_type == "topic":
            matches = [
                item
                for item in original_topics.values()
                if item.page_number == original_evidence.page_number
                and (item.code or item.text[:100]) == original_evidence.item_reference
                and item.geometry == original_evidence.geometry
            ]
            if len(matches) == 1:
                topic = candidate_topics[matches[0].source_record_id]
                if not topic.included:
                    candidate_evidence.included = False
                candidate_evidence.item_reference = topic.code or topic.text[:100]
                candidate_evidence.extracted_text = topic.text
        elif original_evidence.evidence_type == "assessment_record":
            matches = [
                item
                for item in original_records.values()
                if item.page_number == original_evidence.page_number
                and item.method[:100] == original_evidence.item_reference
                and item.geometry == original_evidence.geometry
            ]
            if len(matches) == 1:
                record = candidate_records[matches[0].source_record_id]
                if not record.included:
                    candidate_evidence.included = False
                candidate_evidence.item_reference = record.method[:100]
                candidate_evidence.extracted_text = _assessment_summary(record)

    # Re-run cross-reference validation after normalization changed inclusion states.
    return ExtractionReviewSnapshot.model_validate(normalized.model_dump())


def validate_source_faithful_snapshot(
    candidate: ExtractionReviewSnapshot,
    original: ExtractionReviewSnapshot,
) -> ExtractionReviewSnapshot:
    if candidate.schema_version != original.schema_version:
        raise ExtractionReviewSourceFaithfulnessError(
            "The extraction-review schema version cannot be changed."
        )

    collections: tuple[tuple[str, Iterable[Any], Iterable[Any]], ...] = (
        ("questions", original.questions, candidate.questions),
        ("evidence", original.evidence, candidate.evidence),
        ("CLOs", original.clos, candidate.clos),
        ("topics", original.topics, candidate.topics),
        ("assessment records", original.assessment_records, candidate.assessment_records),
    )
    for label, original_items, candidate_items in collections:
        _assert_same_record_ids(
            collection=label,
            original_items=original_items,
            candidate_items=candidate_items,
        )

    _assert_immutable_fields(
        collection="Question",
        original_items=original.questions,
        candidate_items=candidate.questions,
        fields=(
            "source_record_id",
            "parent_source_record_id",
            "page_number",
            "sequence",
            "extraction_confidence",
            "geometry",
        ),
    )
    _assert_immutable_fields(
        collection="Evidence",
        original_items=original.evidence,
        candidate_items=candidate.evidence,
        fields=(
            "source_record_id",
            "question_source_record_id",
            "source_document",
            "evidence_type",
            "page_number",
            "extraction_confidence",
            "geometry",
        ),
    )
    _assert_immutable_fields(
        collection="CLO",
        original_items=original.clos,
        candidate_items=candidate.clos,
        fields=("source_record_id", "page_number", "extraction_confidence", "geometry"),
    )
    _assert_immutable_fields(
        collection="Topic",
        original_items=original.topics,
        candidate_items=candidate.topics,
        fields=("source_record_id", "page_number", "extraction_confidence", "geometry"),
    )
    _assert_immutable_fields(
        collection="Assessment record",
        original_items=original.assessment_records,
        candidate_items=candidate.assessment_records,
        fields=("source_record_id", "page_number", "extraction_confidence", "geometry"),
    )
    return _normalize_related_evidence(candidate, original)


def _review_blockers(analysis: Analysis) -> list[str]:
    blockers: list[str] = []
    if analysis.confirmed_review_id is not None:
        blockers.append("This extraction review has already been confirmed.")
    elif analysis.state != ProcessingStage.REVIEW_READY:
        blockers.append("The analysis is not currently waiting for extraction review.")
    return blockers


def _warnings(snapshot: ExtractionReviewSnapshot) -> list[ExtractionReviewWarning]:
    warnings: list[ExtractionReviewWarning] = []
    collection_specs: tuple[tuple[str, str, list[Any]], ...] = (
        ("questions", "questions", snapshot.questions),
        ("clos", "CLOs", snapshot.clos),
        ("topics", "topics", snapshot.topics),
        ("assessment_records", "assessment records", snapshot.assessment_records),
        ("evidence", "evidence records", snapshot.evidence),
    )
    for collection, label, items in collection_specs:
        included = [item for item in items if item.included]
        if not included:
            warnings.append(
                ExtractionReviewWarning(
                    code="empty_collection",
                    severity="warning",
                    collection=collection,  # type: ignore[arg-type]
                    source_record_id=None,
                    message=f"No included {label} are available in this extraction.",
                )
            )
        excluded_count = len(items) - len(included)
        if excluded_count:
            warnings.append(
                ExtractionReviewWarning(
                    code="excluded_records",
                    severity="info",
                    collection=collection,  # type: ignore[arg-type]
                    source_record_id=None,
                    message=f"{excluded_count} {label} will be excluded from downstream analysis.",
                )
            )
        for item in included:
            if item.extraction_confidence < LOW_EXTRACTION_CONFIDENCE:
                warnings.append(
                    ExtractionReviewWarning(
                        code="low_extraction_confidence",
                        severity="warning",
                        collection=collection,  # type: ignore[arg-type]
                        source_record_id=item.source_record_id,
                        message=(
                            f"This {label[:-1] if label.endswith('s') else label} has low "
                            "machine-extraction confidence and should be checked against the PDF."
                        ),
                    )
                )
    return warnings


def get_extraction_review(session: Session, analysis: Analysis) -> ExtractionReviewResponse:
    latest = latest_review_revision(session, analysis.id)
    original = _original_review_revision(session, analysis.id)
    blockers = _review_blockers(analysis)
    return ExtractionReviewResponse(
        analysis_id=analysis.id,
        revision_id=latest.id,
        revision_number=latest.revision_number,
        created_at=latest.created_at,
        snapshot=_snapshot(latest),
        original_snapshot=_snapshot(original),
        confirmed_revision_id=analysis.confirmed_review_id,
        is_confirmed=analysis.confirmed_review_id is not None,
        can_edit=not blockers,
        can_confirm=not blockers,
        warnings=_warnings(_snapshot(latest)),
        confirmation_blockers=blockers,
    )


def append_extraction_review_revision(
    session: Session,
    analysis: Analysis,
    *,
    base_revision_id: UUID,
    candidate_snapshot: ExtractionReviewSnapshot,
) -> ExtractionReviewResponse:
    blockers = _review_blockers(analysis)
    if blockers:
        raise ExtractionReviewClosedError(blockers[0])

    latest = latest_review_revision(session, analysis.id)
    if latest.id != base_revision_id:
        raise ExtractionReviewStaleRevisionError(
            "The extraction review changed after this page was loaded. Reload the latest revision."
        )
    original = _original_review_revision(session, analysis.id)
    normalized = validate_source_faithful_snapshot(candidate_snapshot, _snapshot(original))

    next_revision_number = latest.revision_number + 1
    revision = ExtractionReviewRevision(
        analysis_id=analysis.id,
        revision_number=next_revision_number,
        snapshot=normalized.model_dump(mode="json"),
    )
    try:
        with session.begin_nested():
            session.add(revision)
            session.flush()
    except IntegrityError as exc:
        raise ExtractionReviewStaleRevisionError(
            "A newer extraction-review revision was saved concurrently. Reload and try again."
        ) from exc

    return ExtractionReviewResponse(
        analysis_id=analysis.id,
        revision_id=revision.id,
        revision_number=revision.revision_number,
        created_at=revision.created_at,
        snapshot=normalized,
        original_snapshot=_snapshot(original),
        confirmed_revision_id=None,
        is_confirmed=False,
        can_edit=True,
        can_confirm=True,
        warnings=_warnings(normalized),
        confirmation_blockers=[],
    )


def _rows_by_id(session: Session, model: type[Any], analysis_id: UUID) -> dict[UUID, Any]:
    rows = session.execute(select(model).where(model.analysis_id == analysis_id)).scalars().all()
    return {row.id: row for row in rows}


def _require_exact_persisted_ids(
    *, collection: str, rows: dict[UUID, Any], expected_ids: set[UUID]
) -> None:
    if set(rows) != expected_ids:
        raise ExtractionReviewSourceFaithfulnessError(
            f"Persisted {collection} no longer match the confirmed review source-record set."
        )


def _apply_confirmed_snapshot(
    session: Session, analysis_id: UUID, snapshot: ExtractionReviewSnapshot
) -> None:
    """Materialize one confirmed snapshot for existing downstream evaluators.

    Revision 1 remains the immutable machine-extraction audit record. The canonical source tables
    become the confirmed, included transcription consumed by deterministic and semantic stages.
    No new source-row identity is ever created here.
    """

    evidence_rows = _rows_by_id(session, Evidence, analysis_id)
    question_rows = _rows_by_id(session, Question, analysis_id)
    clo_rows = _rows_by_id(session, Clo, analysis_id)
    topic_rows = _rows_by_id(session, Topic, analysis_id)
    record_rows = _rows_by_id(session, AssessmentRecord, analysis_id)

    _require_exact_persisted_ids(
        collection="evidence",
        rows=evidence_rows,
        expected_ids={item.source_record_id for item in snapshot.evidence},
    )
    _require_exact_persisted_ids(
        collection="questions",
        rows=question_rows,
        expected_ids={item.source_record_id for item in snapshot.questions},
    )
    _require_exact_persisted_ids(
        collection="CLOs",
        rows=clo_rows,
        expected_ids={item.source_record_id for item in snapshot.clos},
    )
    _require_exact_persisted_ids(
        collection="topics",
        rows=topic_rows,
        expected_ids={item.source_record_id for item in snapshot.topics},
    )
    _require_exact_persisted_ids(
        collection="assessment records",
        rows=record_rows,
        expected_ids={item.source_record_id for item in snapshot.assessment_records},
    )

    for evidence_item in snapshot.evidence:
        evidence_row = evidence_rows[evidence_item.source_record_id]
        if not evidence_item.included:
            session.delete(evidence_row)
            continue
        evidence_row.item_reference = evidence_item.item_reference
        evidence_row.extracted_text = evidence_item.extracted_text
    session.flush()

    included_questions: list[ExtractionReviewQuestion] = []
    excluded_questions: list[ExtractionReviewQuestion] = []

    for question_item in snapshot.questions:
        target_questions = (
            included_questions if question_item.included else excluded_questions
        )
        target_questions.append(question_item)

    for question_item in included_questions:
        question_row = question_rows[question_item.source_record_id]
        question_row.number_label = question_item.number_label
        question_row.question_text = question_item.question_text
        question_row.marks = question_item.marks

    questions_by_id = _record_map(snapshot.questions)

    def question_depth(question_item: ExtractionReviewQuestion) -> int:
        depth = 0
        parent_id = question_item.parent_source_record_id

        while parent_id is not None:
            depth += 1
            parent_id = questions_by_id[parent_id].parent_source_record_id

        return depth

    for excluded_question in sorted(
        excluded_questions,
        key=lambda value: (question_depth(value), value.sequence),
        reverse=True,
    ):
        session.delete(question_rows[excluded_question.source_record_id])
    session.flush()

    for clo_item in snapshot.clos:
        clo_row = clo_rows[clo_item.source_record_id]
        if not clo_item.included:
            session.delete(clo_row)
            continue
        clo_row.code = clo_item.code
        clo_row.text = clo_item.text
        clo_row.program_outcome_reference = clo_item.program_outcome_reference

    for topic_item in snapshot.topics:
        topic_row = topic_rows[topic_item.source_record_id]
        if not topic_item.included:
            session.delete(topic_row)
            continue
        topic_row.code = topic_item.code
        topic_row.text = topic_item.text
        topic_row.expected_hours = topic_item.expected_hours

    for assessment_item in snapshot.assessment_records:
        assessment_row = record_rows[assessment_item.source_record_id]
        if not assessment_item.included:
            session.delete(assessment_row)
            continue
        assessment_row.method = assessment_item.method
        assessment_row.activity = assessment_item.activity
        assessment_row.percentage = assessment_item.percentage

    session.flush()


def confirm_extraction_review(
    session: Session,
    analysis: Analysis,
    *,
    revision_id: UUID,
) -> ConfirmedReview:
    blockers = _review_blockers(analysis)
    if blockers:
        raise ExtractionReviewClosedError(blockers[0])

    revision = _revision_by_id(session, analysis.id, revision_id)
    if revision is None:
        raise ExtractionReviewRevisionNotFoundError("Extraction-review revision not found.")
    latest = latest_review_revision(session, analysis.id)
    if latest.id != revision.id:
        raise ExtractionReviewStaleRevisionError(
            "Only the latest extraction-review revision can be confirmed."
        )

    original = _original_review_revision(session, analysis.id)
    confirmed_snapshot = validate_source_faithful_snapshot(
        _snapshot(revision),
        _snapshot(original),
    )
    _apply_confirmed_snapshot(session, analysis.id, confirmed_snapshot)

    claim = session.execute(
        update(Analysis)
        .where(
            Analysis.id == analysis.id,
            Analysis.state == ProcessingStage.REVIEW_READY,
            Analysis.confirmed_review_id.is_(None),
        )
        .values(
            confirmed_review_id=revision.id,
            state=ProcessingStage.BUILDING_EVIDENCE,
        )
        .execution_options(synchronize_session=False)
    )
    assert isinstance(claim, CursorResult)
    if claim.rowcount != 1:
        raise ExtractionReviewClosedError(
            "This extraction review was already confirmed by another request."
        )

    session.add(
        ProcessingEvent(
            analysis_id=analysis.id,
            stage=ProcessingStage.BUILDING_EVIDENCE,
            message=(
                f"Extraction review revision {revision.revision_number} was confirmed; "
                "downstream analysis started."
            ),
        )
    )
    session.flush()
    return ConfirmedReview(revision_id=revision.id, revision_number=revision.revision_number)


def review_revision_count(session: Session, analysis_id: UUID) -> int:
    """Small test/audit helper; avoids leaking revision internals into routes."""
    return int(
        session.execute(
            select(func.count(ExtractionReviewRevision.id)).where(
                ExtractionReviewRevision.analysis_id == analysis_id
            )
        ).scalar_one()
    )
