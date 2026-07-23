"""Deterministic, synthetic text-based exam PDFs for M6 rule tests (marks
and total arithmetic, numbering and duplicate-numbering).

Built programmatically with fpdf2 rather than committed as binary files -
same reasoning as pdf_fixtures.py and tp153_pdf_fixtures.py. This module is
test-only; fpdf2 is a dev dependency, not a runtime one.

A sixth scenario - "missing numbering evidence where applicable" - reuses
pdf_fixtures.build_blank_pdf() directly rather than duplicating an
equivalent empty fixture here.
"""

from __future__ import annotations

from fpdf import FPDF, XPos, YPos


def _line(pdf: FPDF, text: str) -> None:
    pdf.multi_cell(0, 8, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def build_exam_with_correct_total_pdf() -> bytes:
    """Q1 [5] + Q2(a) [3] + Q2(b) [4] + Q3 [3] = 15, declared total 15."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    _line(pdf, "Course Exam - Midterm")
    _line(pdf, "Q1. Explain the concept of normalization. [5 marks]")
    _line(pdf, "Q2. Consider the following scenario.")
    _line(pdf, "(a) Identify the primary key. [3 marks]")
    _line(pdf, "(b) Write a query to retrieve records. [4 marks]")
    _line(pdf, "Q3. Define referential integrity. [3 marks]")
    _line(pdf, "Total Marks: 15")
    return bytes(pdf.output())


def build_exam_with_incorrect_total_pdf() -> bytes:
    """Same questions as the correct-total fixture (sum is 15), but the
    declared total is wrong (20)."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    _line(pdf, "Course Exam - Midterm")
    _line(pdf, "Q1. Explain the concept of normalization. [5 marks]")
    _line(pdf, "Q2. Consider the following scenario.")
    _line(pdf, "(a) Identify the primary key. [3 marks]")
    _line(pdf, "(b) Write a query to retrieve records. [4 marks]")
    _line(pdf, "Q3. Define referential integrity. [3 marks]")
    _line(pdf, "Total Marks: 20")
    return bytes(pdf.output())


def build_exam_with_missing_marks_evidence_pdf() -> bytes:
    """Q2 is a standalone top-level question with no marks bracket and no
    children - an unreadable/missing required mark value for the arithmetic
    rule, even though a declared total is present."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    _line(pdf, "Course Exam - Midterm")
    _line(pdf, "Q1. Explain the concept of normalization. [4 marks]")
    _line(pdf, "Q2. Explain the significance of ACID properties.")
    _line(pdf, "Total Marks: 10")
    return bytes(pdf.output())


def build_exam_with_duplicate_top_level_numbering_pdf() -> bytes:
    """ "Q2" is used twice as a top-level question number - a genuine
    top-level duplicate the numbering rule must detect."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    _line(pdf, "Course Exam - Midterm")
    _line(pdf, "Q1. Explain the concept of normalization. [5 marks]")
    _line(pdf, "Q2. First scenario question. [3 marks]")
    _line(pdf, "Q2. Second scenario question, mistakenly renumbered. [4 marks]")
    return bytes(pdf.output())


def build_exam_with_valid_child_numbering_pdf() -> bytes:
    """Q1 and Q2 each have (a)/(b) children - "Q1(a)"/"Q1(b)" and
    "Q2(a)"/"Q2(b)" are all unique full labels despite sharing the letters
    (a)/(b); the numbering rule must not flag these as duplicates."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    _line(pdf, "Course Exam - Midterm")
    _line(pdf, "Q1. Consider the following scenario.")
    _line(pdf, "(a) Identify the primary key. [2 marks]")
    _line(pdf, "(b) Write a query to retrieve records. [3 marks]")
    _line(pdf, "Q2. Consider a second scenario.")
    _line(pdf, "(a) Identify the foreign key. [2 marks]")
    _line(pdf, "(b) Write a query to update records. [3 marks]")
    return bytes(pdf.output())
