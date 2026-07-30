from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.domain import UploadedFileType
from app.models.assessment_record import AssessmentRecord
from app.models.clo import Clo
from app.models.evidence import Evidence
from app.models.topic import Topic
from app.services.extraction.types import (
    ExtractedAssessmentRecord,
    Tp153ExtractionResult,
)


def _assessment_record_summary(record: ExtractedAssessmentRecord) -> str:
    parts = [f"Method: {record.method}"]
    if record.activity:
        parts.append(f"Activity: {record.activity}")
    if record.percentage is not None:
        parts.append(f"Percentage: {record.percentage}%")
    return " | ".join(parts)


def _persist_source_row(
    session: Session,
    *,
    analysis_id: UUID,
    evidence_type: str,
    item_reference: str,
    page_number: int,
    source_text: str | None,
    extraction_method: str,
    geometry: dict[str, float] | None,
    confidence: float,
) -> None:
    if source_text is None:
        return
    session.add(
        Evidence(
            analysis_id=analysis_id,
            source_document=UploadedFileType.TP153,
            evidence_type=evidence_type,
            page_number=page_number,
            item_reference=item_reference[:100],
            extracted_text=f"Extraction method: {extraction_method}\n{source_text}",
            geometry=geometry,
            confidence=confidence,
        )
    )


def persist_tp153_extraction_result(
    session: Session, analysis_id: UUID, result: Tp153ExtractionResult
) -> None:
    """Persists raw extracted CLOs/topics/assessment records plus traceable
    evidence for each. A missing required section becomes an explicit
    evidence row (evidence_type="missing_section") - never a fabricated
    domain row. Deciding what "missing" means academically (Not Verified)
    is later-milestone rule-engine work; this only records the fact."""

    for clo in result.clos:
        geometry = clo.geometry.to_dict() if clo.geometry else None
        session.add(
            Clo(
                analysis_id=analysis_id,
                code=clo.code,
                text=clo.text,
                program_outcome_reference=clo.program_outcome_reference,
                page_number=clo.page_number,
                confidence=clo.confidence,
                geometry=geometry,
            )
        )
        session.add(
            Evidence(
                analysis_id=analysis_id,
                source_document=UploadedFileType.TP153,
                evidence_type="clo",
                page_number=clo.page_number,
                item_reference=clo.code,
                extracted_text=clo.text,
                geometry=geometry,
                confidence=clo.confidence,
            )
        )
        _persist_source_row(
            session,
            analysis_id=analysis_id,
            evidence_type="clo_source_row",
            item_reference=clo.code,
            page_number=clo.page_number,
            source_text=clo.source_text,
            extraction_method=clo.extraction_method,
            geometry=geometry,
            confidence=clo.confidence,
        )

    for topic in result.topics:
        geometry = topic.geometry.to_dict() if topic.geometry else None
        session.add(
            Topic(
                analysis_id=analysis_id,
                code=topic.code,
                text=topic.text,
                expected_hours=topic.expected_hours,
                page_number=topic.page_number,
                confidence=topic.confidence,
                geometry=geometry,
            )
        )
        session.add(
            Evidence(
                analysis_id=analysis_id,
                source_document=UploadedFileType.TP153,
                evidence_type="topic",
                page_number=topic.page_number,
                item_reference=topic.code or topic.text[:100],
                extracted_text=topic.text,
                geometry=geometry,
                confidence=topic.confidence,
            )
        )
        _persist_source_row(
            session,
            analysis_id=analysis_id,
            evidence_type="topic_source_row",
            item_reference=topic.code or topic.text[:100],
            page_number=topic.page_number,
            source_text=topic.source_text,
            extraction_method=topic.extraction_method,
            geometry=geometry,
            confidence=topic.confidence,
        )

    for record in result.assessment_records:
        geometry = record.geometry.to_dict() if record.geometry else None
        session.add(
            AssessmentRecord(
                analysis_id=analysis_id,
                method=record.method,
                activity=record.activity,
                percentage=record.percentage,
                page_number=record.page_number,
                confidence=record.confidence,
                geometry=geometry,
            )
        )
        session.add(
            Evidence(
                analysis_id=analysis_id,
                source_document=UploadedFileType.TP153,
                evidence_type="assessment_record",
                page_number=record.page_number,
                item_reference=record.method[:100],
                extracted_text=_assessment_record_summary(record),
                geometry=geometry,
                confidence=record.confidence,
            )
        )
        _persist_source_row(
            session,
            analysis_id=analysis_id,
            evidence_type="assessment_record_source_row",
            item_reference=record.method,
            page_number=record.page_number,
            source_text=record.source_text,
            extraction_method=record.extraction_method,
            geometry=geometry,
            confidence=record.confidence,
        )

    for field in result.course_fields:
        session.add(
            Evidence(
                analysis_id=analysis_id,
                source_document=UploadedFileType.TP153,
                evidence_type="course_specification_field",
                page_number=field.page_number,
                item_reference=field.field_name,
                extracted_text=field.value,
                geometry=field.geometry.to_dict() if field.geometry else None,
                confidence=field.confidence,
            )
        )

    for missing in result.missing_sections:
        session.add(
            Evidence(
                analysis_id=analysis_id,
                source_document=UploadedFileType.TP153,
                evidence_type="missing_section",
                page_number=missing.page_number,
                item_reference=missing.section,
                extracted_text=missing.note,
                geometry=None,
                confidence=0.0,
            )
        )

    for warning in result.review_warnings:
        session.add(
            Evidence(
                analysis_id=analysis_id,
                source_document=UploadedFileType.TP153,
                evidence_type="course_specification_warning",
                page_number=warning.page_number,
                item_reference=warning.code,
                extracted_text=warning.message,
                geometry=None,
                confidence=warning.confidence,
            )
        )

    session.flush()
