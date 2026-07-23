from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class ExtractionError(RuntimeError):
    """Raised when a digital PDF cannot be parsed. The processing pipeline
    converts any exception (including this one) to a fixed safe failure
    message before it reaches the client - callers must not surface this
    message's text directly."""


@dataclass(frozen=True)
class Geometry:
    x0: float
    top: float
    x1: float
    bottom: float

    def to_dict(self) -> dict[str, float]:
        return {"x0": self.x0, "top": self.top, "x1": self.x1, "bottom": self.bottom}


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
class Tp153MissingEvidence:
    """One of the required TP-153 sections (clos/topics/assessment_records)
    yielded zero records - a real fact worth recording as evidence, not an
    error and never a reason to invent a placeholder domain row."""

    section: str
    page_number: int
    note: str


@dataclass(frozen=True)
class Tp153ExtractionResult:
    clos: list[ExtractedClo]
    topics: list[ExtractedTopic]
    assessment_records: list[ExtractedAssessmentRecord]
    missing_sections: list[Tp153MissingEvidence]


class Tp153Extractor(Protocol):
    def extract(self, pdf_path: Path) -> Tp153ExtractionResult: ...
