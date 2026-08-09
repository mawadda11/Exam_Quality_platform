from __future__ import annotations

from pathlib import Path

from pdf_fixtures import build_completely_blank_pdf
from PIL import Image

from app.services.extraction.digital_pdf_extractor import PdfPlumberExamExtractor
from app.services.extraction.language_detection import TextLanguage, detect_text_language
from app.services.extraction.line_classification import (
    LineKind,
    classify_line,
    parse_declared_total,
)
from app.services.extraction.ocr import OcrLine, resolve_tesseract_languages
from app.services.extraction.text_normalization import (
    normalize_arabic_for_matching,
    parse_localized_number,
    to_ascii_digits,
)
from app.services.extraction.text_quality import assess_text_quality
from app.services.extraction.types import Geometry


class _ArabicFakeOcr:
    def lines_for_image(self, image: Image.Image, scale: float) -> list[OcrLine]:
        geometry = Geometry(x0=20, top=20, x1=450, bottom=40)
        return [
            OcrLine("التعليمات: أجب عن جميع الأسئلة", geometry, 0.92),
            OcrLine("س١. اشرح مفهوم التطبيع [٥ درجات]", geometry, 0.91),
            OcrLine("س٢. أجب عما يلي", geometry, 0.90),
            OcrLine("أ) حدد المفتاح الأساسي [٣ درجات]", geometry, 0.88),
            OcrLine("مجموع الدرجات: ٨", geometry, 0.93),
        ]


def test_arabic_digit_and_matching_normalization_is_conservative() -> None:
    assert to_ascii_digits("١٢۳") == "123"
    assert parse_localized_number("١٢٫٥".replace("٫", ".")) == 12.5
    assert normalize_arabic_for_matching("التَّعليمات：  س١") == "التعليمات: س1"


def test_detects_arabic_english_mixed_and_unknown_text() -> None:
    assert detect_text_language("هذا اختبار عربي").language == TextLanguage.ARABIC
    assert detect_text_language("This is an English exam").language == TextLanguage.ENGLISH
    assert detect_text_language("اكتب Python code").language == TextLanguage.MIXED
    assert detect_text_language("1234").language == TextLanguage.UNKNOWN


def test_classifies_arabic_question_hierarchy_marks_and_total() -> None:
    q1 = classify_line("س١. اشرح التطبيع [٥ درجات]", None)
    q2 = classify_line("السؤال الثاني: اكتب برنامجًا (١٠ درجات)", None)
    child = classify_line("أ) حدد الناتج [٣ درجات]", "Q2")
    instructions = classify_line("التعليمات: أجب عن جميع الأسئلة", None)
    total = classify_line("مجموع الدرجات: ١٨", None)

    assert (q1.kind, q1.number_label, q1.marks.value if q1.marks else None) == (
        LineKind.QUESTION,
        "Q1",
        5.0,
    )
    assert q2.number_label == "Q2"
    assert child.number_label == "Q2(a)"
    assert child.marks is not None and child.marks.value == 3.0
    assert instructions.kind is LineKind.INSTRUCTIONS
    assert total.kind is LineKind.TOTAL_MARKS
    assert parse_declared_total(total.text) == 18.0


def test_arabic_ocr_page_preserves_source_text_geometry_and_diagnostics(tmp_path: Path) -> None:
    pdf_path = tmp_path / "arabic-scanned.pdf"
    pdf_path.write_bytes(build_completely_blank_pdf())

    result = PdfPlumberExamExtractor(ocr_engine=_ArabicFakeOcr()).extract(pdf_path)

    assert [question.number_label for question in result.questions] == ["Q1", "Q2", "Q2(a)"]
    assert result.questions[0].text == "س١. اشرح مفهوم التطبيع [٥ درجات]"
    assert result.questions[0].marks == 5.0
    assert result.questions[2].parent_number_label == "Q2"
    assert all(question.geometry is not None for question in result.questions)
    assert result.document_language == TextLanguage.ARABIC
    assert result.page_diagnostics[0].extraction_method == "ocr"
    assert result.page_diagnostics[0].review_recommended is False
    assert any(item.evidence_type == "declared_total" for item in result.evidence)


def test_direct_text_quality_gate_routes_tiny_or_garbled_text_to_ocr() -> None:
    assert assess_text_quality("").usable is False
    assert assess_text_quality("1").usable is False
    assert assess_text_quality("\ufffd" * 30).usable is False
    quality = assess_text_quality("Question 1. Explain database normalization in detail.")
    assert quality.usable is True


def test_tesseract_language_resolution_prefers_arabic_and_english_but_falls_back() -> None:
    assert resolve_tesseract_languages(available=("eng", "ara", "osd")) == "ara+eng"
    assert resolve_tesseract_languages(available=("eng", "osd")) == "eng"
    assert resolve_tesseract_languages(available=("osd",)) == ""


def test_mixed_rtl_hierarchical_question_marker_is_classified() -> None:
    item = classify_line(
        "1.2 Q أي صيغة تُستخدم غالبًا لتبادل البيانات مع REST API؟ [1 درجة]",
        "Q1",
    )

    assert item.kind is LineKind.SUBQUESTION
    assert item.number_label == "Q1.2"
    assert item.marks is not None and item.marks.value == 1.0
