"""Digital, text-based TP-153 extractor.

Reads only a PDF's existing text layer via pdfplumber - it never performs
OCR. A page with no extractable text simply contributes nothing.

Parsing is a deterministic, regex-based heuristic, not a statistical model,
built around three section headers and one line pattern per section:
- "Course Learning Outcomes" section: lines matching "CLO<n>: <text> [PLO<n>]"
  (the bracketed program-outcome reference is optional).
- "Course Topics" section: lines matching "T<n>: <text> - <n> hours".
- "Assessment Methods" section: lines matching
  "Method: <method> | Activity: <activity> | Percentage: <n>%"; a line
  missing the "| Percentage: ...%" segment still yields a record with
  percentage=None rather than being dropped.

Confidence reflects whether the text match and the position (geometry)
match agreed, not any statistical certainty. If, after the whole document
is parsed, a required section (CLOs, topics, or assessment records) has
zero rows, that is recorded as a Tp153MissingEvidence entry - never as an
invented row.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pdfplumber

from app.services.extraction.types import (
    ExtractedAssessmentRecord,
    ExtractedClo,
    ExtractedTopic,
    ExtractionError,
    Geometry,
    Tp153ExtractionResult,
    Tp153MissingEvidence,
)

_CLO_SECTION_HEADER = re.compile(r"^Course Learning Outcomes\s*$", re.IGNORECASE)
_TOPICS_SECTION_HEADER = re.compile(r"^Course Topics\s*$", re.IGNORECASE)
_ASSESSMENT_SECTION_HEADER = re.compile(r"^Assessment Methods\s*$", re.IGNORECASE)

_CLO_LINE = re.compile(r"^CLO(\d+):\s*(.+?)(?:\s*\[(PLO\d+)\])?\s*$")
_TOPIC_LINE = re.compile(r"^T(\d+):\s*(.+?)\s*-\s*(\d+(?:\.\d+)?)\s*hours?\s*$")
_ASSESSMENT_LINE_FULL = re.compile(
    r"^Method:\s*(.+?)\s*\|\s*Activity:\s*(.+?)\s*\|\s*Percentage:\s*(\d+(?:\.\d+)?)%\s*$"
)
_ASSESSMENT_LINE_PARTIAL = re.compile(r"^Method:\s*(.+?)\s*\|\s*Activity:\s*(.+?)\s*$")

_CLO_SEARCH = r"CLO\d+:"
_TOPIC_SEARCH = r"T\d+:"
_ASSESSMENT_SEARCH = r"Method:"

_FULL_CONFIDENCE = 1.0
_NO_GEOMETRY_CONFIDENCE = 0.6

_SECTION_LABELS: dict[str, str] = {
    "clos": "Course Learning Outcomes",
    "topics": "Course Topics",
    "assessment_records": "Assessment Methods",
}


def _geometry_from_match(match: dict[str, Any]) -> Geometry:
    return Geometry(
        x0=float(match["x0"]),
        top=float(match["top"]),
        x1=float(match["x1"]),
        bottom=float(match["bottom"]),
    )


def _next_geometry(matches: Iterator[dict[str, Any]]) -> Geometry | None:
    match = next(matches, None)
    return _geometry_from_match(match) if match is not None else None


def _confidence_for(geometry: Geometry | None) -> float:
    return _FULL_CONFIDENCE if geometry is not None else _NO_GEOMETRY_CONFIDENCE


class PdfPlumberTp153Extractor:
    """Digital-PDF-only TP-153 extractor. See module docstring for the heuristic."""

    def extract(self, pdf_path: Path) -> Tp153ExtractionResult:
        try:
            return self._extract(pdf_path)
        except ExtractionError:
            raise
        except Exception as exc:
            raise ExtractionError(f"Failed to parse digital PDF: {pdf_path.name}") from exc

    def _extract(self, pdf_path: Path) -> Tp153ExtractionResult:
        clos: list[ExtractedClo] = []
        topics: list[ExtractedTopic] = []
        assessment_records: list[ExtractedAssessmentRecord] = []
        current_section: str | None = None
        last_page_number = 1

        with pdfplumber.open(pdf_path) as document:
            for page_index, page in enumerate(document.pages):
                page_number = page_index + 1
                last_page_number = page_number
                text = page.extract_text() or ""
                lines = [line.strip() for line in text.splitlines() if line.strip()]

                clo_matches = iter(page.search(_CLO_SEARCH))
                topic_matches = iter(page.search(_TOPIC_SEARCH))
                assessment_matches = iter(page.search(_ASSESSMENT_SEARCH))

                for line in lines:
                    if _CLO_SECTION_HEADER.match(line):
                        current_section = "clos"
                        continue
                    if _TOPICS_SECTION_HEADER.match(line):
                        current_section = "topics"
                        continue
                    if _ASSESSMENT_SECTION_HEADER.match(line):
                        current_section = "assessment_records"
                        continue

                    if current_section == "clos" and (clo_match := _CLO_LINE.match(line)):
                        geometry = _next_geometry(clo_matches)
                        clos.append(
                            ExtractedClo(
                                code=f"CLO{clo_match.group(1)}",
                                text=clo_match.group(2).strip(),
                                program_outcome_reference=clo_match.group(3),
                                page_number=page_number,
                                confidence=_confidence_for(geometry),
                                geometry=geometry,
                            )
                        )
                    elif current_section == "topics" and (topic_match := _TOPIC_LINE.match(line)):
                        geometry = _next_geometry(topic_matches)
                        topics.append(
                            ExtractedTopic(
                                code=f"T{topic_match.group(1)}",
                                text=topic_match.group(2).strip(),
                                expected_hours=float(topic_match.group(3)),
                                page_number=page_number,
                                confidence=_confidence_for(geometry),
                                geometry=geometry,
                            )
                        )
                    elif current_section == "assessment_records":
                        full_match = _ASSESSMENT_LINE_FULL.match(line)
                        if full_match:
                            geometry = _next_geometry(assessment_matches)
                            assessment_records.append(
                                ExtractedAssessmentRecord(
                                    method=full_match.group(1).strip(),
                                    activity=full_match.group(2).strip(),
                                    percentage=float(full_match.group(3)),
                                    page_number=page_number,
                                    confidence=_confidence_for(geometry),
                                    geometry=geometry,
                                )
                            )
                            continue
                        partial_match = _ASSESSMENT_LINE_PARTIAL.match(line)
                        if partial_match:
                            geometry = _next_geometry(assessment_matches)
                            assessment_records.append(
                                ExtractedAssessmentRecord(
                                    method=partial_match.group(1).strip(),
                                    activity=partial_match.group(2).strip(),
                                    percentage=None,
                                    page_number=page_number,
                                    confidence=_confidence_for(geometry),
                                    geometry=geometry,
                                )
                            )

        section_records: dict[str, list[Any]] = {
            "clos": list(clos),
            "topics": list(topics),
            "assessment_records": list(assessment_records),
        }
        missing_sections = [
            Tp153MissingEvidence(
                section=section,
                page_number=last_page_number,
                note=f"No {label} section was found in the TP-153.",
            )
            for section, label in _SECTION_LABELS.items()
            if not section_records[section]
        ]

        return Tp153ExtractionResult(
            clos=clos,
            topics=topics,
            assessment_records=assessment_records,
            missing_sections=missing_sections,
        )
