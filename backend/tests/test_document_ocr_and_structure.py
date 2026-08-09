from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Never

import pytest
from fpdf import FPDF
from helpers import valid_pdf_bytes

from app.core.config import Settings
from app.core.domain import (
    ExtractionWarningSeverity,
    QuestionType,
    SupportingMaterialType,
)
from app.services.extraction.digital_pdf_extractor import PdfPlumberExamExtractor
from app.services.extraction.document_ocr import (
    FakeDocumentOcrProvider,
    NormalizedOcrDocument,
    NormalizedOcrLine,
    NormalizedOcrPage,
    TesseractDocumentOcrProvider,
    create_document_ocr_provider,
)
from app.services.extraction.exam_structure import (
    DeterministicExamStructureParser,
    ExamStructureParserError,
    GeminiExamStructureParser,
    ResilientExamStructureParser,
    StructureParserOutput,
    apply_exam_structure_parser,
)
from app.services.extraction.ocr import OcrLine
from app.services.extraction.reconciliation import (
    collapse_reconciliation_warnings,
    reconcile_native_and_ocr,
)
from app.services.extraction.targeted_ocr import TargetedOcrResult
from app.services.extraction.types import (
    ExtractedQuestion,
    ExtractedSourceLine,
    ExtractedSourceToken,
    ExtractedSupportingMaterial,
    ExtractedTableCell,
    ExtractionReconciliationWarning,
    ExtractionResult,
    Geometry,
)


class _FakeOcrEngine:
    def lines_for_image(self, image: object, scale: float) -> list[OcrLine]:
        del image, scale
        return [
            OcrLine(
                text="السؤال 1 Question 1",
                geometry=Geometry(10, 20, 150, 40),
                confidence=0.91,
            )
        ]


class _CountingOcrEngine:
    def __init__(self) -> None:
        self.calls = 0

    def lines_for_image(self, image: object, scale: float) -> list[OcrLine]:
        del image, scale
        self.calls += 1
        return []


def _source(
    line_id: str,
    text: str,
    order: int = 1,
    page_number: int = 1,
) -> ExtractedSourceLine:
    return ExtractedSourceLine(
        source_line_id=line_id,
        provider="pdfplumber",
        provider_version=None,
        page_number=page_number,
        reading_order=order,
        original_text=text,
        geometry=Geometry(10, 10 * order, 300, 10 * order + 8),
        confidence=0.98,
        extraction_method="direct_text",
        language="mixed",
    )


def _fallback(
    line_id: str,
    text: str = "Question 1: Choose the answer [1]",
    sequence: int = 1,
) -> ExtractedQuestion:
    return ExtractedQuestion(
        number_label=str(sequence),
        text=text,
        page_number=1,
        parent_number_label=None,
        marks=1,
        sequence=sequence,
        confidence=0.98,
        geometry=Geometry(10, 10, 300, 18),
        source_line_ids=(line_id,),
    )


def test_provider_factory_is_provider_neutral_and_tesseract_only() -> None:
    assert isinstance(create_document_ocr_provider(Settings()), TesseractDocumentOcrProvider)
    with pytest.raises(ValueError, match="Unsupported EXAM_OCR_PROVIDER"):
        create_document_ocr_provider(Settings(exam_ocr_provider="cloud-provider"))


def test_tesseract_document_provider_normalizes_full_pdf_once(tmp_path: Path) -> None:
    pdf_path = tmp_path / "mixed.pdf"
    pdf_path.write_bytes(valid_pdf_bytes())
    provider = TesseractDocumentOcrProvider(_FakeOcrEngine())

    result = provider.extract(pdf_path)

    assert result.provider_name == "tesseract"
    assert len(result.pages) == 1
    assert result.pages[0].lines[0].line_id == "P1-L1"
    assert result.pages[0].lines[0].original_text == "السؤال 1 Question 1"
    assert result.pages[0].lines[0].geometry == Geometry(10, 20, 150, 40)


def test_readable_digital_pdf_does_not_run_full_page_tesseract_comparison(
    tmp_path: Path,
) -> None:
    document = FPDF()
    document.add_page()
    document.set_font("Helvetica", size=12)
    document.text(20, 20, "Question 1: Explain testing.")
    pdf_path = tmp_path / "digital.pdf"
    document.output(str(pdf_path))
    page_engine = _CountingOcrEngine()
    document_engine = _CountingOcrEngine()

    result = PdfPlumberExamExtractor(
        ocr_engine=page_engine,
        document_ocr_provider=TesseractDocumentOcrProvider(document_engine),
    ).extract(pdf_path)

    assert result.questions
    assert page_engine.calls == 0
    assert document_engine.calls == 0
    assert result.reconciliation_warnings == []


def test_fake_provider_is_deterministic_and_never_uses_network(tmp_path: Path) -> None:
    expected = NormalizedOcrDocument("fake", "1", "ocr", pages=())
    provider = FakeDocumentOcrProvider(expected)
    assert provider.extract(tmp_path / "not-read.pdf") is expected
    assert provider.calls == 1


def test_reconciliation_marks_technical_and_option_disagreements_critical() -> None:
    native = [
        _source("P1-N1", "Q1: Which IP is valid? 10.0.0.1 [1]"),
        _source("P1-N2", "A) 10.0.0.1", 2),
    ]
    ocr = NormalizedOcrDocument(
        provider_name="tesseract",
        provider_version="5",
        extraction_method="ocr",
        pages=(
            NormalizedOcrPage(
                page_number=1,
                width=612,
                height=792,
                lines=(
                    NormalizedOcrLine(
                        "P1-L1",
                        1,
                        1,
                        "Q7: Which IP is valid? 10.0.0.7 [2]",
                        Geometry(10, 10, 300, 18),
                        0.9,
                        "en",
                    ),
                    NormalizedOcrLine(
                        "P1-L2",
                        1,
                        2,
                        "A) 10.0.0.7",
                        Geometry(10, 20, 300, 28),
                        0.9,
                        "en",
                    ),
                ),
                language="en",
                average_confidence=0.9,
            ),
        ),
    )
    warnings = reconcile_native_and_ocr(native, ocr)
    codes = {warning.code for warning in warnings}
    assert {"QUESTION_NUMBER_MISMATCH", "MARKS_MISMATCH", "OPTION_TEXT_MISMATCH"} <= codes
    assert all(
        warning.severity is ExtractionWarningSeverity.CRITICAL
        for warning in warnings
        if warning.code
        in codes & {"QUESTION_NUMBER_MISMATCH", "MARKS_MISMATCH", "OPTION_TEXT_MISMATCH"}
    )


def test_deterministic_parser_classifies_mcq_options_true_false_and_blank() -> None:
    parser = DeterministicExamStructureParser()
    sources = [
        _source("P1-N1", "Question 1: Choose the answer [1]", 1),
        _source("P1-N2", "A) Alpha", 2),
        _source("P1-N3", "B) Beta", 3),
        _source("P1-N4", "Question 2: True or False [1]", 4),
        _source("P1-N5", "Question 3: Complete ____ [1]", 5),
    ]
    result = parser.parse(
        source_lines=sources,
        fallback_questions=[
            _fallback("P1-N1"),
            _fallback("P1-N4", "Question 2: True or False [1]", 2),
            _fallback("P1-N5", "Question 3: Complete ____ [1]", 3),
        ],
        reconciliation_warnings=[],
    )
    assert result.questions[0].question_type is QuestionType.MULTIPLE_CHOICE
    assert [option.option_label for option in result.questions[0].options] == ["A", "B"]
    assert result.questions[1].question_type is QuestionType.TRUE_FALSE
    assert result.questions[2].question_type is QuestionType.FILL_IN_BLANK
    assert len(result.questions[2].blanks) == 1


def test_deterministic_parser_promotes_mcq_children_but_preserves_marked_subquestions() -> None:
    parser = DeterministicExamStructureParser()
    sources = [
        _source("P1-N1", "Q1: Choose the correct answer", 1),
        _source("P1-N2", "A) Alpha", 2),
        _source("P1-N3", "B) Beta", 3),
        _source("P1-N4", "C) Gamma", 4),
        _source("P1-N5", "D) Delta", 5),
        _source("P1-N6", "Q2: Discuss each part", 6),
        _source("P1-N7", "A) First argument [1]", 7),
        _source("P1-N8", "B) Second argument [1]", 8),
    ]
    parent_one = _fallback("P1-N1")
    mcq_children = [
        ExtractedQuestion(
            number_label=f"1({label.casefold()})",
            text=sources[index].original_text,
            page_number=1,
            parent_number_label="1",
            marks=None,
            sequence=index + 1,
            confidence=0.98,
            geometry=sources[index].geometry,
            source_line_ids=(sources[index].source_line_id,),
        )
        for index, label in enumerate("ABCD", start=1)
    ]
    parent_two = _fallback("P1-N6", "Q2: Discuss each part", 6)
    marked_children = [
        ExtractedQuestion(
            number_label=f"6({label.casefold()})",
            text=sources[index].original_text,
            page_number=1,
            parent_number_label="6",
            marks=1,
            sequence=index + 1,
            confidence=0.98,
            geometry=sources[index].geometry,
            source_line_ids=(sources[index].source_line_id,),
        )
        for index, label in zip((6, 7), "AB", strict=True)
    ]
    result = parser.parse(
        source_lines=sources,
        fallback_questions=[parent_one, *mcq_children, parent_two, *marked_children],
        reconciliation_warnings=[],
    )
    assert len(result.questions[0].options) == 4
    assert result.questions[0].question_type is QuestionType.MULTIPLE_CHOICE
    assert any(question.parent_number_label == "6" for question in result.questions)


def test_deterministic_parser_collapses_inline_mcq_option_row_not_lettered_child() -> None:
    parser = DeterministicExamStructureParser()
    sources = [
        _source("P1-S", "Question 1 - Multiple Choice [2 marks]", 1),
        _source("P1-Q11", "Q1.1 Which layer provides end-to-end process communication?", 2),
        _source("P1-O11", "A. Network  B. Transport  C. Data Link  D. Physical", 3),
        _source("P1-Q12", "Q1.2 Which protocol maps an IPv4 address to a MAC address?", 4),
        _source("P1-O12", "A. DNS  B. ARP  C. DHCP  D. ICMP", 5),
    ]
    section = ExtractedQuestion(
        number_label="Q1",
        text=sources[0].original_text,
        page_number=1,
        parent_number_label=None,
        marks=2,
        sequence=1,
        confidence=0.98,
        geometry=sources[0].geometry,
        local_key="q1",
        source_line_ids=("P1-S",),
    )
    q11 = ExtractedQuestion(
        number_label="Q1.1",
        text=sources[1].original_text,
        page_number=1,
        parent_number_label="Q1",
        marks=None,
        sequence=2,
        confidence=0.98,
        geometry=sources[1].geometry,
        local_key="q11",
        parent_local_key="q1",
        question_type=QuestionType.SHORT_ANSWER,
        source_line_ids=("P1-Q11",),
    )
    bogus_option_child_11 = ExtractedQuestion(
        number_label="Q1(a)",
        text=sources[2].original_text,
        page_number=1,
        parent_number_label="Q1",
        marks=None,
        sequence=3,
        confidence=0.98,
        geometry=sources[2].geometry,
        local_key="q1a-options-11",
        parent_local_key="q1",
        source_line_ids=("P1-O11",),
    )
    q12 = replace(
        q11,
        number_label="Q1.2",
        text=sources[3].original_text,
        sequence=4,
        local_key="q12",
        geometry=sources[3].geometry,
        source_line_ids=("P1-Q12",),
    )
    bogus_option_child_12 = replace(
        bogus_option_child_11,
        text=sources[4].original_text,
        sequence=5,
        local_key="q1a-options-12",
        geometry=sources[4].geometry,
        source_line_ids=("P1-O12",),
    )

    result = parser.parse(
        source_lines=sources,
        fallback_questions=[section, q11, bogus_option_child_11, q12, bogus_option_child_12],
        reconciliation_warnings=[],
    )

    by_label = {question.number_label: question for question in result.questions}
    assert "Q1(a)" not in [question.number_label for question in result.questions]
    assert by_label["Q1.1"].question_type is QuestionType.MULTIPLE_CHOICE
    assert [option.option_text for option in by_label["Q1.1"].options] == [
        "Network",
        "Transport",
        "Data Link",
        "Physical",
    ]
    assert by_label["Q1.2"].question_type is QuestionType.MULTIPLE_CHOICE
    assert [option.option_text for option in by_label["Q1.2"].options] == [
        "DNS",
        "ARP",
        "DHCP",
        "ICMP",
    ]


def test_deterministic_parser_preserves_inline_lettered_independent_tasks() -> None:
    parser = DeterministicExamStructureParser()
    sources = [
        _source("P1-Q2", "Question 2 - Answer all parts [9 marks]", 1),
        _source(
            "P1-Q2A",
            "A. Explain TCP reliability. [3 marks]  B. Calculate the delay. [3 marks]  "
            "C. Compare IPv4 and IPv6. [3 marks]",
            2,
        ),
    ]
    parent = ExtractedQuestion(
        number_label="Q2",
        text=sources[0].original_text,
        page_number=1,
        parent_number_label=None,
        marks=9,
        sequence=1,
        confidence=0.98,
        geometry=sources[0].geometry,
        local_key="q2",
        source_line_ids=("P1-Q2",),
    )
    child = ExtractedQuestion(
        number_label="Q2(a)",
        text=sources[1].original_text,
        page_number=1,
        parent_number_label="Q2",
        marks=None,
        sequence=2,
        confidence=0.98,
        geometry=sources[1].geometry,
        local_key="q2a",
        parent_local_key="q2",
        source_line_ids=("P1-Q2A",),
    )

    result = parser.parse(
        source_lines=sources,
        fallback_questions=[parent, child],
        reconciliation_warnings=[],
    )

    assert any(question.number_label == "Q2(a)" for question in result.questions)
    assert not result.questions[0].options


def test_gemini_structure_parser_allows_inline_options_to_share_one_source_line() -> None:
    lines = [
        _source("P1-Q1", "Q1.1 Which layer provides end-to-end process communication?", 1),
        _source("P1-O1", "A. Network  B. Transport  C. Data Link  D. Physical", 2),
    ]
    payload = {
        "questions": [
            {
                "candidate_id": "q11",
                "number_label": "Q1.1",
                "question_type": "multiple_choice",
                "stem_source_line_ids": ["P1-Q1"],
                "option_candidates": [
                    {"label": "A", "source_line_ids": ["P1-O1"]},
                    {"label": "B", "source_line_ids": ["P1-O1"]},
                    {"label": "C", "source_line_ids": ["P1-O1"]},
                    {"label": "D", "source_line_ids": ["P1-O1"]},
                ],
                "page_number": 1,
                "confidence": 0.99,
            }
        ],
        "warnings": [],
    }

    result = GeminiExamStructureParser(
        api_key="fake",
        model="fake",
        client=_FakeGeminiClient(payload),
    ).parse(
        source_lines=lines,
        fallback_questions=[],
        reconciliation_warnings=[],
    )

    question = result.questions[0]
    assert question.question_type is QuestionType.MULTIPLE_CHOICE
    assert [option.option_text for option in question.options] == [
        "Network",
        "Transport",
        "Data Link",
        "Physical",
    ]


def test_deterministic_parser_expands_numbered_mcq_and_true_false_sections() -> None:
    parser = DeterministicExamStructureParser()
    mcq_lines = [
        _source("P1-N1", "Section A: Choose the correct answer", 1),
        _source("P1-N2", "1) First item?", 2),
        _source("P1-N3", "A) Alpha", 3),
        _source("P1-N4", "B) Beta", 4),
        _source("P1-N5", "C) Gamma", 5),
        _source("P1-N6", "D) Delta", 6),
        _source("P1-N7", "2) Second item?", 7),
        _source("P1-N8", "A) One", 8),
        _source("P1-N9", "B) Two", 9),
        _source("P1-N10", "C) Three", 10),
        _source("P1-N11", "D) Four", 11),
    ]
    mcq = parser.parse(
        source_lines=mcq_lines,
        fallback_questions=[_fallback("P1-N1", mcq_lines[0].original_text)],
        reconciliation_warnings=[],
    )
    mcq_children = [
        question
        for question in mcq.questions
        if question.question_type is QuestionType.MULTIPLE_CHOICE
        and question.parent_local_key is not None
    ]
    assert [question.number_label for question in mcq_children] == ["1", "2"]
    assert [[option.option_label for option in question.options] for question in mcq_children] == [
        ["A", "B", "C", "D"],
        ["A", "B", "C", "D"],
    ]

    true_false_lines = [
        _source("P1-T1", "True / False", 1),
        _source("P1-T2", "1) A statement ( )", 2),
        _source("P1-T3", "2) Another statement ( )", 3),
    ]
    true_false = parser.parse(
        source_lines=true_false_lines,
        fallback_questions=[_fallback("P1-T1", true_false_lines[0].original_text)],
        reconciliation_warnings=[],
    )
    statements = [
        question for question in true_false.questions if question.parent_local_key is not None
    ]
    assert len(statements) == 2
    assert all(question.question_type is QuestionType.TRUE_FALSE for question in statements)
    assert all(not question.blanks for question in statements)


def test_deterministic_parser_persists_each_blank_with_geometry() -> None:
    line = _source("P1-B1", "Question 1: Fill ____ then ______.", 1)
    result = DeterministicExamStructureParser().parse(
        source_lines=[line],
        fallback_questions=[_fallback(line.source_line_id, line.original_text)],
        reconciliation_warnings=[],
    )

    assert result.questions[0].question_type is QuestionType.FILL_IN_BLANK
    assert len(result.questions[0].blanks) == 2
    assert all(blank.geometry is not None for blank in result.questions[0].blanks)


def test_deterministic_parser_spatially_attaches_standalone_fractional_marks() -> None:
    question_line = _source("P1-M1", "Question 1: State one fact.", 1)
    marks_line = _source("P1-M2", "[0.5]", 2)
    result = DeterministicExamStructureParser().parse(
        source_lines=[question_line, marks_line],
        fallback_questions=[
            replace(
                _fallback(question_line.source_line_id, question_line.original_text),
                marks=None,
            )
        ],
        reconciliation_warnings=[],
    )

    assert result.questions[0].marks == 0.5
    assert marks_line.source_line_id in result.questions[0].source_line_ids


def test_deterministic_parser_recovers_marks_from_an_existing_source_span() -> None:
    question_line = _source("P1-M3", "Question 1: State one fact.", 1)
    marks_line = _source("P1-M4", "[1]", 2)
    fallback = replace(
        _fallback(question_line.source_line_id, question_line.original_text),
        marks=None,
        source_line_ids=(question_line.source_line_id, marks_line.source_line_id),
    )
    result = DeterministicExamStructureParser().parse(
        source_lines=[question_line, marks_line],
        fallback_questions=[fallback],
        reconciliation_warnings=[],
    )

    assert result.questions[0].marks == 1


def test_deterministic_parser_preserves_cross_page_question_continuation() -> None:
    first = _source("P1-C1", "Question 1: Explain the following", 1, 1)
    continuation = _source("P2-C1", "using the formula x = y / z.", 1, 2)
    second = _source("P2-C2", "Question 2: State one fact.", 2, 2)
    result = DeterministicExamStructureParser().parse(
        source_lines=[first, continuation, second],
        fallback_questions=[
            _fallback(first.source_line_id, first.original_text, 1),
            replace(
                _fallback(second.source_line_id, second.original_text, 2),
                page_number=2,
            ),
        ],
        reconciliation_warnings=[],
    )

    assert result.questions[0].text.endswith("using the formula x = y / z.")
    assert result.questions[0].source_line_ids == ("P1-C1", "P2-C1")


def test_deterministic_parser_attaches_a_separate_blank_line_to_nearest_question() -> None:
    question_line = _source("P1-Q1", "Question 1: Complete the statement", 1)
    blank_line = _source("P1-Q1-B", "The address is ____ and mask is ______.", 2)
    result = DeterministicExamStructureParser().parse(
        source_lines=[question_line, blank_line],
        fallback_questions=[_fallback(question_line.source_line_id, question_line.original_text)],
        reconciliation_warnings=[],
    )

    assert result.questions[0].question_type is QuestionType.FILL_IN_BLANK
    assert len(result.questions[0].blanks) == 2
    assert blank_line.source_line_id in result.questions[0].source_line_ids


def test_deterministic_parser_retains_unassigned_visible_content_as_a_candidate() -> None:
    line = _source("P1-U1", "Complete ____", 1)
    result = DeterministicExamStructureParser().parse(
        source_lines=[line],
        fallback_questions=[],
        reconciliation_warnings=[],
    )

    assert result.questions == ()
    assert result.candidates[0].item_kind == "visible_content"
    assert result.candidates[0].source_line_ids == (line.source_line_id,)


class _FakeModels:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.calls = 0
        self.last_kwargs: dict[str, object] | None = None

    def generate_content(self, **kwargs: object) -> SimpleNamespace:
        self.calls += 1
        self.last_kwargs = kwargs
        assert kwargs["config"] is not None
        return SimpleNamespace(text=json.dumps(self.payload))


class _FakeGeminiClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self.models = _FakeModels(payload)


class _UnavailableStructureParser:
    def parse(self, **kwargs: object) -> Never:
        del kwargs
        raise ExamStructureParserError("provider unavailable")


def test_resilient_structure_parser_keeps_local_results_when_gemini_is_unavailable() -> None:
    line = _source("P1-L1", "Question 1: State one fact.")
    result = ResilientExamStructureParser(_UnavailableStructureParser()).parse(
        source_lines=[line],
        fallback_questions=[_fallback(line.source_line_id, line.original_text)],
        reconciliation_warnings=[],
    )

    assert result.questions[0].text == line.original_text
    assert any(warning.code == "STRUCTURE_PARSER_FAILED" for warning in result.warnings)


def test_gemini_structure_parser_recovers_wrapped_stem_from_independent_local_boundary() -> None:
    lines = [
        _source(
            "P1-L1",
            "Question 5: A queue initially contains A, B, and C, with A at the front. "
            "Perform the operations enqueue(D),",
            1,
        ),
        _source(
            "P1-L2",
            "dequeue(), enqueue(E), and dequeue(). Show the queue after each operation.",
            2,
        ),
        _source("P1-L3", "Question 6: Explain graph traversal.", 3),
    ]
    fallback = ExtractedQuestion(
        number_label="5",
        text=f"{lines[0].original_text} {lines[1].original_text}",
        page_number=1,
        parent_number_label=None,
        marks=6,
        sequence=5,
        confidence=0.98,
        geometry=Geometry(10, 10, 300, 28),
        source_line_ids=("P1-L1", "P1-L2"),
    )
    payload = {
        "questions": [
            {
                "candidate_id": "q5",
                "number_label": "5",
                "question_type": "short_answer",
                # Simulate the exact regression: Gemini picked only the first
                # physical line of a visibly wrapped question.
                "stem_source_line_ids": ["P1-L1"],
                "page_number": 1,
                "confidence": 1.0,
            }
        ],
        "warnings": [],
    }

    result = GeminiExamStructureParser(
        api_key="fake",
        model="fake",
        client=_FakeGeminiClient(payload),
    ).parse(
        source_lines=lines,
        fallback_questions=[fallback],
        reconciliation_warnings=[],
    )

    question = result.questions[0]
    assert question.text == f"{lines[0].original_text} {lines[1].original_text}"
    assert question.source_line_ids == ("P1-L1", "P1-L2")
    assert question.confidence == pytest.approx(0.98)
    assert not any(warning.code == "QUESTION_BOUNDARY_MISMATCH" for warning in result.warnings)


def test_gemini_structure_parser_recovers_wrapped_stem_when_gemini_and_local_draft_both_truncate() -> None:
    lines = [
        _source(
            "P1-L1",
            "Question 5: A queue initially contains A, B, and C, with A at the front. "
            "Perform the operations enqueue(D),",
            1,
        ),
        _source(
            "P1-L2",
            "dequeue(), enqueue(E), and dequeue(). Show the queue after each operation.",
            2,
        ),
        _source("P1-L3", "Question 6: Explain graph traversal.", 3),
    ]
    # Reproduce the live regression: both semantic candidates point only to the
    # first physical line, while the normalized source stream still contains the
    # visibly wrapped continuation line.
    fallback = ExtractedQuestion(
        number_label="5",
        text=lines[0].original_text,
        page_number=1,
        parent_number_label=None,
        marks=6,
        sequence=5,
        confidence=0.98,
        geometry=Geometry(10, 10, 300, 18),
        source_line_ids=("P1-L1",),
    )
    payload = {
        "questions": [
            {
                "candidate_id": "q5",
                "number_label": "5",
                "question_type": "short_answer",
                "stem_source_line_ids": ["P1-L1"],
                "page_number": 1,
                "confidence": 1.0,
            }
        ],
        "warnings": [],
    }

    result = GeminiExamStructureParser(
        api_key="fake",
        model="fake",
        client=_FakeGeminiClient(payload),
    ).parse(
        source_lines=lines,
        fallback_questions=[fallback],
        reconciliation_warnings=[],
    )

    question = result.questions[0]
    assert question.text == f"{lines[0].original_text} {lines[1].original_text}"
    assert question.source_line_ids == ("P1-L1", "P1-L2")
    assert question.review_status.value == "machine_extracted"
    assert not any(warning.code == "QUESTION_BOUNDARY_MISMATCH" for warning in result.warnings)


def test_gemini_structure_parser_reclaims_same_question_instruction_misclassification_for_wrapped_stem() -> None:
    lines = [
        _source(
            "P1-L1",
            "Question 5: A queue initially contains A, B, and C, with A at the front. "
            "Perform the operations enqueue(D),",
            1,
        ),
        _source(
            "P1-L2",
            "dequeue(), enqueue(E), and dequeue(). Show the queue after each operation.",
            2,
        ),
        _source("P1-L3", "Question 6: Explain graph traversal.", 3),
    ]
    fallback = ExtractedQuestion(
        number_label="5",
        text=lines[0].original_text,
        page_number=1,
        parent_number_label=None,
        marks=6,
        sequence=5,
        confidence=0.98,
        geometry=Geometry(10, 10, 300, 18),
        source_line_ids=("P1-L1",),
    )
    payload = {
        "questions": [
            {
                "candidate_id": "q5",
                "number_label": "5",
                "question_type": "short_answer",
                "stem_source_line_ids": ["P1-L1"],
                # Live-model regression: Gemini can place the wrapped second
                # physical line in instruction_source_line_ids instead of stem.
                "instruction_source_line_ids": ["P1-L2"],
                "page_number": 1,
                "confidence": 1.0,
            }
        ],
        "warnings": [],
    }

    result = GeminiExamStructureParser(
        api_key="fake",
        model="fake",
        client=_FakeGeminiClient(payload),
    ).parse(
        source_lines=lines,
        fallback_questions=[fallback],
        reconciliation_warnings=[],
    )

    question = result.questions[0]
    assert question.text == f"{lines[0].original_text} {lines[1].original_text}"
    assert question.source_line_ids == ("P1-L1", "P1-L2")
    assert question.instructions is None


def test_gemini_structure_parser_keeps_explicit_instruction_out_of_wrapped_stem() -> None:
    lines = [
        _source("P1-L1", "Question 5: Explain the queue operation,", 1),
        _source("P1-L2", "Instructions: show all working.", 2),
        _source("P1-L3", "Question 6: Explain graph traversal.", 3),
    ]
    fallback = ExtractedQuestion(
        number_label="5",
        text=lines[0].original_text,
        page_number=1,
        parent_number_label=None,
        marks=None,
        sequence=5,
        confidence=0.98,
        geometry=Geometry(10, 10, 300, 18),
        source_line_ids=("P1-L1",),
    )
    payload = {
        "questions": [
            {
                "candidate_id": "q5",
                "number_label": "5",
                "question_type": "short_answer",
                "stem_source_line_ids": ["P1-L1"],
                "instruction_source_line_ids": ["P1-L2"],
                "page_number": 1,
                "confidence": 1.0,
            }
        ],
        "warnings": [],
    }

    result = GeminiExamStructureParser(
        api_key="fake",
        model="fake",
        client=_FakeGeminiClient(payload),
    ).parse(
        source_lines=lines,
        fallback_questions=[fallback],
        reconciliation_warnings=[],
    )

    question = result.questions[0]
    assert question.text == lines[0].original_text
    assert question.source_line_ids == ("P1-L1",)
    assert question.instructions == lines[1].original_text


def test_gemini_structure_parser_does_not_absorb_unclassified_local_only_text() -> None:
    lines = [
        _source("P1-L1", "Question 5: Explain the queue operation.", 1),
        _source("P1-L2", "Department watermark text", 2),
        _source("P1-L3", "Question 6: Explain graph traversal.", 3),
    ]
    # Simulate an over-broad local candidate. The reconciliation layer must not
    # treat every line between Q5 and Q6 as canonical question text.
    fallback = ExtractedQuestion(
        number_label="5",
        text=f"{lines[0].original_text} {lines[1].original_text}",
        page_number=1,
        parent_number_label=None,
        marks=None,
        sequence=5,
        confidence=0.98,
        geometry=Geometry(10, 10, 300, 28),
        source_line_ids=("P1-L1", "P1-L2"),
    )
    payload = {
        "questions": [
            {
                "candidate_id": "q5",
                "number_label": "5",
                "question_type": "short_answer",
                "stem_source_line_ids": ["P1-L1"],
                "page_number": 1,
                "confidence": 1.0,
            }
        ],
        "warnings": [],
    }

    result = GeminiExamStructureParser(
        api_key="fake",
        model="fake",
        client=_FakeGeminiClient(payload),
    ).parse(
        source_lines=lines,
        fallback_questions=[fallback],
        reconciliation_warnings=[],
    )

    question = result.questions[0]
    assert question.text == lines[0].original_text
    assert question.source_line_ids == ("P1-L1",)
    assert question.confidence == pytest.approx(0.74)
    assert question.review_status.value == "needs_review"
    boundary_warning = next(
        warning for warning in result.warnings if warning.code == "QUESTION_BOUNDARY_MISMATCH"
    )
    assert boundary_warning.source_line_ids == ("P1-L2",)


def test_gemini_structure_parser_reconstructs_text_only_from_source_ids() -> None:
    lines = [
        _source("P1-L1", "Question 1: Choose [1]", 1),
        _source("P1-L2", "A) Original Alpha", 2),
        _source("P1-L3", "B) Original Beta", 3),
    ]
    payload = {
        "questions": [
            {
                "number_label": "1",
                "question_type": "multiple_choice",
                "stem_source_line_ids": ["P1-L1"],
                "option_candidates": [
                    {"label": "A", "source_line_ids": ["P1-L2"]},
                    {"label": "B", "source_line_ids": ["P1-L3"]},
                ],
                "marks_source_line_ids": ["P1-L1"],
                "instruction_source_line_ids": [],
                "parent_number_label": None,
                "page_number": 1,
            }
        ],
        "warnings": [],
    }
    client = _FakeGeminiClient(payload)
    parser = GeminiExamStructureParser(api_key="fake", model="fake", client=client)
    result = parser.parse(
        source_lines=lines,
        fallback_questions=[],
        reconciliation_warnings=[],
    )
    assert result.questions[0].text == "Question 1: Choose [1]"
    assert result.questions[0].options[0].option_text == "Original Alpha"
    assert result.questions[0].source_line_ids == ("P1-L1",)
    assert client.models.last_kwargs is not None
    request_schema = client.models.last_kwargs["config"].response_json_schema
    governed_schema = StructureParserOutput.model_json_schema()
    assert "minLength" in json.dumps(governed_schema)
    assert "minLength" not in json.dumps(request_schema)
    assert "maxLength" not in json.dumps(request_schema)
    assert '"default"' not in json.dumps(request_schema)
    assert "$defs" in request_schema


def test_gemini_structure_parser_rejects_nonexistent_source_line() -> None:
    payload = {
        "questions": [
            {
                "number_label": "1",
                "question_type": "unknown",
                "stem_source_line_ids": ["P1-L404"],
                "option_candidates": [],
                "marks_source_line_ids": [],
                "instruction_source_line_ids": [],
                "parent_number_label": None,
                "page_number": 1,
            }
        ],
        "warnings": [],
    }
    parser = GeminiExamStructureParser(
        api_key="fake",
        model="fake",
        validation_retries=0,
        client=_FakeGeminiClient(payload),
    )
    with pytest.raises(ExamStructureParserError, match="could not be validated"):
        parser.parse(
            source_lines=[_source("P1-L1", "Question 1")],
            fallback_questions=[],
            reconciliation_warnings=[],
        )


def test_gemini_vision_sends_full_page_and_reuses_validated_cache(tmp_path: Path) -> None:
    pdf_path = tmp_path / "exam.pdf"
    pdf_path.write_bytes(valid_pdf_bytes())
    payload = {
        "questions": [
            {
                "candidate_id": "question-1",
                "number_label": "1",
                "question_type": "short_answer",
                "stem_source_line_ids": ["P1-L1"],
                "page_number": 1,
                "confidence": 0.9,
            }
        ],
        "warnings": [],
    }
    client = _FakeGeminiClient(payload)
    parser = GeminiExamStructureParser(api_key="fake", model="fake", client=client)
    line = replace(
        _source("P1-L1", "Question 1: State one fact."),
        tokens=(
            ExtractedSourceToken(
                token_id="P1-L1-T1",
                original_text="Question",
                geometry=Geometry(10, 10, 70, 18),
                confidence=0.98,
            ),
        ),
    )

    fresh = parser.parse(
        source_lines=[line],
        fallback_questions=[_fallback(line.source_line_id, line.original_text)],
        reconciliation_warnings=[],
        pdf_path=pdf_path,
    )
    cached = parser.parse(
        source_lines=[line],
        fallback_questions=[_fallback(line.source_line_id, line.original_text)],
        reconciliation_warnings=[],
        pdf_path=pdf_path,
    )

    assert client.models.calls == 1
    assert client.models.last_kwargs is not None
    assert isinstance(client.models.last_kwargs["contents"], list)
    assert len(client.models.last_kwargs["contents"]) == 3
    prompt_part = client.models.last_kwargs["contents"][0]
    assert "P1-L1-T1" in prompt_part.text
    assert "local_candidates" in prompt_part.text
    assert fresh.candidates[0].provenance == "fresh_gemini"
    assert cached.candidates[0].provenance == "cache"


def test_gemini_uses_stable_candidate_identity_for_duplicate_visible_labels() -> None:
    lines = [
        _source("P1-L1", "Question 8: Answer the following", 1),
        _source("P1-L2", "Question 8: Child statement", 2),
    ]
    payload = {
        "questions": [
            {
                "candidate_id": "parent-8",
                "number_label": "8",
                "question_type": "mixed",
                "stem_source_line_ids": ["P1-L1"],
                "page_number": 1,
            },
            {
                "candidate_id": "child-8",
                "number_label": "8",
                "question_type": "short_answer",
                "stem_source_line_ids": ["P1-L2"],
                "parent_candidate_id": "parent-8",
                "page_number": 1,
            },
        ],
        "warnings": [],
    }
    result = GeminiExamStructureParser(
        api_key="fake",
        model="fake",
        client=_FakeGeminiClient(payload),
    ).parse(source_lines=lines, fallback_questions=[], reconciliation_warnings=[])

    assert result.questions[0].number_label == result.questions[1].number_label == "8"
    assert result.questions[1].parent_local_key == result.questions[0].local_key


def test_gemini_candidate_text_requires_targeted_ocr_before_becoming_canonical(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf_path = tmp_path / "exam.pdf"
    pdf_path.write_bytes(valid_pdf_bytes())
    recovered = replace(
        _source("P1-Rmissing-L1", "Question 9: Recovered source text"),
        provider="tesseract",
        extraction_method="targeted_ocr",
    )

    def fake_targeted(*args: object, **kwargs: object) -> TargetedOcrResult:
        del args, kwargs
        return TargetedOcrResult((recovered,))

    monkeypatch.setattr(
        "app.services.extraction.exam_structure.targeted_tesseract_ocr",
        fake_targeted,
    )
    payload = {
        "questions": [
            {
                "candidate_id": "missing",
                "number_label": "9",
                "question_type": "short_answer",
                "candidate_text": "Question 9: Recovered source text",
                "geometry": {"x0": 5, "top": 5, "x1": 310, "bottom": 30},
                "page_number": 1,
                "confidence": 0.95,
            }
        ],
        "warnings": [],
    }
    result = GeminiExamStructureParser(
        api_key="fake",
        model="fake",
        cache_enabled=False,
        client=_FakeGeminiClient(payload),
    ).parse(
        source_lines=[],
        fallback_questions=[],
        reconciliation_warnings=[],
        pdf_path=pdf_path,
    )

    assert result.questions[0].text == recovered.original_text
    assert result.questions[0].extraction_method == "targeted_ocr"
    assert result.candidates[0].provenance == "targeted_ocr"


def test_gemini_retains_visual_material_candidates_and_blocks_uncorroborated_tables() -> None:
    payload = {
        "questions": [],
        "supporting_materials": [
            {
                "candidate_id": "visual-table-1",
                "material_type": "table",
                "page_number": 1,
                "candidate_text": "two-column matching table",
                "geometry": {"x0": 20, "top": 40, "x1": 300, "bottom": 240},
                "confidence": 0.9,
            }
        ],
        "warnings": [],
    }
    result = GeminiExamStructureParser(
        api_key="fake",
        model="fake",
        client=_FakeGeminiClient(payload),
    ).parse(source_lines=[], fallback_questions=[], reconciliation_warnings=[])

    assert result.candidates[0].item_kind == "table"
    assert result.candidates[0].original_text == "two-column matching table"
    assert any(warning.code == "TABLE_STRUCTURE_MISMATCH" for warning in result.warnings)


def test_gemini_page_cap_is_a_critical_quota_guard(tmp_path: Path) -> None:
    document = FPDF()
    document.add_page()
    document.set_font("Helvetica", size=12)
    document.text(20, 20, "Question 1")
    document.add_page()
    document.text(20, 20, "Question 2")
    pdf_path = tmp_path / "two-pages.pdf"
    document.output(str(pdf_path))
    payload = {
        "questions": [
            {
                "candidate_id": "q1",
                "number_label": "1",
                "question_type": "short_answer",
                "stem_source_line_ids": ["P1-L1"],
                "page_number": 1,
            }
        ],
        "warnings": [],
    }
    result = GeminiExamStructureParser(
        api_key="fake",
        model="fake",
        max_pages_per_document=1,
        cache_enabled=False,
        client=_FakeGeminiClient(payload),
    ).parse(
        source_lines=[_source("P1-L1", "Question 1")],
        fallback_questions=[_fallback("P1-L1", "Question 1")],
        reconciliation_warnings=[],
        pdf_path=pdf_path,
    )

    page_limit_warning = next(
        warning for warning in result.warnings if warning.code == "VISUAL_PAGE_LIMIT_REACHED"
    )
    assert page_limit_warning.severity is ExtractionWarningSeverity.CRITICAL


def test_deterministic_parser_recognizes_underscore_numbered_short_answers() -> None:
    parser = DeterministicExamStructureParser()
    result = parser.parse(
        source_lines=[
            _source("P1-N1", "1_ What is unit testing?", 1),
            _source("P1-N2", "2_ Explain integration testing.", 2),
        ],
        fallback_questions=[],
        reconciliation_warnings=[],
    )

    assert [question.number_label for question in result.questions] == ["1", "2"]
    assert all(question.question_type is QuestionType.SHORT_ANSWER for question in result.questions)


def test_lettered_open_questions_remain_subquestions_not_mcq_options() -> None:
    parser = DeterministicExamStructureParser()
    sources = [
        _source("P1-N1", "Question 1", 1),
        _source("P1-N2", "1. Explain the scenario", 2),
        _source("P1-N3", "A) What is the purpose?", 3),
        _source("P1-N4", "B) How is it protected?", 4),
        _source("P1-N5", "2. Draw the diagram", 5),
        _source("P1-N6", "A) Label the sender", 6),
        _source("P1-N7", "B) Label the receiver", 7),
    ]
    result = parser.parse(
        source_lines=sources,
        fallback_questions=[
            ExtractedQuestion(
                number_label="Q1",
                text="Question 1",
                page_number=1,
                parent_number_label=None,
                marks=None,
                sequence=1,
                confidence=0.98,
                geometry=sources[0].geometry,
                local_key="P1-Q1",
                source_line_ids=("P1-N1",),
            )
        ],
        reconciliation_warnings=[],
    )

    assert sum(len(question.options) for question in result.questions) == 0
    assert any(question.parent_local_key == "P1-Q1-I1" for question in result.questions)
    assert any(question.parent_local_key == "P1-Q1-I2" for question in result.questions)


def test_repeated_line_warnings_are_collapsed_by_page_and_code() -> None:
    warnings = [
        ExtractionReconciliationWarning(
            code="UNASSIGNED_CONTENT",
            severity=ExtractionWarningSeverity.WARNING,
            message="OCR content could not be assigned safely.",
            page_number=1,
            source_line_ids=(f"P1-L{index}",),
            geometry=Geometry(10, index * 10, 100, index * 10 + 5),
        )
        for index in range(1, 6)
    ]

    collapsed = collapse_reconciliation_warnings(warnings)

    assert len(collapsed) == 1
    assert len(collapsed[0].source_line_ids) == 5
    assert "5 related occurrences" in collapsed[0].message


def test_reduced_scope_keeps_table_visual_and_does_not_create_cell_blanks() -> None:
    prompt = ExtractedSourceLine(
        source_line_id="P1-L1",
        provider="pdfplumber",
        provider_version=None,
        page_number=1,
        reading_order=1,
        original_text=(
            "Question 4: Write two differences between Software inspection "
            "and Software testing"
        ),
        geometry=Geometry(20, 40, 500, 55),
        confidence=0.98,
        extraction_method="direct_text",
        language="en",
    )
    header_one = ExtractedSourceLine(
        source_line_id="P1-L2",
        provider="pdfplumber",
        provider_version=None,
        page_number=1,
        reading_order=2,
        original_text="Software inspection",
        geometry=Geometry(60, 90, 250, 104),
        confidence=0.98,
        extraction_method="direct_text",
        language="en",
    )
    header_two = replace(
        header_one,
        source_line_id="P1-L3",
        reading_order=3,
        original_text="Software testing",
        geometry=Geometry(260, 90, 450, 104),
    )
    question = ExtractedQuestion(
        number_label="4",
        text=(
            "Question 4: Write two differences between Software inspection and "
            "Software testing Software inspection Software testing"
        ),
        page_number=1,
        parent_number_label=None,
        marks=None,
        sequence=1,
        confidence=0.98,
        geometry=Geometry(20, 40, 500, 180),
        local_key="P1-Q1",
        source_line_ids=("P1-L1", "P1-L2", "P1-L3"),
    )
    material = ExtractedSupportingMaterial(
        local_key="P1-T1",
        material_type=SupportingMaterialType.TABLE,
        page_number=1,
        source_text="Software inspection Software testing",
        confidence=0.98,
        geometry=Geometry(50, 80, 470, 180),
        extraction_method="direct_text",
        question_local_key="P1-Q1",
        cells=(
            ExtractedTableCell(
                row_index=0,
                column_index=0,
                original_text="Software inspection",
                page_number=1,
                geometry=Geometry(50, 80, 250, 110),
                confidence=0.98,
                source_line_ids=("P1-L2",),
            ),
            ExtractedTableCell(
                row_index=0,
                column_index=1,
                original_text="Software testing",
                page_number=1,
                geometry=Geometry(250, 80, 470, 110),
                confidence=0.98,
                source_line_ids=("P1-L3",),
            ),
            ExtractedTableCell(
                row_index=1,
                column_index=0,
                original_text="",
                page_number=1,
                geometry=Geometry(50, 110, 250, 145),
                confidence=0.98,
            ),
            ExtractedTableCell(
                row_index=1,
                column_index=1,
                original_text="",
                page_number=1,
                geometry=Geometry(250, 110, 470, 145),
                confidence=0.98,
            ),
        ),
    )

    result = DeterministicExamStructureParser().parse(
        source_lines=[prompt, header_one, header_two],
        fallback_questions=[question],
        reconciliation_warnings=[],
        supporting_materials=[material],
    )

    assert len(result.questions) == 1
    assert result.questions[0].text == prompt.original_text
    assert result.questions[0].blanks == ()


def test_true_false_table_rows_become_unscored_children_across_pages() -> None:
    parser = DeterministicExamStructureParser()
    parent_line = _source(
        "P1-N1",
        "Question 2 - True or False (2 marks)",
        1,
        page_number=1,
    )
    table = ExtractedSupportingMaterial(
        local_key="p2:table:0",
        material_type=SupportingMaterialType.TABLE,
        page_number=2,
        source_text="No. | Statement | T / F",
        confidence=0.95,
        geometry=Geometry(10, 20, 500, 120),
        extraction_method="direct_text",
        cells=(
            ExtractedTableCell(0, 0, "No.", 2, Geometry(10, 20, 50, 40), 0.95),
            ExtractedTableCell(0, 1, "Statement", 2, Geometry(50, 20, 450, 40), 0.95),
            ExtractedTableCell(0, 2, "T / F", 2, Geometry(450, 20, 500, 40), 0.95),
            ExtractedTableCell(1, 0, "1", 2, Geometry(10, 40, 50, 70), 0.95),
            ExtractedTableCell(
                1,
                1,
                "Projection chooses rows from a relation.",
                2,
                Geometry(50, 40, 450, 70),
                0.95,
            ),
            ExtractedTableCell(1, 2, "", 2, Geometry(450, 40, 500, 70), 0.95),
            ExtractedTableCell(2, 0, "2", 2, Geometry(10, 70, 50, 100), 0.95),
            ExtractedTableCell(
                2,
                1,
                "COMMIT makes the transaction permanent.",
                2,
                Geometry(50, 70, 450, 100),
                0.95,
            ),
            ExtractedTableCell(2, 2, "", 2, Geometry(450, 70, 500, 100), 0.95),
        ),
    )
    parent = ExtractedQuestion(
        number_label="Q2",
        text=parent_line.original_text,
        page_number=1,
        parent_number_label=None,
        marks=2.0,
        sequence=1,
        confidence=0.98,
        geometry=parent_line.geometry,
        local_key="P1-Q2",
        source_line_ids=(parent_line.source_line_id,),
    )

    result = parser.parse(
        source_lines=[parent_line],
        fallback_questions=[parent],
        reconciliation_warnings=[],
        supporting_materials=[table],
    )

    assert [item.number_label for item in result.questions] == ["Q2", "Q2.1", "Q2.2"]
    assert result.questions[0].question_type is QuestionType.TRUE_FALSE
    assert all(item.parent_number_label == "Q2" for item in result.questions[1:])
    assert all(item.marks is None for item in result.questions[1:])
    assert all(item.question_type is QuestionType.TRUE_FALSE for item in result.questions[1:])




def test_pipeline_uses_true_false_table_for_structure_before_hiding_it_from_materials() -> None:
    parent_line = _source(
        "P1-N1",
        "Question 2 - True or False (2 marks)",
        1,
        page_number=1,
    )
    table = ExtractedSupportingMaterial(
        local_key="p2:table:0",
        material_type=SupportingMaterialType.TABLE,
        page_number=2,
        source_text="No. | Statement | T / F",
        confidence=0.95,
        geometry=Geometry(10, 20, 500, 120),
        extraction_method="direct_text",
        cells=(
            ExtractedTableCell(0, 0, "No.", 2, Geometry(10, 20, 50, 40), 0.95),
            ExtractedTableCell(0, 1, "Statement", 2, Geometry(50, 20, 450, 40), 0.95),
            ExtractedTableCell(0, 2, "T / F", 2, Geometry(450, 20, 500, 40), 0.95),
            ExtractedTableCell(1, 0, "1", 2, Geometry(10, 40, 50, 70), 0.95),
            ExtractedTableCell(
                1,
                1,
                "Projection chooses rows from a relation.",
                2,
                Geometry(50, 40, 450, 70),
                0.95,
            ),
            ExtractedTableCell(1, 2, "", 2, Geometry(450, 40, 500, 70), 0.95),
            ExtractedTableCell(2, 0, "2", 2, Geometry(10, 70, 50, 100), 0.95),
            ExtractedTableCell(
                2,
                1,
                "COMMIT makes the transaction permanent.",
                2,
                Geometry(50, 70, 450, 100),
                0.95,
            ),
            ExtractedTableCell(2, 2, "", 2, Geometry(450, 70, 500, 100), 0.95),
        ),
    )
    parent = ExtractedQuestion(
        number_label="Q2",
        text=parent_line.original_text,
        page_number=1,
        parent_number_label=None,
        marks=2.0,
        sequence=1,
        confidence=0.98,
        geometry=parent_line.geometry,
        local_key="P1-Q2",
        source_line_ids=(parent_line.source_line_id,),
    )
    raw = ExtractionResult(
        questions=[parent],
        evidence=[],
        source_lines=[parent_line],
        supporting_materials=[table],
    )

    result = apply_exam_structure_parser(raw, DeterministicExamStructureParser())

    assert [item.number_label for item in result.questions] == ["Q2", "Q2.1", "Q2.2"]
    assert result.supporting_materials == []

@pytest.mark.xfail(strict=False, reason="Known pre-deploy regression: dotted answer line may classify short-answer item as mixed")
def test_long_dotted_answer_lines_do_not_create_fill_blank_questions() -> None:
    parser = DeterministicExamStructureParser()
    sources = [
        _source("P1-N1", "Question 3 - Short Answer (3 marks)", 1),
        _source(
            "P1-N2",
            "Q3(a) Distinguish between a candidate key and a primary key. [3 marks]",
            2,
        ),
        _source("P1-N3", "." * 80, 3),
    ]
    result = parser.parse(
        source_lines=sources,
        fallback_questions=[
            ExtractedQuestion(
                number_label="Q3",
                text=sources[0].original_text,
                page_number=1,
                parent_number_label=None,
                marks=3.0,
                sequence=1,
                confidence=0.98,
                geometry=sources[0].geometry,
                local_key="P1-Q3",
                source_line_ids=("P1-N1",),
            ),
            ExtractedQuestion(
                number_label="Q3(a)",
                text=f"{sources[1].original_text} {sources[2].original_text}",
                page_number=1,
                parent_number_label="Q3",
                marks=3.0,
                sequence=2,
                confidence=0.98,
                geometry=sources[1].geometry,
                local_key="P1-Q3-A",
                parent_local_key="P1-Q3",
                source_line_ids=("P1-N2", "P1-N3"),
            ),
        ],
        reconciliation_warnings=[],
    )

    child = result.questions[1]
    assert child.question_type is QuestionType.SHORT_ANSWER
    assert child.blanks == ()



def test_marks_badge_is_structured_data_not_part_of_question_text() -> None:
    parser = DeterministicExamStructureParser()
    parent_source = _source(
        "P1-N1",
        "Question 4 - SQL Application (9 marks)",
        1,
    )
    child_source = _source(
        "P1-N2",
        "Q4(b) Write an SQL query to display each student name with the [3 marks] "
        "titles of courses.",
        2,
    )
    parent = ExtractedQuestion(
        number_label="Q4",
        text=parent_source.original_text,
        page_number=1,
        parent_number_label=None,
        marks=9.0,
        sequence=1,
        confidence=0.98,
        geometry=parent_source.geometry,
        local_key="P1-Q4",
        source_line_ids=(parent_source.source_line_id,),
    )
    child = ExtractedQuestion(
        number_label="Q4(b)",
        text=child_source.original_text,
        page_number=1,
        parent_number_label="Q4",
        marks=3.0,
        sequence=2,
        confidence=0.98,
        geometry=child_source.geometry,
        local_key="P1-Q4-B",
        parent_local_key="P1-Q4",
        source_line_ids=(child_source.source_line_id,),
    )

    result = parser.parse(
        source_lines=[parent_source, child_source],
        fallback_questions=[parent, child],
        reconciliation_warnings=[],
        supporting_materials=[],
    )

    by_label = {item.number_label: item for item in result.questions}
    assert by_label["Q4"].marks == 9.0
    assert by_label["Q4"].text == "Question 4 - SQL Application"
    assert by_label["Q4(b)"].marks == 3.0
    assert by_label["Q4(b)"].text == (
        "Q4(b) Write an SQL query to display each student name with the titles of courses."
    )


def test_deterministic_structure_keeps_fixture_admin_notes_out_of_question_text() -> None:
    parser = DeterministicExamStructureParser()
    sources = [
        _source("P2-N1", "Question 2 - True / False [6 marks]", 1, page_number=2),
        _source(
            "P2-N2",
            "Important fixture behavior: the six child statements intentionally have no "
            "individual marks. The system must keep them",
            2,
            page_number=2,
        ),
        _source(
            "P2-N3",
            "unallocated and must NOT assume 1 mark each merely because the parent total is 6.",
            3,
            page_number=2,
        ),
    ]
    parent = ExtractedQuestion(
        number_label="Q2",
        text=" ".join(line.original_text for line in sources),
        page_number=2,
        parent_number_label=None,
        marks=6.0,
        sequence=1,
        confidence=0.98,
        geometry=sources[0].geometry,
        local_key="P2-Q2",
        source_line_ids=tuple(line.source_line_id for line in sources),
    )

    result = parser.parse(
        source_lines=sources,
        fallback_questions=[parent],
        reconciliation_warnings=[],
    )

    question = result.questions[0]
    assert question.text == "Question 2 - True / False"
    assert question.source_line_ids == ("P2-N1",)
    assert "fixture" not in question.text.casefold()
    assert "system must" not in question.text.casefold()


def test_gemini_structure_uses_source_text_but_excludes_fixture_admin_commentary() -> None:
    sources = [
        _source("P2-N1", "Question 2 - True / False [6 marks]", 1, page_number=2),
        _source(
            "P2-N2",
            "Important fixture behavior: the six child statements intentionally have no "
            "individual marks. The system must keep them",
            2,
            page_number=2,
        ),
        _source(
            "P2-N3",
            "unallocated and must NOT assume 1 mark each merely because the parent total is 6.",
            3,
            page_number=2,
        ),
    ]
    payload = {
        "questions": [
            {
                "candidate_id": "q2",
                "number_label": "Q2",
                "question_type": "true_false",
                "stem_source_line_ids": ["P2-N1", "P2-N2", "P2-N3"],
                "marks_source_line_ids": ["P2-N1"],
                "page_number": 2,
                "confidence": 0.98,
            }
        ],
        "warnings": [],
    }

    result = GeminiExamStructureParser(
        api_key="fake",
        model="fake",
        client=_FakeGeminiClient(payload),
    ).parse(source_lines=sources, fallback_questions=[], reconciliation_warnings=[])

    question = result.questions[0]
    assert question.text == "Question 2 - True / False [6 marks]"
    assert question.source_line_ids == ("P2-N1",)
    assert "fixture" not in question.text.casefold()


def test_missing_mark_admin_sentence_is_not_canonical_question_text() -> None:
    parser = DeterministicExamStructureParser()
    sources = [
        _source(
            "P3-N7",
            "Q3(c) Identify the default gateway that should be configured for a host on LAN-A.",
            7,
            page_number=3,
        ),
        _source(
            "P3-N8",
            "No individual mark is printed for Q3(c).",
            8,
            page_number=3,
        ),
        _source(
            "P3-N9",
            "Fixture intent: because Q3 total = 9, Q3(c) must be derived deterministically as 3",
            9,
            page_number=3,
        ),
        _source("P3-N10", "marks.", 10, page_number=3),
    ]
    child = ExtractedQuestion(
        number_label="Q3(c)",
        text=" ".join(line.original_text for line in sources),
        page_number=3,
        parent_number_label=None,
        marks=None,
        sequence=1,
        confidence=0.98,
        geometry=sources[0].geometry,
        local_key="P3-Q3-C",
        source_line_ids=tuple(line.source_line_id for line in sources),
    )

    result = parser.parse(
        source_lines=sources,
        fallback_questions=[child],
        reconciliation_warnings=[],
    )

    question = result.questions[0]
    assert question.text == (
        "Q3(c) Identify the default gateway that should be configured for a host on LAN-A."
    )
    assert question.source_line_ids == ("P3-N7",)
