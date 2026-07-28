"""Render a governed :class:`ReportContent` snapshot to PDF bytes.

All academic and operational decisions are assembled in ``content.py``. This
module is presentation only and keeps the user-facing report focused on the
uploaded exam, its findings, recommendations, and traceable evidence.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from fpdf import FPDF, XPos, YPos

from app.services.reporting.content import (
    EvidenceCitation,
    ReportContent,
    ReportFindingEntry,
    ReportItemJudgment,
)

_REPORT_FONT_FAMILY = "ReportUnicode"
_ARABIC_CHARACTER = re.compile(r"[\u0600-\u06ff]")

_REPORT_FONT_CANDIDATES: dict[str, tuple[Path, ...]] = {
    "": (
        Path(os.getenv("REPORT_FONT_REGULAR_PATH", "")),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ),
    "B": (
        Path(os.getenv("REPORT_FONT_BOLD_PATH", "")),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ),
    "I": (
        Path(os.getenv("REPORT_FONT_ITALIC_PATH", "")),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("C:/Windows/Fonts/ariali.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ),
}


def _first_existing_font(candidates: tuple[Path, ...]) -> Path:
    for candidate in candidates:
        if str(candidate) and candidate.is_file():
            return candidate
    raise RuntimeError(
        "No Unicode report font was found. Install fonts-dejavu-core or configure "
        "REPORT_FONT_REGULAR_PATH, REPORT_FONT_BOLD_PATH, and REPORT_FONT_ITALIC_PATH."
    )


def _configure_report_fonts(pdf: FPDF) -> None:
    for style, candidates in _REPORT_FONT_CANDIDATES.items():
        pdf.add_font(
            family=_REPORT_FONT_FAMILY,
            style=style,
            fname=str(_first_existing_font(candidates)),
        )
    # HarfBuzz shaping is required for joined Arabic glyphs and correct
    # bidirectional ordering. uharfbuzz is a declared runtime dependency in
    # pyproject.toml, so a deployment must not silently emit broken Arabic.
    pdf.set_text_shaping(True)


def _set_font(pdf: FPDF, *, style: str = "", size: int = 11) -> None:
    pdf.set_font(_REPORT_FONT_FAMILY, style=style, size=size)


_SCOPE_DISCLAIMER = (
    "This report is limited to the uploaded examination and its populated TP-153 Course "
    "Specification. It does not evaluate student answers or grades, estimate difficulty, "
    "classify Bloom's Taxonomy levels, or issue an accreditation, approval, or rejection "
    "decision. Recommendations are academic support for human review, not institutional "
    "decisions."
)


def _heading(pdf: FPDF, text: str) -> None:
    _set_font(pdf, style="B", size=13)
    pdf.multi_cell(0, 9, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    _set_font(pdf, size=11)


def _subheading(pdf: FPDF, text: str) -> None:
    _set_font(pdf, style="B", size=11)
    pdf.multi_cell(0, 7, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    _set_font(pdf, size=10)


def _is_predominantly_arabic(text: str) -> bool:
    arabic_count = len(_ARABIC_CHARACTER.findall(text))
    latin_count = sum(char.isascii() and char.isalpha() for char in text)
    return arabic_count > latin_count


def _paragraph(pdf: FPDF, text: str, *, style: str = "", size: int = 11) -> None:
    _set_font(pdf, style=style, size=size)
    # Whole Arabic paragraphs are right-aligned. Mixed evidence/citation lines
    # remain left-aligned while fpdf2 shapes their Arabic fragments correctly.
    alignment = "R" if _is_predominantly_arabic(text) else "L"
    pdf.multi_cell(
        0,
        6,
        text,
        align=alignment,
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )


def _score_line(content: ReportContent) -> str:
    if content.score is None:
        return content.score_label or "Insufficient Evidence"
    plural = "" if content.denominator == 1 else "s"
    return f"{content.score}% (based on {content.denominator} verified applicable rule{plural})"


def _citation_line(item: EvidenceCitation) -> str:
    document = "Exam" if item.source_document.value == "exam" else "TP-153"
    return f"{item.item_reference} | {document} page {item.page_number} | {item.evidence_type}"


def _render_item_judgment(
    pdf: FPDF,
    entry: ReportFindingEntry,
    judgment: ReportItemJudgment,
) -> None:
    relationship = entry.rule_id in {"RULE001", "RULE007"} and judgment.is_derived_relationship
    label = "AI-derived advisory relationship" if relationship else "Governed item judgment"
    _paragraph(pdf, f"  {label} - {judgment.status.value}", style="B", size=9)
    if relationship:
        _paragraph(
            pdf,
            "  This relationship is an analysis output, not an official TP-153 mapping, and "
            "does not overwrite source evidence.",
            style="I",
            size=8,
        )

    if judgment.source_evidence is not None:
        _paragraph(
            pdf,
            f"  Source: {_citation_line(judgment.source_evidence)}",
            size=9,
        )
    else:
        _paragraph(
            pdf,
            f"  Source evidence reference unavailable: {judgment.source_evidence_id}",
            style="I",
            size=9,
        )

    if judgment.target_evidence:
        for target in judgment.target_evidence:
            _paragraph(pdf, f"  Related evidence: {_citation_line(target)}", size=9)
    elif judgment.target_evidence_ids:
        _paragraph(
            pdf,
            "  Related evidence references were retained but could not be resolved in this "
            "report snapshot.",
            style="I",
            size=9,
        )
    else:
        _paragraph(pdf, "  No target relationship was asserted.", style="I", size=9)

    _paragraph(pdf, f"  Concise reasoning: {judgment.reasoning}", size=9)


def _render_finding(pdf: FPDF, entry: ReportFindingEntry) -> None:
    _set_font(pdf, style="B", size=11)
    pdf.multi_cell(
        0,
        6,
        f"{entry.requirement_name} - {entry.status.value}",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    _set_font(pdf, style="I", size=9)
    pdf.multi_cell(
        0,
        5,
        f"{entry.dimension} | {entry.source_type} ({entry.officiality}) | "
        f"{entry.requirement_id} / {entry.rule_id}",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    _paragraph(pdf, entry.explanation)

    if entry.confidence_level is not None:
        _paragraph(
            pdf,
            f"Semantic confidence: {entry.confidence_level.value} "
            "(categorical only; not a score, severity, priority, probability, or weight)",
            style="B",
            size=9,
        )
    if entry.evaluation_reasoning:
        _paragraph(
            pdf,
            f"Governed decision reasoning: {entry.evaluation_reasoning}",
            size=9,
        )
    for basis in entry.confidence_basis:
        _paragraph(pdf, f"  Confidence basis: {basis}", size=9)

    if entry.item_judgments:
        _paragraph(
            pdf,
            f"Evidence-linked item judgments ({len(entry.item_judgments)}):",
            style="B",
            size=9,
        )
        for judgment in entry.item_judgments:
            _render_item_judgment(pdf, entry, judgment)

    if entry.evidence:
        _paragraph(pdf, f"Linked evidence ({len(entry.evidence)}):", style="B", size=9)
        for item in entry.evidence:
            _paragraph(pdf, f"  - {_citation_line(item)}", size=9)
    else:
        _paragraph(pdf, "No evidence was linked to this finding.", style="I", size=9)

    if entry.retrieved_knowledge_ids:
        _paragraph(
            pdf,
            "Controlled KB references: " + ", ".join(entry.retrieved_knowledge_ids),
            size=9,
        )

    provenance = [
        value
        for value in (
            f"Provider: {entry.ai_provider}" if entry.ai_provider else None,
            f"Model: {entry.ai_model}" if entry.ai_model else None,
            (f"Prompt: {entry.prompt_template_version}" if entry.prompt_template_version else None),
            f"KB: {entry.finding_kb_version}" if entry.finding_kb_version else None,
        )
        if value is not None
    ]
    if provenance:
        _paragraph(pdf, "AI provenance: " + " | ".join(provenance), style="I", size=8)

    for recommendation in entry.recommendations:
        _paragraph(pdf, f"Recommendation: {recommendation.title}", style="B", size=9)
        _paragraph(pdf, recommendation.text, size=9)

    pdf.ln(3)


def render_report_pdf(content: ReportContent) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    _configure_report_fonts(pdf)
    pdf.add_page()

    _set_font(pdf, style="B", size=16)
    pdf.multi_cell(
        0,
        10,
        "AI Exam Quality Platform - Analysis Report",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )

    _paragraph(pdf, f"{content.course_code} - {content.course_name}")
    _paragraph(pdf, f"{content.exam_type.value} exam, {content.term}")
    _paragraph(
        pdf,
        f"Analysis ID: {content.analysis_id} | Generated: "
        f"{content.generated_at.isoformat(timespec='seconds')} | KB version: "
        f"{content.kb_version}",
        size=9,
    )
    pdf.ln(2)

    _heading(pdf, "Scope")
    _paragraph(pdf, _SCOPE_DISCLAIMER, style="I")
    pdf.ln(2)

    _heading(pdf, "Overall Exam Quality Score")
    _paragraph(pdf, _score_line(content))
    _paragraph(
        pdf,
        f"Satisfied: {content.satisfied_count} | Partially Satisfied: "
        f"{content.partially_satisfied_count} | Not Satisfied: "
        f"{content.not_satisfied_count} | Not Verified: {content.not_verified_count} | "
        f"Not Applicable: {content.not_applicable_count}",
        size=10,
    )
    _paragraph(
        pdf,
        "Not Verified and Not Applicable are visible but excluded from the denominator. "
        "Semantic confidence never changes scoring weight.",
        style="I",
        size=9,
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
            _subheading(pdf, entry.requirement_name)
            _paragraph(pdf, entry.explanation, size=10)
        pdf.ln(2)

    _heading(pdf, f"Findings ({len(content.findings)})")
    if not content.findings:
        _paragraph(pdf, "No findings are available for this analysis.", style="I")
    for entry in content.findings:
        _render_finding(pdf, entry)

    output = pdf.output()
    return bytes(output)
