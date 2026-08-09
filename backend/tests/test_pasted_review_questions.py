from __future__ import annotations

import uuid

from app.core.domain import (
    QuestionPreparationMode,
    QuestionReviewStatus,
    QuestionType,
    UploadedFileType,
)
from app.schemas.extraction_review import ExtractionReviewSnapshot
from app.services.extraction.review_workflow import validate_source_faithful_snapshot


def _id(value: int) -> uuid.UUID:
    return uuid.UUID(int=value)


def _original() -> ExtractionReviewSnapshot:
    question_id = _id(1)
    return ExtractionReviewSnapshot.model_validate(
        {
            "schema_version": 2,
            "preparation_mode": QuestionPreparationMode.ASSISTED_PDF,
            "questions": [
                {
                    "source_record_id": question_id,
                    "included": True,
                    "parent_source_record_id": None,
                    "number_label": "Q1",
                    "question_text": "Machine draft",
                    "page_number": 1,
                    "marks": 2.0,
                    "sequence": 1,
                    "extraction_confidence": 0.9,
                    "geometry": {"x0": 10.0, "top": 20.0, "x1": 100.0, "bottom": 40.0},
                    "question_type": QuestionType.SHORT_ANSWER,
                    "instructions": None,
                    "extraction_method": "pdfplumber",
                    "review_status": QuestionReviewStatus.MACHINE_EXTRACTED,
                }
            ],
            "question_options": [],
            "question_blanks": [],
            "question_source_spans": [],
            "extraction_warnings": [],
            "evidence": [
                {
                    "source_record_id": _id(2),
                    "included": True,
                    "question_source_record_id": question_id,
                    "source_document": UploadedFileType.EXAM,
                    "evidence_type": "question_text",
                    "page_number": 1,
                    "item_reference": "Q1",
                    "extracted_text": "Machine draft",
                    "extraction_confidence": 0.9,
                    "geometry": {"x0": 10.0, "top": 20.0, "x1": 100.0, "bottom": 40.0},
                }
            ],
            "clos": [],
            "topics": [],
            "assessment_records": [],
            "supporting_materials": [],
            "supporting_annotations": [],
            "document_references": [],
            "reference_associations": [],
        }
    )


def test_assisted_review_can_replace_visible_draft_with_source_faithful_pasted_question() -> None:
    original = _original()
    candidate = original.model_copy(deep=True)
    candidate.questions[0].included = False
    candidate.evidence[0].included = False

    pasted_question_id = uuid.UUID(int=3)
    candidate.questions.append(
        candidate.questions[0].model_copy(
            update={
                "source_record_id": pasted_question_id,
                "included": True,
                "number_label": "Q1",
                "question_text": "Pasted source-faithful question",
                "marks": 3.0,
                "sequence": 2,
                "extraction_confidence": 1.0,
                "geometry": None,
                "extraction_method": "pasted_review",
                "review_status": QuestionReviewStatus.REVIEWED,
            }
        )
    )
    candidate.evidence.append(
        candidate.evidence[0].model_copy(
            update={
                "source_record_id": uuid.UUID(int=4),
                "included": True,
                "question_source_record_id": pasted_question_id,
                "page_number": 1,
                "item_reference": "Q1",
                "extracted_text": "Pasted source-faithful question",
                "extraction_confidence": 1.0,
                "geometry": None,
            }
        )
    )

    validated = validate_source_faithful_snapshot(candidate, original)

    included = [question for question in validated.questions if question.included]
    assert len(included) == 1
    assert included[0].extraction_method == "pasted_review"
    assert included[0].geometry is None
    assert included[0].question_text == "Pasted source-faithful question"
    assert validated.preparation_mode.value == "assisted_pdf"
