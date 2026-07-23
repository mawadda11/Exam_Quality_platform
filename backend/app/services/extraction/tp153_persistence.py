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


def persist_tp153_extraction_result(
    session: Session, analysis_id: UUID, result: Tp153ExtractionResult
) -> None:
    """Persists raw extracted CLOs/topics/assessment records plus traceable
    evidence for each. A missing required section becomes an explicit
    evidence row (evidence_type="missing_section") - never a fabricated
    domain row. Deciding what "missing" means academically (Not Verified)
    is later-milestone rule-engine work; this only records the fact."""

    for clo in result.clos:
        session.add(
            Clo(
                analysis_id=analysis_id,
                code=clo.code,
                text=clo.text,
                program_outcome_reference=clo.program_outcome_reference,
                page_number=clo.page_number,
                confidence=clo.confidence,
                geometry=clo.geometry.to_dict() if clo.geometry else None,
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
                geometry=clo.geometry.to_dict() if clo.geometry else None,
                confidence=clo.confidence,
            )
        )

    for topic in result.topics:
        session.add(
            Topic(
                analysis_id=analysis_id,
                code=topic.code,
                text=topic.text,
                expected_hours=topic.expected_hours,
                page_number=topic.page_number,
                confidence=topic.confidence,
                geometry=topic.geometry.to_dict() if topic.geometry else None,
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
                geometry=topic.geometry.to_dict() if topic.geometry else None,
                confidence=topic.confidence,
            )
        )

    for record in result.assessment_records:
        session.add(
            AssessmentRecord(
                analysis_id=analysis_id,
                method=record.method,
                activity=record.activity,
                percentage=record.percentage,
                page_number=record.page_number,
                confidence=record.confidence,
                geometry=record.geometry.to_dict() if record.geometry else None,
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
                geometry=record.geometry.to_dict() if record.geometry else None,
                confidence=record.confidence,
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

    session.flush()
