"""Deterministic, synthetic exam PDFs for M8 CLO/topic alignment and
coverage tests. Designed to pair with tp153_pdf_fixtures.build_complete_tp153_pdf()
(CLO1/CLO2/CLO3, T1/T2/T3) - same fpdf2/_line() pattern as pdf_fixtures.py
and rules_pdf_fixtures.py.
"""

from __future__ import annotations

from fpdf import FPDF, XPos, YPos


def _line(pdf: FPDF, text: str) -> None:
    pdf.multi_cell(0, 8, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def build_exam_citing_all_clos_and_topics_pdf() -> bytes:
    """Every question explicitly cites one CLO and one topic, covering all
    three of each - Satisfied for alignment and coverage rules alike."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    _line(pdf, "Course Exam - Midterm")
    _line(pdf, "Q1. Explain normalization. [CLO1] [T1] [5 marks]")
    _line(pdf, "Q2. Describe entity-relationship modeling. [CLO2] [T2] [5 marks]")
    _line(pdf, "Q3. Write a query using joins. [CLO3] [T3] [5 marks]")
    return bytes(pdf.output())


def build_exam_citing_no_clos_or_topics_pdf() -> bytes:
    """No question cites any CLO/topic reference at all - Not Satisfied for
    alignment and coverage rules alike."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    _line(pdf, "Course Exam - Midterm")
    _line(pdf, "Q1. Explain normalization. [5 marks]")
    _line(pdf, "Q2. Describe entity-relationship modeling. [5 marks]")
    return bytes(pdf.output())


def build_exam_citing_some_clos_and_topics_pdf() -> bytes:
    """Q1 cites CLO1/T1; Q2 cites nothing - Partially Satisfied for
    alignment (some but not all questions cite); Not Satisfied for coverage
    (CLO2/CLO3/T2/T3 remain uncited)."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    _line(pdf, "Course Exam - Midterm")
    _line(pdf, "Q1. Explain normalization. [CLO1] [T1] [5 marks]")
    _line(pdf, "Q2. Describe entity-relationship modeling. [5 marks]")
    return bytes(pdf.output())


def build_exam_citing_two_topics_pdf() -> bytes:
    """Cites exactly T1 and T2 (and no CLOs) - pairs with
    tp153_pdf_fixtures.build_missing_clo_section_tp153_pdf(), whose Course
    Topics section has only T1/T2 (no T3), so this exam fully covers the
    topics that fixture actually provides while leaving CLOs untouched."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    _line(pdf, "Course Exam - Midterm")
    _line(pdf, "Q1. Explain normalization. [T1] [5 marks]")
    _line(pdf, "Q2. Describe entity-relationship modeling. [T2] [5 marks]")
    return bytes(pdf.output())


def build_exam_citing_hyphenated_and_bracketed_variants_pdf() -> bytes:
    """Exercises the citation-variant forms from decision 2 directly:
    bare, hyphenated, and bracketed - all three must be recognized."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    _line(pdf, "Course Exam - Midterm")
    _line(pdf, "Q1. Explain normalization. CLO1 T1 [5 marks]")
    _line(pdf, "Q2. Describe entity-relationship modeling. CLO-2 T-2 [5 marks]")
    _line(pdf, "Q3. Write a query using joins. [CLO3] [T3] [5 marks]")
    return bytes(pdf.output())
