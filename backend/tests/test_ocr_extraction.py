"""Tests for PdfPlumberExamExtractor's OCR fallback (SRS FR-006).

Two kinds of test here, deliberately kept separate:
- Fake-engine tests: inject a fake OcrEngine (no real Tesseract call), proving
  the *dispatch contract* - a page with real digital text never invokes OCR
  at all, a page with none does, and parent-label/sequence state threads
  correctly across a mixed digital+scanned document. These always run.
- One real, live test using the actual TesseractOcrEngine against a genuinely
  rasterized, text-layer-free PDF (tests/pdf_fixtures.build_scanned_looking_
  exam_pdf). It's skipped when the `tesseract` binary isn't on PATH, since
  pytesseract only wraps that external CLI tool - it is not a pip-installable
  guarantee the way pdfplumber/fpdf2 are. See backend/Dockerfile and
  .github/workflows/ci.yml for where the tesseract-ocr system package is
  installed so this test runs for real there.

Live verification note (not asserted by any test): running this real test
against build_scanned_looking_exam_pdf() correctly recovers Q1 (5 marks), Q2,
and Q2(a) (3 marks) with ~93-96% confidence. Q2(b) is a genuine, reproducible
Tesseract misread at this fixture's rendering ("(b)" recognized as "(ob)",
confirmed unchanged across --psm 3/4/6) - not a bug in the classification or
grouping logic, and not something this system should paper over with ad-hoc
regex tolerance for OCR noise. It is real evidence of OCR's inherent
imperfection versus native digital text extraction, so only the reliably-
reproduced questions are asserted below.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from pdf_fixtures import (
    build_completely_blank_pdf,
    build_digital_page_then_blank_page_pdf,
    build_scanned_looking_exam_pdf,
    build_synthetic_exam_pdf,
)

from app.services.extraction.digital_pdf_extractor import PdfPlumberExamExtractor
from app.services.extraction.line_classification import LineKind, classify_line
from app.services.extraction.ocr import OcrLine
from app.services.extraction.types import Geometry

_TESSERACT_AVAILABLE = shutil.which("tesseract") is not None


class _FakeOcrEngine:
    """Returns pre-canned OcrLine records instead of calling real Tesseract -
    lets the dispatch/classification/state-threading contract be tested
    without needing the tesseract binary installed."""

    def __init__(self, lines_by_call: list[list[OcrLine]]) -> None:
        self._lines_by_call = list(lines_by_call)
        self.call_count = 0

    def lines_for_image(self, image: object, scale: float) -> list[OcrLine]:
        lines = self._lines_by_call[self.call_count]
        self.call_count += 1
        return lines


def _ocr_line(text: str) -> OcrLine:
    return OcrLine(text=text, geometry=Geometry(x0=0, top=0, x1=1, bottom=1), confidence=0.9)


def _write_pdf(tmp_path: Path, name: str, content: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(content)
    return path


def test_page_with_digital_text_never_invokes_ocr_engine(tmp_path: Path) -> None:
    fake_engine = _FakeOcrEngine(lines_by_call=[])
    pdf_path = _write_pdf(tmp_path, "digital.pdf", build_synthetic_exam_pdf())

    result = PdfPlumberExamExtractor(ocr_engine=fake_engine).extract(pdf_path)

    assert fake_engine.call_count == 0
    assert len(result.questions) == 8  # matches the fixture's known digital-path count


def test_page_with_no_extractable_text_invokes_injected_ocr_engine(tmp_path: Path) -> None:
    fake_engine = _FakeOcrEngine(
        lines_by_call=[
            [
                _ocr_line("Q1. What is a primary key? [4 marks]"),
                _ocr_line("(a) Give one example. [2 marks]"),
            ]
        ]
    )
    pdf_path = _write_pdf(tmp_path, "blank.pdf", build_completely_blank_pdf())

    result = PdfPlumberExamExtractor(ocr_engine=fake_engine).extract(pdf_path)

    assert fake_engine.call_count == 1
    labels = [q.number_label for q in result.questions]
    assert labels == ["Q1", "Q1(a)"]
    assert result.questions[0].marks == 4.0
    assert result.questions[1].marks == 2.0
    # OCR-sourced confidence is the engine's own value, not the digital
    # path's binary 1.0/0.6 placeholder.
    assert result.questions[0].confidence == 0.9


def test_parent_label_and_sequence_thread_across_a_digital_to_ocr_page_break(
    tmp_path: Path,
) -> None:
    """Page 1 (digital) ends mid-question ("Q2." + "(a)"); page 2 is a
    genuinely blank page that triggers the OCR-fallback path. The injected
    fake engine ignores the (blank) page image and returns a canned "(b)"
    line, so this only needs real OCR dispatch to work correctly, not real
    text recognition - proving current_parent_label ("Q2") and the running
    sequence counter both survive a real digital-to-OCR page transition via
    the actual public extract() path, not just within one page/source type."""
    fake_engine = _FakeOcrEngine(lines_by_call=[[_ocr_line("(b) Second subpart. [2 marks]")]])
    pdf_path = _write_pdf(tmp_path, "mixed.pdf", build_digital_page_then_blank_page_pdf())

    result = PdfPlumberExamExtractor(ocr_engine=fake_engine).extract(pdf_path)

    assert fake_engine.call_count == 1
    labels = [q.number_label for q in result.questions]
    assert labels == ["Q2", "Q2(a)", "Q2(b)"]
    assert [q.sequence for q in result.questions] == [1, 2, 3]
    assert result.questions[2].parent_number_label == "Q2"


@pytest.mark.skipif(not _TESSERACT_AVAILABLE, reason="tesseract binary not installed on PATH")
def test_real_tesseract_ocr_recovers_questions_from_a_genuinely_scanned_page(
    tmp_path: Path,
) -> None:
    pdf_path = _write_pdf(tmp_path, "scanned.pdf", build_scanned_looking_exam_pdf())

    result = PdfPlumberExamExtractor().extract(pdf_path)

    by_label = {q.number_label: q for q in result.questions}
    assert "Q1" in by_label
    assert by_label["Q1"].marks == 5.0
    assert "database" in by_label["Q1"].text.lower()
    assert "Q2" in by_label
    assert "Q2(a)" in by_label
    assert by_label["Q2(a)"].marks == 3.0
    assert by_label["Q2(a)"].parent_number_label == "Q2"
    for question in result.questions:
        assert 0.0 < question.confidence <= 1.0


def test_classify_line_still_used_directly_by_ocr_path_for_other_lines() -> None:
    # A quick guard that OTHER-kind OCR lines (e.g. OCR noise/empty artifacts
    # that survived word-grouping) are dropped rather than persisted -
    # exercised here at the classification level since it's the same shared
    # function the OCR path calls per-line.
    classified = classify_line("###", current_parent_label=None)
    assert classified.kind is LineKind.OTHER
