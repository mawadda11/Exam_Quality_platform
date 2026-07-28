from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

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
class ExtractedQuestion:
    number_label: str
    text: str
    page_number: int
    parent_number_label: str | None
    marks: float | None
    sequence: int
    confidence: float
    geometry: Geometry | None


@dataclass(frozen=True)
class ExtractedEvidence:
    evidence_type: str
    page_number: int
    item_reference: str
    extracted_text: str
    confidence: float
    geometry: Geometry | None
    question_number_label: str | None


@dataclass(frozen=True)
class ExtractionResult:
    questions: list[ExtractedQuestion]
    evidence: list[ExtractedEvidence]
    document_language: TextLanguage = TextLanguage.UNKNOWN
    page_diagnostics: list[PageExtractionDiagnostic] = field(default_factory=list)


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


@dataclass(frozen=True)
class ExtractedTopic:
    code: str | None
    text: str
    expected_hours: float | None
    page_number: int
    confidence: float
    geometry: Geometry | None


@dataclass(frozen=True)
class ExtractedAssessmentRecord:
    method: str
    activity: str | None
    percentage: float | None
    page_number: int
    confidence: float
    geometry: Geometry | None


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
class Tp153ExtractionResult:
    clos: list[ExtractedClo]
    topics: list[ExtractedTopic]
    assessment_records: list[ExtractedAssessmentRecord]
    missing_sections: list[Tp153MissingEvidence]
    course_fields: list[ExtractedCourseField] = field(default_factory=list)
    layout_family: str = "unknown"
    document_language: TextLanguage = TextLanguage.UNKNOWN
    page_diagnostics: list[PageExtractionDiagnostic] = field(default_factory=list)


class Tp153Extractor(Protocol):
    def extract(self, pdf_path: Path) -> Tp153ExtractionResult: ...
