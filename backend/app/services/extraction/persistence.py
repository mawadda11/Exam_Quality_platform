from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.domain import UploadedFileType
from app.models.evidence import Evidence
from app.models.question import Question
from app.services.extraction.types import ExtractionResult


def persist_extraction_result(
    session: Session, analysis_id: UUID, result: ExtractionResult
) -> None:
    """Two passes over questions: insert every row first so each gets a
    generated id, then resolve parent_question_id from parent_number_label
    now that every label maps to a known row. Evidence links to a question
    the same way, via question_number_label -> number_label."""
    rows_by_label: dict[str, Question] = {}

    for extracted in result.questions:
        row = Question(
            analysis_id=analysis_id,
            number_label=extracted.number_label,
            question_text=extracted.text,
            page_number=extracted.page_number,
            marks=extracted.marks,
            sequence=extracted.sequence,
            confidence=extracted.confidence,
            geometry=extracted.geometry.to_dict() if extracted.geometry else None,
        )
        session.add(row)
        rows_by_label[extracted.number_label] = row

    session.flush()

    for extracted in result.questions:
        if extracted.parent_number_label:
            parent_row = rows_by_label.get(extracted.parent_number_label)
            if parent_row is not None:
                rows_by_label[extracted.number_label].parent_question_id = parent_row.id

    for ev in result.evidence:
        related_question = (
            rows_by_label.get(ev.question_number_label) if ev.question_number_label else None
        )
        session.add(
            Evidence(
                analysis_id=analysis_id,
                question_id=related_question.id if related_question else None,
                source_document=UploadedFileType.EXAM,
                evidence_type=ev.evidence_type,
                page_number=ev.page_number,
                item_reference=ev.item_reference,
                extracted_text=ev.extracted_text,
                geometry=ev.geometry.to_dict() if ev.geometry else None,
                confidence=ev.confidence,
            )
        )

    session.flush()
