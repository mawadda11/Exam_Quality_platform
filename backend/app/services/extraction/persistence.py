from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.domain import ExtractionWarningSeverity, QuestionReviewStatus, UploadedFileType
from app.models.evidence import Evidence
from app.models.extraction_warning import ExtractionWarning
from app.models.question import Question
from app.models.question_blank import QuestionBlank
from app.models.question_option import QuestionOption
from app.models.question_source_span import QuestionSourceSpan
from app.services.extraction.structured_persistence import persist_structured_evidence
from app.services.extraction.types import ExtractionResult


def persist_extraction_result(
    session: Session, analysis_id: UUID, result: ExtractionResult
) -> None:
    """Two passes over questions: insert every row first so each gets a
    generated id, then resolve parent_question_id from parent_number_label
    now that every label maps to a known row. Evidence links to a question
    the same way, via question_number_label -> number_label."""
    rows_by_label: dict[str, list[Question]] = {}
    rows_by_key: dict[str, Question] = {}
    extracted_by_key = {
        (item.local_key or f"P{item.page_number}-Q{item.sequence}"): item
        for item in result.questions
    }
    critical_line_ids = {
        source_line_id
        for warning in result.reconciliation_warnings
        if warning.severity is ExtractionWarningSeverity.CRITICAL and not warning.resolved
        for source_line_id in warning.source_line_ids
    }

    for extracted in result.questions:
        row = Question(
            analysis_id=analysis_id,
            number_label=extracted.number_label,
            question_text=extracted.text,
            question_type=extracted.question_type,
            instructions=extracted.instructions,
            page_number=extracted.page_number,
            marks=extracted.marks,
            sequence=extracted.sequence,
            confidence=extracted.confidence,
            geometry=extracted.geometry.to_dict() if extracted.geometry else None,
            extraction_method=extracted.extraction_method,
            review_status=(
                QuestionReviewStatus.NEEDS_REVIEW
                if critical_line_ids.intersection(extracted.source_line_ids)
                else extracted.review_status
            ),
        )
        session.add(row)
        local_key = extracted.local_key or f"P{extracted.page_number}-Q{extracted.sequence}"
        rows_by_key[local_key] = row
        rows_by_label.setdefault(extracted.number_label, []).append(row)

    session.flush()

    for extracted in result.questions:
        local_key = extracted.local_key or f"P{extracted.page_number}-Q{extracted.sequence}"
        parent_row = rows_by_key.get(extracted.parent_local_key or "")
        if parent_row is None and extracted.parent_number_label:
            candidates = [
                row
                for row in rows_by_label.get(extracted.parent_number_label, [])
                if row.sequence < extracted.sequence
            ]
            parent_row = max(candidates, key=lambda row: row.sequence) if candidates else None
        if parent_row is not None:
            rows_by_key[local_key].parent_question_id = parent_row.id

    source_lines_by_id = {item.source_line_id: item for item in result.source_lines}
    for local_key, extracted in extracted_by_key.items():
        question_row = rows_by_key[local_key]
        option_rows: dict[str, QuestionOption] = {}
        for option in extracted.options:
            option_row = QuestionOption(
                question_id=question_row.id,
                option_label=option.option_label,
                option_text=option.option_text,
                sequence=option.sequence,
                page_number=option.page_number,
                confidence=option.confidence,
                geometry=option.geometry.to_dict() if option.geometry else None,
            )
            session.add(option_row)
            option_rows[option.local_key] = option_row
        session.flush()

        for blank in extracted.blanks:
            session.add(
                QuestionBlank(
                    question_id=question_row.id,
                    blank_index=blank.blank_index,
                    source_text=blank.source_text,
                    page_number=blank.page_number,
                    geometry=blank.geometry.to_dict() if blank.geometry else None,
                )
            )

        question_line_ids = extracted.source_line_ids or (
            f"P{extracted.page_number}-Q{extracted.sequence}-canonical",
        )
        for source_line_id in question_line_ids:
            source = source_lines_by_id.get(source_line_id)
            session.add(
                QuestionSourceSpan(
                    question_id=question_row.id,
                    option_id=None,
                    provider=source.provider if source else extracted.extraction_method,
                    provider_version=source.provider_version if source else None,
                    source_line_id=source_line_id,
                    original_text=source.original_text if source else extracted.text,
                    page_number=source.page_number if source else extracted.page_number,
                    geometry=(
                        source.geometry.to_dict()
                        if source and source.geometry
                        else (extracted.geometry.to_dict() if extracted.geometry else None)
                    ),
                    confidence=source.confidence if source else extracted.confidence,
                    extraction_method=(
                        source.extraction_method if source else extracted.extraction_method
                    ),
                )
            )
        for option in extracted.options:
            option_row = option_rows[option.local_key]
            option_line_ids = option.source_line_ids or (
                f"P{option.page_number}-{option.local_key}-canonical",
            )
            for source_line_id in option_line_ids:
                source = source_lines_by_id.get(source_line_id)
                session.add(
                    QuestionSourceSpan(
                        question_id=question_row.id,
                        option_id=option_row.id,
                        provider=source.provider if source else extracted.extraction_method,
                        provider_version=source.provider_version if source else None,
                        source_line_id=source_line_id,
                        original_text=source.original_text if source else option.option_text,
                        page_number=source.page_number if source else option.page_number,
                        geometry=(
                            source.geometry.to_dict()
                            if source and source.geometry
                            else (option.geometry.to_dict() if option.geometry else None)
                        ),
                        confidence=source.confidence if source else option.confidence,
                        extraction_method=(
                            source.extraction_method if source else extracted.extraction_method
                        ),
                    )
                )

    for ev in result.evidence:
        related_question = rows_by_key.get(ev.question_local_key or "") or (
            rows_by_label.get(ev.question_number_label, [None])[-1]
            if ev.question_number_label
            else None
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

    for candidate in result.structure_candidates:
        question = rows_by_key.get(candidate.question_local_key or "")
        session.add(
            Evidence(
                analysis_id=analysis_id,
                question_id=question.id if question is not None else None,
                source_document=UploadedFileType.EXAM,
                evidence_type=(
                    f"extraction_candidate_{candidate.pipeline}_{candidate.provenance}"[:100]
                ),
                page_number=candidate.page_number,
                item_reference=candidate.candidate_id[:100],
                extracted_text=candidate.original_text,
                geometry=candidate.geometry.to_dict() if candidate.geometry else None,
                confidence=candidate.confidence,
            )
        )

    session.flush()
    for warning in result.reconciliation_warnings:
        session.add(
            ExtractionWarning(
                analysis_id=analysis_id,
                code=warning.code,
                severity=warning.severity,
                page_number=warning.page_number,
                source_line_ids=list(warning.source_line_ids),
                message=warning.message,
                geometry=warning.geometry.to_dict() if warning.geometry else None,
                resolved=warning.resolved,
            )
        )
    session.flush()
    latest_rows_by_label = {label: rows[-1] for label, rows in rows_by_label.items()}
    persist_structured_evidence(
        session,
        analysis_id,
        result,
        latest_rows_by_label,
        rows_by_key,
    )
