from __future__ import annotations

import json
from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.domain import ProcessingStage, UploadedFileType


class _StrictReviewModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        allow_inf_nan=False,
        str_strip_whitespace=True,
    )


class ExtractionReviewGeometry(_StrictReviewModel):
    x0: float
    top: float
    x1: float
    bottom: float


class ExtractionReviewQuestion(_StrictReviewModel):
    source_record_id: UUID
    included: bool
    parent_source_record_id: UUID | None
    number_label: str = Field(min_length=1, max_length=50)
    question_text: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    marks: float | None = Field(default=None, ge=0)
    sequence: int = Field(ge=0)
    extraction_confidence: float = Field(ge=0, le=1)
    geometry: ExtractionReviewGeometry | None


class ExtractionReviewEvidence(_StrictReviewModel):
    source_record_id: UUID
    included: bool
    question_source_record_id: UUID | None
    source_document: UploadedFileType
    evidence_type: str = Field(min_length=1, max_length=100)
    page_number: int = Field(ge=1)
    item_reference: str = Field(min_length=1, max_length=100)
    extracted_text: str = Field(min_length=1)
    extraction_confidence: float = Field(ge=0, le=1)
    geometry: ExtractionReviewGeometry | None


class ExtractionReviewClo(_StrictReviewModel):
    source_record_id: UUID
    included: bool
    code: str = Field(min_length=1, max_length=50)
    text: str = Field(min_length=1)
    program_outcome_reference: str | None = Field(default=None, min_length=1, max_length=50)
    page_number: int = Field(ge=1)
    extraction_confidence: float = Field(ge=0, le=1)
    geometry: ExtractionReviewGeometry | None


class ExtractionReviewTopic(_StrictReviewModel):
    source_record_id: UUID
    included: bool
    code: str | None = Field(default=None, min_length=1, max_length=50)
    text: str = Field(min_length=1)
    expected_hours: float | None = Field(default=None, ge=0)
    page_number: int = Field(ge=1)
    extraction_confidence: float = Field(ge=0, le=1)
    geometry: ExtractionReviewGeometry | None


class ExtractionReviewAssessmentRecord(_StrictReviewModel):
    source_record_id: UUID
    included: bool
    method: str = Field(min_length=1, max_length=200)
    activity: str | None = Field(default=None, min_length=1, max_length=200)
    percentage: float | None = Field(default=None, ge=0, le=100)
    page_number: int = Field(ge=1)
    extraction_confidence: float = Field(ge=0, le=1)
    geometry: ExtractionReviewGeometry | None


class ExtractionReviewSnapshot(_StrictReviewModel):
    """A complete, versioned snapshot of source-faithful extraction rows.

    Collections may be empty. A snapshot records only entities and evidence
    that genuinely exist when it is created; callers must never fabricate
    placeholder questions, CLOs, topics, or assessment records.
    """

    schema_version: Literal[1]
    questions: list[ExtractionReviewQuestion]
    evidence: list[ExtractionReviewEvidence]
    clos: list[ExtractionReviewClo]
    topics: list[ExtractionReviewTopic]
    assessment_records: list[ExtractionReviewAssessmentRecord]

    @model_validator(mode="after")
    def validate_source_references(self) -> Self:
        collections = {
            "question": [item.source_record_id for item in self.questions],
            "evidence": [item.source_record_id for item in self.evidence],
            "CLO": [item.source_record_id for item in self.clos],
            "topic": [item.source_record_id for item in self.topics],
            "assessment record": [item.source_record_id for item in self.assessment_records],
        }
        for label, record_ids in collections.items():
            if len(record_ids) != len(set(record_ids)):
                raise ValueError(f"{label} source_record_id values must be unique.")

        questions_by_id = {item.source_record_id: item for item in self.questions}
        for question in self.questions:
            parent_id = question.parent_source_record_id
            if parent_id is None:
                continue
            parent = questions_by_id.get(parent_id)
            if parent is None:
                raise ValueError("Question parent references must resolve within the snapshot.")
            if question.included and not parent.included:
                raise ValueError("An included question cannot reference an excluded parent.")

        for evidence in self.evidence:
            question_id = evidence.question_source_record_id
            if question_id is None:
                continue
            referenced_question = questions_by_id.get(question_id)
            if referenced_question is None:
                raise ValueError("Evidence question references must resolve within the snapshot.")
            if evidence.included and not referenced_question.included:
                raise ValueError("Included evidence cannot reference an excluded question.")

        return self


class ExtractionReviewWarning(_StrictReviewModel):
    code: str = Field(min_length=1, max_length=100)
    severity: Literal["info", "warning"]
    collection: Literal[
        "questions",
        "evidence",
        "clos",
        "topics",
        "assessment_records",
        "review",
    ]
    source_record_id: UUID | None
    message: str = Field(min_length=1, max_length=500)


class ExtractionReviewResponse(_StrictReviewModel):
    analysis_id: UUID
    revision_id: UUID
    revision_number: int = Field(ge=1)
    created_at: datetime
    snapshot: ExtractionReviewSnapshot
    original_snapshot: ExtractionReviewSnapshot
    confirmed_revision_id: UUID | None
    is_confirmed: bool
    can_edit: bool
    can_confirm: bool
    warnings: list[ExtractionReviewWarning]
    confirmation_blockers: list[str]


class _ReviewRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ExtractionReviewUpdateRequest(_ReviewRequestModel):
    base_revision_id: UUID
    snapshot: ExtractionReviewSnapshot

    @field_validator("snapshot", mode="before")
    @classmethod
    def parse_snapshot_as_strict_json(cls, value: object) -> ExtractionReviewSnapshot:
        if isinstance(value, ExtractionReviewSnapshot):
            return value
        return ExtractionReviewSnapshot.model_validate_json(json.dumps(value))


class ExtractionReviewConfirmRequest(_ReviewRequestModel):
    revision_id: UUID


class ExtractionReviewConfirmResponse(_StrictReviewModel):
    analysis_id: UUID
    confirmed_revision_id: UUID
    confirmed_revision_number: int = Field(ge=1)
    state: ProcessingStage
