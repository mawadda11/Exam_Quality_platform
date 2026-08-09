from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from app.core.domain import (
    ExtractionWarningSeverity,
    QuestionReviewStatus,
    QuestionType,
    ReferenceTargetType,
    SupportingAnnotationType,
    SupportingMaterialType,
)
from app.services.extraction.language_detection import TextLanguage


class ExtractionError(RuntimeError):
    """Raised when a PDF cannot be parsed safely.

    The processing pipeline converts any exception (including this one) to a
    fixed safe failure message before it reaches the client. Callers must not
    surface this message's text directly.
    """


@dataclass(frozen=True)
class Geometry:
    x0: float
    top: float
    x1: float
    bottom: float

    def to_dict(self) -> dict[str, float]:
        return {"x0": self.x0, "top": self.top, "x1": self.x1, "bottom": self.bottom}


@dataclass(frozen=True)
class PageExtractionDiagnostic:
    page_number: int
    language: TextLanguage
    language_confidence: float
    extraction_method: str
    text_quality_confidence: float
    review_recommended: bool
    reason: str


@dataclass(frozen=True)
class ExtractedSourceToken:
    token_id: str
    original_text: str
    geometry: Geometry | None
    confidence: float | None


@dataclass(frozen=True)
class ExtractedSourceLine:
    source_line_id: str
    provider: str
    provider_version: str | None
    page_number: int
    reading_order: int
    original_text: str
    geometry: Geometry | None
    confidence: float | None
    extraction_method: str
    language: str | None = None
    tokens: tuple[ExtractedSourceToken, ...] = ()
    page_width: float | None = None
    page_height: float | None = None
    # Exact provider/native line before geometry-aware reading-order repair.
    # ``original_text`` is the source-faithful logical reading text used by
    # extraction/reconciliation; this keeps the untouched PDF order available
    # for audit without feeding visual-order Arabic back into canonical text.
    raw_text: str | None = None


@dataclass(frozen=True)
class ExtractionReconciliationWarning:
    code: str
    severity: ExtractionWarningSeverity
    message: str
    page_number: int | None
    source_line_ids: tuple[str, ...] = ()
    geometry: Geometry | None = None
    resolved: bool = False


@dataclass(frozen=True)
class ExtractedQuestionOption:
    local_key: str
    question_local_key: str
    option_label: str
    option_text: str
    sequence: int
    page_number: int
    confidence: float
    geometry: Geometry | None
    source_line_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtractedQuestionBlank:
    question_local_key: str
    blank_index: int
    source_text: str | None
    page_number: int
    geometry: Geometry | None


@dataclass(frozen=True)
class ExtractedQuestion:
    number_label: str
    text: str
    page_number: int
    parent_number_label: str | None
    marks: float | None
    sequence: int
    confidence: float
    geometry: Geometry | None
    local_key: str | None = None
    parent_local_key: str | None = None
    question_type: QuestionType = QuestionType.UNKNOWN
    instructions: str | None = None
    extraction_method: str = "direct_text"
    review_status: QuestionReviewStatus = QuestionReviewStatus.MACHINE_EXTRACTED
    source_line_ids: tuple[str, ...] = ()
    options: tuple[ExtractedQuestionOption, ...] = ()
    blanks: tuple[ExtractedQuestionBlank, ...] = ()
    supporting_material_local_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtractedEvidence:
    evidence_type: str
    page_number: int
    item_reference: str
    extracted_text: str
    confidence: float
    geometry: Geometry | None
    question_number_label: str | None
    question_local_key: str | None = None


@dataclass(frozen=True)
class ExtractedTableCell:
    row_index: int
    column_index: int
    original_text: str
    page_number: int
    geometry: Geometry | None
    confidence: float
    source_line_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtractedSupportingMaterial:
    local_key: str
    material_type: SupportingMaterialType
    page_number: int
    source_text: str
    confidence: float
    geometry: Geometry | None
    extraction_method: str
    question_number_label: str | None = None
    question_local_key: str | None = None
    cells: tuple[ExtractedTableCell, ...] = ()


@dataclass(frozen=True)
class ExtractedSupportingAnnotation:
    local_key: str
    material_local_key: str | None
    annotation_type: SupportingAnnotationType
    original_text: str
    normalized_label: str | None
    page_number: int
    confidence: float
    geometry: Geometry | None
    extraction_method: str


@dataclass(frozen=True)
class ExtractedDocumentReference:
    local_key: str
    target_type: ReferenceTargetType
    original_text: str
    target_label: str
    normalized_target_label: str
    page_number: int
    confidence: float
    geometry: Geometry | None
    extraction_method: str
    question_number_label: str | None = None
    question_local_key: str | None = None


@dataclass(frozen=True)
class ExtractedStructureCandidate:
    candidate_id: str
    pipeline: str
    item_kind: str
    page_number: int
    original_text: str
    geometry: Geometry | None
    confidence: float
    question_local_key: str | None = None
    source_line_ids: tuple[str, ...] = ()
    provenance: str = "local_only"


@dataclass(frozen=True)
class ExtractionResult:
    questions: list[ExtractedQuestion]
    evidence: list[ExtractedEvidence]
    document_language: TextLanguage = TextLanguage.UNKNOWN
    page_diagnostics: list[PageExtractionDiagnostic] = field(default_factory=list)
    supporting_materials: list[ExtractedSupportingMaterial] = field(default_factory=list)
    supporting_annotations: list[ExtractedSupportingAnnotation] = field(default_factory=list)
    document_references: list[ExtractedDocumentReference] = field(default_factory=list)
    source_lines: list[ExtractedSourceLine] = field(default_factory=list)
    reconciliation_warnings: list[ExtractionReconciliationWarning] = field(default_factory=list)
    structure_candidates: list[ExtractedStructureCandidate] = field(default_factory=list)


class ExamExtractor(Protocol):
    def extract(self, pdf_path: Path) -> ExtractionResult: ...


@dataclass(frozen=True)
class ExtractedClo:
    code: str
    text: str
    program_outcome_reference: str | None
    page_number: int
    confidence: float
    geometry: Geometry | None
    source_text: str | None = None
    extraction_method: str = "direct_text"


@dataclass(frozen=True)
class ExtractedTopic:
    code: str | None
    text: str
    expected_hours: float | None
    page_number: int
    confidence: float
    geometry: Geometry | None
    source_text: str | None = None
    extraction_method: str = "direct_text"


@dataclass(frozen=True)
class ExtractedAssessmentRecord:
    method: str
    activity: str | None
    percentage: float | None
    page_number: int
    confidence: float
    geometry: Geometry | None
    source_text: str | None = None
    extraction_method: str = "direct_text"
    related_clo_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtractedCourseField:
    field_name: str
    value: str
    page_number: int
    confidence: float
    geometry: Geometry | None


@dataclass(frozen=True)
class Tp153MissingEvidence:
    """A required Course Specification section yielded zero records.

    This is a source fact worth recording as evidence, not an error and never
    a reason to invent a placeholder domain row.
    """

    section: str
    page_number: int
    note: str


@dataclass(frozen=True)
class CourseSpecificationWarning:
    code: str
    page_number: int
    message: str
    confidence: float


@dataclass(frozen=True)
class Tp153ExtractionResult:
    clos: list[ExtractedClo]
    topics: list[ExtractedTopic]
    assessment_records: list[ExtractedAssessmentRecord]
    missing_sections: list[Tp153MissingEvidence]
    course_fields: list[ExtractedCourseField] = field(default_factory=list)
    layout_family: str = "unknown"
    document_language: TextLanguage = TextLanguage.UNKNOWN
    page_diagnostics: list[PageExtractionDiagnostic] = field(default_factory=list)
    review_warnings: list[CourseSpecificationWarning] = field(default_factory=list)


class Tp153Extractor(Protocol):
    def extract(self, pdf_path: Path) -> Tp153ExtractionResult: ...
