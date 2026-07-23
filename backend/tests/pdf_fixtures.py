"""Deterministic, synthetic text-based exam PDFs for M4 extraction tests.

Built programmatically with fpdf2 rather than committed as binary files -
the repo's .gitignore excludes *.pdf entirely, and generating the PDF from
readable Python source is easier to review and keep deterministic anyway.
This module is test-only; fpdf2 is a dev dependency, not a runtime one.
"""

from __future__ import annotations

from fpdf import FPDF, XPos, YPos


def _line(pdf: FPDF, text: str) -> None:
    pdf.multi_cell(0, 8, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def build_synthetic_exam_pdf() -> bytes:
    """A small, fixed-structure, text-based digital exam PDF.

    Page 1: instructions, Q1 (standalone, 5 marks), Q2 with (a)/(b).
    Page 2: Q3 with (a)/(b), Q4 (standalone, 6 marks).

    8 question rows total, in sequence order:
    Q1, Q2, Q2(a), Q2(b), Q3, Q3(a), Q3(b), Q4.
    """
    pdf = FPDF()

    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    _line(pdf, "Course Exam - Midterm")
    _line(pdf, "Instructions: Answer all questions. Show your work clearly.")
    _line(pdf, "Q1. Explain the concept of normalization in database design. [5 marks]")
    _line(pdf, "Q2. Consider the following scenario.")
    _line(pdf, "(a) Identify the primary key for the given table. [3 marks]")
    _line(pdf, "(b) Write a SQL query to retrieve all active records. [4 marks]")

    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    _line(pdf, "Q3. Short answer questions.")
    _line(pdf, "(a) Define polymorphism in object-oriented programming. [2 marks]")
    _line(pdf, "(b) Provide one example of polymorphism in Python. [3 marks]")
    _line(pdf, "Q4. Write a function that reverses a string without built-in reverse. [6 marks]")

    return bytes(pdf.output())


def build_blank_pdf() -> bytes:
    """A structurally valid, parseable PDF with no question content - used
    to test the zero-questions-found path without triggering a parse error."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    _line(pdf, "This page intentionally contains no exam questions.")
    return bytes(pdf.output())
