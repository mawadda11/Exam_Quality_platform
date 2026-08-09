from __future__ import annotations

import json
from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.domain import (
    AssociationBasis,
    ExtractionWarningSeverity,
    ProcessingStage,
    QuestionPreparationMode,
    QuestionReviewStatus,
    QuestionType,
    ReferenceResolutionStatus,
    ReferenceTargetType,
    SupportingAnnotationType,
    SupportingMaterialType,
    UploadedFileType,
)


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
    question_type: QuestionType = QuestionType.UNKNOWN
    instructions: str | None = None
    extraction_method: str = Field(default="legacy", min_length=1, max_length=30)
    review_status: QuestionReviewStatus = QuestionReviewStatus.REVIEWED


class ExtractionReviewQuestionOption(_StrictReviewModel):
    source_record_id: UUID
    included: bool
    question_source_record_id: UUID
    option_label: str = Field(min_length=1, max_length=50)
    option_text: str = Field(min_length=1)
    sequence: int = Field(ge=0)
    page_number: int = Field(ge=1)
    extraction_confidence: float = Field(ge=0, le=1)
    geometry: ExtractionReviewGeometry | None


class ExtractionReviewQuestionBlank(_StrictReviewModel):
    source_record_id: UUID
    included: bool
    question_source_record_id: UUID
    blank_index: int = Field(ge=1)
    source_text: str | None = Field(default=None, min_length=1)
    page_number: int = Field(ge=1)
    geometry: ExtractionReviewGeometry | None


class ExtractionReviewQuestionSourceSpan(_StrictReviewModel):
    source_record_id: UUID
    question_source_record_id: UUID
    option_source_record_id: UUID | None
    provider: str = Field(min_length=1, max_length=50)
    provider_version: str | None = Field(default=None, max_length=100)
    source_line_id: str = Field(min_length=1, max_length=100)
    original_text: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    geometry: ExtractionReviewGeometry | None
    extraction_confidence: float | None = Field(default=None, ge=0, le=1)
    extraction_method: str = Field(min_length=1, max_length=30)


class ExtractionReviewExtractionWarning(_StrictReviewModel):
    source_record_id: UUID
    code: str = Field(min_length=1, max_length=100)
    severity: ExtractionWarningSeverity
    page_number: int | None = Field(default=None, ge=1)
    source_line_ids: list[str]
    message: str = Field(min_length=1)
    geometry: ExtractionReviewGeometry | None
    resolved: bool


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
    related_clo_codes: list[str] = Field(default_factory=list)
    page_number: int = Field(ge=1)
    extraction_confidence: float = Field(ge=0, le=1)
    geometry: ExtractionReviewGeometry | None


class ExtractionReviewSupportingMaterial(_StrictReviewModel):
    source_record_id: UUID
    included: bool
    question_source_record_id: UUID | None
    source_document: UploadedFileType
    material_type: SupportingMaterialType
    source_text: str
    page_number: int = Field(ge=1)
    extraction_confidence: float = Field(ge=0, le=1)
    extraction_method: str = Field(min_length=1, max_length=20)
    geometry: ExtractionReviewGeometry | None


class ExtractionReviewSupportingAnnotation(_StrictReviewModel):
    source_record_id: UUID
    included: bool
    material_source_record_id: UUID | None
    source_document: UploadedFileType
    annotation_type: SupportingAnnotationType
    original_text: str = Field(min_length=1)
    normalized_label: str | None = Field(default=None, min_length=1, max_length=100)
    page_number: int = Field(ge=1)
    extraction_confidence: float = Field(ge=0, le=1)
    extraction_method: str = Field(min_length=1, max_length=20)
    geometry: ExtractionReviewGeometry | None


class ExtractionReviewDocumentReference(_StrictReviewModel):
    source_record_id: UUID
    included: bool
    question_source_record_id: UUID | None
    source_document: UploadedFileType
    target_type: ReferenceTargetType
    original_text: str = Field(min_length=1)
    target_label: str = Field(min_length=1, max_length=100)
    normalized_target_label: str = Field(min_length=1, max_length=100)
    resolution_status: ReferenceResolutionStatus
    page_number: int = Field(ge=1)
    extraction_confidence: float = Field(ge=0, le=1)
    extraction_method: str = Field(min_length=1, max_length=20)
    geometry: ExtractionReviewGeometry | None


class ExtractionReviewReferenceAssociation(_StrictReviewModel):
    source_record_id: UUID
    reference_source_record_id: UUID
    target_material_source_record_id: UUID | None
    target_question_source_record_id: UUID | None
    basis: AssociationBasis
    extraction_confidence: float = Field(ge=0, le=1)
    proximity_distance: float | None = Field(default=None, ge=0)
    exact_label_match: bool
    selected: bool
    ambiguity_reason: str | None = Field(default=None, max_length=500)


class ExtractionReviewSnapshot(_StrictReviewModel):
    """A complete, versioned snapshot of source-faithful extraction rows.

    Collections may be empty. A snapshot records only entities and evidence
    that genuinely exist when it is created. Manual PDF questions require a
    selected region of the immutable exam PDF. Structured-template questions
    require a source page and matching exam question_text evidence but never
    invent PDF geometry. Placeholder CLOs, topics, assessment records, or
    untraceable questions remain prohibited.
    """

    schema_version: Literal[1, 2]
    preparation_mode: QuestionPreparationMode = QuestionPreparationMode.ASSISTED_PDF
    questions: list[ExtractionReviewQuestion]
    question_options: list[ExtractionReviewQuestionOption] = Field(default_factory=list)
    question_blanks: list[ExtractionReviewQuestionBlank] = Field(default_factory=list)
    question_source_spans: list[ExtractionReviewQuestionSourceSpan] = Field(default_factory=list)
    extraction_warnings: list[ExtractionReviewExtractionWarning] = Field(default_factory=list)
    evidence: list[ExtractionReviewEvidence]
    clos: list[ExtractionReviewClo]
    topics: list[ExtractionReviewTopic]
    assessment_records: list[ExtractionReviewAssessmentRecord]
    supporting_materials: list[ExtractionReviewSupportingMaterial] = Field(default_factory=list)
    supporting_annotations: list[ExtractionReviewSupportingAnnotation] = Field(default_factory=list)
    document_references: list[ExtractionReviewDocumentReference] = Field(default_factory=list)
    reference_associations: list[ExtractionReviewReferenceAssociation] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_source_references(self) -> Self:
        collections = {
            "question": [item.source_record_id for item in self.questions],
            "question option": [item.source_record_id for item in self.question_options],
            "question blank": [item.source_record_id for item in self.question_blanks],
            "question source span": [item.source_record_id for item in self.question_source_spans],
            "extraction warning": [item.source_record_id for item in self.extraction_warnings],
            "evidence": [item.source_record_id for item in self.evidence],
            "CLO": [item.source_record_id for item in self.clos],
            "topic": [item.source_record_id for item in self.topics],
            "assessment record": [item.source_record_id for item in self.assessment_records],
            "supporting material": [item.source_record_id for item in self.supporting_materials],
            "supporting annotation": [
                item.source_record_id for item in self.supporting_annotations
            ],
            "document reference": [item.source_record_id for item in self.document_references],
            "reference association": [
                item.source_record_id for item in self.reference_associations
            ],
        }
        for label, record_ids in collections.items():
            if len(record_ids) != len(set(record_ids)):
                raise ValueError(f"{label} source_record_id values must be unique.")

        questions_by_id = {item.source_record_id: item for item in self.questions}
        options_by_id = {item.source_record_id: item for item in self.question_options}
        for question in self.questions:
            parent_id = question.parent_source_record_id
            if parent_id is None:
                continue
            parent = questions_by_id.get(parent_id)
            if parent is None:
                raise ValueError("Question parent references must resolve within the snapshot.")
            if question.included and not parent.included:
                raise ValueError("An included question cannot reference an excluded parent.")
        for question in self.questions:
            visited = {question.source_record_id}
            parent_id = question.parent_source_record_id
            while parent_id is not None:
                if parent_id in visited:
                    raise ValueError("Question hierarchy must not contain a cycle.")
                visited.add(parent_id)
                parent_id = questions_by_id[parent_id].parent_source_record_id

        for option in self.question_options:
            option_question = questions_by_id.get(option.question_source_record_id)
            if option_question is None:
                raise ValueError("Question-option links must resolve within the snapshot.")
            if option.included and not option_question.included:
                raise ValueError("An included option cannot reference an excluded question.")
        for blank in self.question_blanks:
            blank_question = questions_by_id.get(blank.question_source_record_id)
            if blank_question is None:
                raise ValueError("Question-blank links must resolve within the snapshot.")
            if blank.included and not blank_question.included:
                raise ValueError("An included blank cannot reference an excluded question.")
        for span in self.question_source_spans:
            if span.question_source_record_id not in questions_by_id:
                raise ValueError("Question-source-span question links must resolve.")
            if span.option_source_record_id is not None:
                span_option = options_by_id.get(span.option_source_record_id)
                if (
                    span_option is None
                    or span_option.question_source_record_id != span.question_source_record_id
                ):
                    raise ValueError("Question-source-span option links must resolve.")

        for evidence in self.evidence:
            question_id = evidence.question_source_record_id
            if question_id is None:
                continue
            referenced_question = questions_by_id.get(question_id)
            if referenced_question is None:
                raise ValueError("Evidence question references must resolve within the snapshot.")
            if evidence.included and not referenced_question.included:
                raise ValueError("Included evidence cannot reference an excluded question.")

        materials_by_id = {item.source_record_id: item for item in self.supporting_materials}
        references_by_id = {item.source_record_id: item for item in self.document_references}
        for material in self.supporting_materials:
            question_id = material.question_source_record_id
            if question_id is not None and question_id not in questions_by_id:
                raise ValueError("Supporting-material question references must resolve.")
        for annotation in self.supporting_annotations:
            material_id = annotation.material_source_record_id
            if material_id is not None and material_id not in materials_by_id:
                raise ValueError("Annotation material references must resolve.")
            if (
                annotation.included
                and material_id is not None
                and not materials_by_id[material_id].included
            ):
                raise ValueError("An included annotation cannot reference an excluded material.")
        for reference in self.document_references:
            question_id = reference.question_source_record_id
            if question_id is not None and question_id not in questions_by_id:
                raise ValueError("Document-reference question links must resolve.")
        for association in self.reference_associations:
            if association.reference_source_record_id not in references_by_id:
                raise ValueError("Association reference links must resolve.")
            material_id = association.target_material_source_record_id
            question_id = association.target_question_source_record_id
            if (material_id is None) == (question_id is None):
                raise ValueError("An association must reference exactly one target.")
            if material_id is not None and material_id not in materials_by_id:
                raise ValueError("Association material targets must resolve.")
            if question_id is not None and question_id not in questions_by_id:
                raise ValueError("Association question targets must resolve.")

        return self


class ExtractionReviewWarning(_StrictReviewModel):
    code: str = Field(min_length=1, max_length=100)
    severity: Literal["info", "warning", "critical"]
    collection: Literal[
        "questions",
        "question_options",
        "question_blanks",
        "extraction_warnings",
        "evidence",
        "clos",
        "topics",
        "assessment_records",
        "supporting_materials",
        "supporting_annotations",
        "document_references",
        "reference_associations",
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
    blocking_extraction_warning_ids: list[UUID] = Field(default_factory=list)


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
