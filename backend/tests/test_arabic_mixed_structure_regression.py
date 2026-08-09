from __future__ import annotations

from types import SimpleNamespace

from app.core.domain import QuestionType, SupportingMaterialType
from app.services.extraction.digital_pdf_extractor import _native_page_source_lines
from app.services.extraction.exam_structure import DeterministicExamStructureParser
from app.services.extraction.pdf_layout import (
    PdfLayoutLine,
    PdfLayoutToken,
    _clean_join,
    _rtl_reading_tokens,
)
from app.services.extraction.structure_reconciliation import reconcile_structure_candidates
from app.services.extraction.types import (
    ExtractedQuestion,
    ExtractedQuestionOption,
    ExtractedSourceLine,
    ExtractedSupportingMaterial,
    ExtractedTableCell,
    Geometry,
)


def _source(line_id: str, text: str, order: int, *, top: float | None = None) -> ExtractedSourceLine:
    y = top if top is not None else float(order * 20)
    return ExtractedSourceLine(
        source_line_id=line_id,
        provider="pdfplumber",
        provider_version=None,
        page_number=1,
        reading_order=order,
        original_text=text,
        geometry=Geometry(10, y, 500, y + 12),
        confidence=0.98,
        extraction_method="direct_text",
        language="mixed",
        page_width=600,
        page_height=800,
    )


def test_native_source_line_uses_logical_reading_text_and_preserves_raw_text() -> None:
    raw = "] ةجرد 1 [؟دوجوم ريغ دروملا HTTP ةلاح زمر ام Q 1.1"
    reading = "Q 1.1 ما رمز حالة HTTP المورد غير موجود؟ [1 درجة]"
    layout = PdfLayoutLine(
        raw_text=raw,
        reading_text=reading,
        page_number=1,
        geometry=Geometry(10, 20, 500, 32),
        source_spans=(raw,),
        tokens=(PdfLayoutToken(original_text=raw, geometry=Geometry(10, 20, 500, 32)),),
    )

    lines = _native_page_source_lines(
        SimpleNamespace(width=600, height=800),
        page_number=1,
        text_lines=[],
        layout_lines=[layout],
        confidence=1.0,
        language="mixed",
    )

    assert lines[0].original_text == reading
    assert lines[0].raw_text == raw


def test_clean_join_repairs_detached_arabic_diacritic_glyphs_conservatively() -> None:
    assert _clean_join(["اكتب", "ً", "مثال", "ا", "بسيطً", "ا"]) == "اكتب مثالًا بسيطًا"
    assert _clean_join(["،", "ّ", "وعلل"]) == "، وعلل"


def test_rtl_reading_order_preserves_multi_token_english_runs() -> None:
    words = [
        {"x0": 535.0, "logical_text": "1.2"},
        {"x0": 526.0, "logical_text": "Q"},
        {"x0": 500.0, "logical_text": "أي"},
        {"x0": 348.0, "logical_text": "API"},
        {"x0": 314.0, "logical_text": "REST"},
    ]

    assert _rtl_reading_tokens(words) == ["Q", "1.2", "أي", "REST", "API"]


def test_arabic_mcq_options_are_not_materialized_as_fake_questions() -> None:
    parser = DeterministicExamStructureParser()
    sources = [
        _source("P1-N1", "السؤال الأول - اختيار من متعدد [1 درجة]", 1),
        _source("P1-N2", "Q 1.1 ما رمز حالة HTTP للمورد غير الموجود؟ [1 درجة]", 2),
        _source("P1-N3", "أ. 200", 3),
        _source("P1-N4", "ب. 301", 4),
        _source("P1-N5", "ج. 404", 5),
        _source("P1-N6", "د. 500", 6),
    ]
    fallback = [
        ExtractedQuestion(
            number_label="Q1",
            text=sources[0].original_text,
            page_number=1,
            parent_number_label=None,
            marks=1.0,
            sequence=1,
            confidence=0.98,
            geometry=sources[0].geometry,
            local_key="q1",
            source_line_ids=("P1-N1",),
        ),
        ExtractedQuestion(
            number_label="Q1.1",
            text=sources[1].original_text,
            page_number=1,
            parent_number_label="Q1",
            marks=1.0,
            sequence=2,
            confidence=0.98,
            geometry=sources[1].geometry,
            local_key="q11",
            parent_local_key="q1",
            source_line_ids=("P1-N2",),
        ),
    ]
    for index, label in enumerate("abcd", start=3):
        source = sources[index - 1]
        fallback.append(
            ExtractedQuestion(
                number_label=f"Q1({label})",
                text=source.original_text,
                page_number=1,
                parent_number_label="Q1",
                marks=None,
                sequence=index,
                confidence=0.98,
                geometry=source.geometry,
                local_key=f"q1-{label}",
                parent_local_key="q1",
                source_line_ids=(source.source_line_id,),
            )
        )

    result = parser.parse(
        source_lines=sources,
        fallback_questions=fallback,
        reconciliation_warnings=[],
    )

    assert [question.number_label for question in result.questions] == ["Q1", "Q1.1"]
    assert [question.sequence for question in result.questions] == [1, 2]
    item = result.questions[1]
    assert item.question_type is QuestionType.MULTIPLE_CHOICE
    assert [option.option_text for option in item.options] == ["200", "301", "404", "500"]


def test_arabic_true_false_table_uses_parent_context_when_header_is_visual_order() -> None:
    parser = DeterministicExamStructureParser()
    parent_line = _source("P1-N1", "السؤال الثاني - صح أو خطأ [2 درجات]", 1, top=20)
    parent = ExtractedQuestion(
        number_label="Q2",
        text=parent_line.original_text,
        page_number=1,
        parent_number_label=None,
        marks=2.0,
        sequence=1,
        confidence=0.98,
        geometry=Geometry(10, 20, 500, 55),
        local_key="q2",
        source_line_ids=(parent_line.source_line_id,),
    )
    table = ExtractedSupportingMaterial(
        local_key="p1:table:0",
        material_type=SupportingMaterialType.TABLE,
        page_number=1,
        source_text="# | العبارة | صح / خطأ",
        confidence=0.95,
        geometry=Geometry(10, 60, 500, 150),
        extraction_method="direct_text",
        cells=(
            ExtractedTableCell(0, 0, "أطخ حص", 1, Geometry(10, 60, 70, 80), 0.95),
            ExtractedTableCell(0, 1, "العبارة", 1, Geometry(70, 60, 450, 80), 0.95),
            ExtractedTableCell(0, 2, "#", 1, Geometry(450, 60, 500, 80), 0.95),
            ExtractedTableCell(1, 0, "", 1, Geometry(10, 80, 70, 110), 0.95),
            ExtractedTableCell(
                1,
                1,
                "1 استخدام HTTPS يعني اتصالًا مشفرًا.",
                1,
                Geometry(70, 80, 450, 110),
                0.95,
            ),
            ExtractedTableCell(1, 2, "1", 1, Geometry(450, 80, 500, 110), 0.95),
            ExtractedTableCell(2, 0, "", 1, Geometry(10, 110, 70, 140), 0.95),
            ExtractedTableCell(
                2,
                1,
                "2 يمكن أن تحتوي JSON على Array.",
                1,
                Geometry(70, 110, 450, 140),
                0.95,
            ),
            ExtractedTableCell(2, 2, "2", 1, Geometry(450, 110, 500, 140), 0.95),
        ),
    )

    result = parser.parse(
        source_lines=[parent_line],
        fallback_questions=[parent],
        reconciliation_warnings=[],
        supporting_materials=[table],
    )

    assert [question.number_label for question in result.questions] == ["Q2", "Q2.1", "Q2.2"]
    assert [question.text for question in result.questions[1:]] == [
        "استخدام HTTPS يعني اتصالًا مشفرًا.",
        "يمكن أن تحتوي JSON على Array.",
    ]
    assert all(question.marks is None for question in result.questions[1:])


def test_standalone_arabic_marks_attach_to_immediately_preceding_question() -> None:
    parser = DeterministicExamStructureParser()
    parent_line = _source("P1-N1", "السؤال الثالث - إجابة قصيرة [3 درجات]", 1, top=10)
    stem = _source("P1-N2", "Q3(c) صمّم REST endpoint مناسبًا.", 2, top=30)
    mark = _source("P1-N3", "[3 درجات]", 3, top=46)
    parent = ExtractedQuestion(
        number_label="Q3",
        text=parent_line.original_text,
        page_number=1,
        parent_number_label=None,
        marks=3.0,
        sequence=1,
        confidence=0.98,
        geometry=parent_line.geometry,
        local_key="q3",
        source_line_ids=(parent_line.source_line_id,),
    )
    question = ExtractedQuestion(
        number_label="Q3(c)",
        text=stem.original_text,
        page_number=1,
        parent_number_label="Q3",
        marks=None,
        sequence=2,
        confidence=0.98,
        geometry=stem.geometry,
        local_key="q3c",
        parent_local_key="q3",
        source_line_ids=(stem.source_line_id,),
    )

    result = parser.parse(
        source_lines=[parent_line, stem, mark],
        fallback_questions=[parent, question],
        reconciliation_warnings=[],
    )

    child = next(item for item in result.questions if item.number_label == "Q3(c)")
    assert child.marks == 3.0


def test_reconciliation_drops_visual_question_that_is_a_local_mcq_option() -> None:
    option = ExtractedQuestionOption(
        local_key="q11-o1",
        question_local_key="q11",
        option_label="A",
        option_text="200",
        sequence=1,
        page_number=1,
        confidence=0.98,
        geometry=Geometry(20, 40, 100, 52),
        source_line_ids=("P1-N3",),
    )
    local = ExtractedQuestion(
        number_label="Q1.1",
        text="Q1.1 Which status code means not found?",
        page_number=1,
        parent_number_label="Q1",
        marks=1.0,
        sequence=1,
        confidence=0.98,
        geometry=Geometry(10, 20, 500, 32),
        local_key="q11",
        question_type=QuestionType.MULTIPLE_CHOICE,
        source_line_ids=("P1-N2",),
        options=(option,),
    )
    fake_visual = ExtractedQuestion(
        number_label="200",
        text="200",
        page_number=1,
        parent_number_label="Q1",
        marks=None,
        sequence=2,
        confidence=0.92,
        geometry=option.geometry,
        local_key="visual-200",
        question_type=QuestionType.UNKNOWN,
        source_line_ids=("P1-N3",),
    )

    result = reconcile_structure_candidates(
        local_questions=(local,),
        visual_questions=(fake_visual,),
        local_candidates=(),
        visual_candidates=(),
    )

    assert [question.number_label for question in result.questions] == ["Q1.1"]
    assert any(warning.code == "QUESTION_BOUNDARY_MISMATCH" for warning in result.warnings)
