"""Renders a ReportContent snapshot to PDF bytes using fpdf2 - the same
library already used (as a test-only dependency, until this milestone) to
build synthetic exam PDFs for extraction tests. Layout only; all content
decisions (what to include, what text to show) live in content.py.
"""

from __future__ import annotations

from fpdf import FPDF, XPos, YPos

from app.services.reporting.content import ReportContent, ReportFindingEntry

_SCOPE_DISCLAIMER = (
    "This report is limited to the uploaded examination and its populated TP-153 Course "
    "Specification. It does not evaluate student answers or grades, estimate difficulty, "
    "classify Bloom's Taxonomy levels, or issue an accreditation, approval, or rejection "
    "decision. Recommendations are academic support for human review, not institutional "
    "decisions."
)


def _heading(pdf: FPDF, text: str) -> None:
    pdf.set_font("Helvetica", style="B", size=13)
    pdf.multi_cell(0, 9, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", size=11)


def _paragraph(pdf: FPDF, text: str, *, style: str = "") -> None:
    pdf.set_font("Helvetica", style=style, size=11)
    pdf.multi_cell(0, 6, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _score_line(content: ReportContent) -> str:
    if content.score is None:
        return content.score_label or "Insufficient Evidence"
    plural = "" if content.denominator == 1 else "s"
    return f"{content.score} (based on {content.denominator} verified applicable rule{plural})"


def _render_finding(pdf: FPDF, entry: ReportFindingEntry) -> None:
    pdf.set_font("Helvetica", style="B", size=11)
    pdf.multi_cell(
        0,
        6,
        f"{entry.requirement_name} - {entry.status.value}",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.set_font("Helvetica", style="I", size=9)
    pdf.multi_cell(
        0,
        5,
        f"{entry.dimension} | {entry.source_type} ({entry.officiality})",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    _paragraph(pdf, entry.explanation)

    if entry.evidence:
        pdf.set_font("Helvetica", size=9)
        for item in entry.evidence:
            doc = "Exam" if item.source_document.value == "exam" else "TP-153"
            pdf.multi_cell(
                0,
                5,
                f"  - Evidence: {item.evidence_type} ({doc} p.{item.page_number}, "
                f"{item.item_reference})",
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
    else:
        pdf.set_font("Helvetica", style="I", size=9)
        pdf.multi_cell(
            0,
            5,
            "  No evidence was linked to this finding.",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )

    for rec in entry.recommendations:
        pdf.set_font("Helvetica", style="B", size=9)
        pdf.multi_cell(0, 5, f"  Recommendation: {rec.title}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", size=9)
        pdf.multi_cell(0, 5, f"  {rec.text}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(3)


def render_report_pdf(content: ReportContent) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", style="B", size=16)
    pdf.multi_cell(
        0,
        10,
        "AI Exam Quality Platform - Analysis Report",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )

    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(
        0,
        6,
        f"{content.course_code} - {content.course_name}",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.multi_cell(
        0,
        6,
        f"{content.exam_type.value} exam, {content.term}",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.set_font("Helvetica", size=9)
    pdf.multi_cell(
        0,
        5,
        f"Analysis ID: {content.analysis_id} | Generated: "
        f"{content.generated_at.isoformat(timespec='seconds')} | KB version: {content.kb_version}",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(2)

    _heading(pdf, "Scope")
    _paragraph(pdf, _SCOPE_DISCLAIMER, style="I")
    pdf.ln(2)

    _heading(pdf, "Overall Exam Quality Score")
    _paragraph(pdf, _score_line(content))
    _paragraph(
        pdf,
        f"Satisfied: {content.satisfied_count}  |  Partially Satisfied: "
        f"{content.partially_satisfied_count}  |  Not Satisfied: {content.not_satisfied_count}  |  "
        f"Not Verified: {content.not_verified_count}  |  Not Applicable: "
        f"{content.not_applicable_count}",
    )
    pdf.ln(2)

    missing = content.missing_evidence
    if missing:
        _heading(pdf, f"Missing Evidence ({len(missing)})")
        _paragraph(
            pdf,
            "Excluded from the score because required evidence was missing, unreadable, or "
            "insufficient - not because the exam failed the requirement.",
            style="I",
        )
        for entry in missing:
            pdf.set_font("Helvetica", style="B", size=10)
            pdf.multi_cell(0, 5, entry.requirement_name, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", size=10)
            pdf.multi_cell(0, 5, entry.explanation, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)

    _heading(pdf, f"Findings ({len(content.findings)})")
    if not content.findings:
        _paragraph(pdf, "No findings are available for this analysis.", style="I")
    for entry in content.findings:
        _render_finding(pdf, entry)

    output = pdf.output()
    return bytes(output)
