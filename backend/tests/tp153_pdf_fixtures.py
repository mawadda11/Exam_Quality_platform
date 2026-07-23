"""Deterministic, synthetic text-based TP-153 PDFs for M5 extraction tests.

Built programmatically with fpdf2 rather than committed as binary files -
the repo's .gitignore excludes *.pdf entirely, and generating the PDF from
readable Python source is easier to review and keep deterministic anyway.
This module is test-only; fpdf2 is a dev dependency, not a runtime one.
"""

from __future__ import annotations

from fpdf import FPDF, XPos, YPos


def _line(pdf: FPDF, text: str) -> None:
    pdf.multi_cell(0, 8, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def build_complete_tp153_pdf() -> bytes:
    """A complete, two-page TP-153: CLOs and topics on page 1, assessment
    methods on page 2. 3 CLOs, 3 topics, 3 assessment records."""
    pdf = FPDF()

    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    _line(pdf, "Course Specification (TP-153)")
    _line(pdf, "Course Learning Outcomes")
    _line(pdf, "CLO1: Explain fundamental database design principles. [PLO2]")
    _line(pdf, "CLO2: Apply normalization techniques to relational schemas. [PLO3]")
    _line(pdf, "CLO3: Design and implement SQL queries for data retrieval. [PLO2]")
    _line(pdf, "Course Topics")
    _line(pdf, "T1: Introduction to Databases - 3 hours")
    _line(pdf, "T2: Entity-Relationship Modeling - 4 hours")
    _line(pdf, "T3: Normalization - 5 hours")

    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    _line(pdf, "Assessment Methods")
    _line(pdf, "Method: Midterm Exam | Activity: Written Exam | Percentage: 20%")
    _line(pdf, "Method: Final Exam | Activity: Written Exam | Percentage: 30%")
    _line(pdf, "Method: Assignments | Activity: Homework | Percentage: 15%")

    return bytes(pdf.output())


def build_missing_clo_section_tp153_pdf() -> bytes:
    """A TP-153 with the entire Course Learning Outcomes section omitted -
    topics and assessment methods are present and complete. The extractor
    must report a missing-evidence marker for CLOs, never invent one."""
    pdf = FPDF()

    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    _line(pdf, "Course Specification (TP-153)")
    _line(pdf, "Course Topics")
    _line(pdf, "T1: Introduction to Databases - 3 hours")
    _line(pdf, "T2: Entity-Relationship Modeling - 4 hours")

    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    _line(pdf, "Assessment Methods")
    _line(pdf, "Method: Midterm Exam | Activity: Written Exam | Percentage: 20%")

    return bytes(pdf.output())


def build_incomplete_assessment_tp153_pdf() -> bytes:
    """A TP-153 with complete CLOs/topics but one assessment line missing
    its percentage - the extractor must still capture method and activity,
    with percentage=None, rather than dropping the record entirely."""
    pdf = FPDF()

    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    _line(pdf, "Course Specification (TP-153)")
    _line(pdf, "Course Learning Outcomes")
    _line(pdf, "CLO1: Explain fundamental database design principles. [PLO2]")
    _line(pdf, "Course Topics")
    _line(pdf, "T1: Introduction to Databases - 3 hours")
    _line(pdf, "Assessment Methods")
    _line(pdf, "Method: Midterm Exam | Activity: Written Exam | Percentage: 20%")
    _line(pdf, "Method: Lab Work | Activity: Practical Session")

    return bytes(pdf.output())
