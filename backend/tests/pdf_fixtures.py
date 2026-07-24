"""Deterministic, synthetic text-based exam PDFs for M4 extraction tests.

Built programmatically with fpdf2 rather than committed as binary files -
the repo's .gitignore excludes *.pdf entirely, and generating the PDF from
readable Python source is easier to review and keep deterministic anyway.
This module is test-only; fpdf2 is a dev dependency, not a runtime one.
"""

from __future__ import annotations

import io

import pdfplumber
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


def build_completely_blank_pdf() -> bytes:
    """A single page with zero content drawn on it at all - unlike
    build_blank_pdf() (which has a real text layer, just no question
    content), pdfplumber sees no extractable text here, triggering the
    OCR-fallback path."""
    pdf = FPDF()
    pdf.add_page()
    return bytes(pdf.output())


def build_digital_page_then_blank_page_pdf() -> bytes:
    """Page 1: real digital text ending mid-question ("Q2." + "(a)").
    Page 2: genuinely empty (no content drawn at all) - pdfplumber sees zero
    extractable text on it, triggering the OCR-fallback path, same as a real
    scanned page would. Used with an injected fake OCR engine (which ignores
    actual image content) to test that parent-label/sequence state survives
    a digital-to-OCR page transition, without needing real OCR to recognize
    anything on this deliberately blank page."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    _line(pdf, "Q2. A question spanning a page break.")
    _line(pdf, "(a) First subpart. [1 marks]")

    pdf.add_page()  # intentionally blank - no set_font/text calls at all

    return bytes(pdf.output())


def build_scanned_looking_exam_pdf() -> bytes:
    """A single-page PDF with NO text layer at all - only a rasterized image
    of build_synthetic_exam_pdf()'s first page - simulating a genuinely
    scanned exam page for OCR-fallback tests.

    Built by rendering the known-good digital fixture through pdfplumber's
    own rasterizer and re-embedding the resulting image as a full-page image
    in a fresh PDF, rather than depending on a bundled font file to draw text
    directly onto an image - this stays fully deterministic and needs no new
    binary assets. Because the source content is
    build_synthetic_exam_pdf()'s own first page, the expected recovered text
    (instructions, Q1, Q2/(a)/(b)) is already known from that fixture.
    """
    with pdfplumber.open(io.BytesIO(build_synthetic_exam_pdf())) as document:
        page = document.pages[0]
        width, height = page.width, page.height
        image = page.to_image(resolution=200).original

    image_buffer = io.BytesIO()
    image.save(image_buffer, format="PNG")
    image_buffer.seek(0)

    pdf = FPDF(unit="pt", format=(width, height))
    pdf.add_page()
    pdf.image(image_buffer, x=0, y=0, w=width, h=height)
    return bytes(pdf.output())
