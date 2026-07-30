"""Render a governed :class:`ReportContent` snapshot to PDF bytes.

Localization is applied only while rendering. Governed wording and reasoning
remain unchanged in storage and are retained as clearly labelled original
source wording in Arabic reports.

The primary report body (sections 1-13) stays faculty-readable and concise:
no provider/model/prompt/knowledge-base identifiers, no raw evidence-ID
lists, no numeric confidence. That technical provenance is preserved - never
deleted - in the separated Technical Traceability Appendix (section 14) as a
short summary (a findings-level provenance table plus judgment counts), not
a full evidence-linked judgment inventory. The complete per-judgment source
and target evidence citations remain in the stored findings records and are
available through the platform's findings data for detailed audit.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from fpdf import FPDF, XPos, YPos
from fpdf.enums import Align
from fpdf.errors import FPDFException
from fpdf.fonts import FontFace

from app.core.domain import AcademicStatus, ReportLanguage
from app.services.reporting.content import (
    ReportContent,
    ReportFindingEntry,
    ReportRelationshipEntry,
)
from app.services.reporting.presentation import (
    finding_explanation,
    governed_label,
    recommendation_text,
    requirement_name,
)

logger = logging.getLogger(__name__)

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

_EN = {
    "title": "Exam Quality Analyzer - Analysis Report",
    "exam": "exam",
    "report_id": "Report ID",
    "generated": "Generated",
    "language_label": "Report language",
    "scope": "Scope Disclaimer",
    "scope_text": (
        "This report applies only to the uploaded examination and the corresponding Course "
        "Specification. The platform does not issue accreditation decisions, does not evaluate "
        "the complete academic program, and does not replace academic judgment. The faculty "
        "member remains responsible for the final examination decision."
    ),
    "s1_header": "1. Report Header",
    "s2_summary": "2. Executive Summary",
    "s3_score": "3. Overall Exam Quality Score",
    "s4_distribution": "4. Status Distribution",
    "s5_exam_summary": "5. Exam Summary",
    "s6_clo": "6. CLO Analysis",
    "s7_topic": "7. Topic Analysis",
    "s8_marks": "8. Marks & Structure",
    "s9_materials": "9. Materials & References",
    "s10_findings": "10. Key Findings",
    "s11_missing": "11. Missing or Unverified Evidence",
    "s12_recommendations": "12. Recommendations",
    "s13_scope": "13. Scope Disclaimer",
    "s14_appendix": "14. Technical Traceability Appendix",
    "summary_text": (
        "This report analyzes the uploaded exam against the Course Specification, covering "
        "question clarity, CLO and topic alignment and coverage, marks and structure, and "
        "supporting materials."
    ),
    "overall_result_scored": (
        "Overall result: {score}% based on {count} verified applicable checks."
    ),
    "overall_result_label": "Overall result: {label}.",
    "strongest_areas": "Strongest verified areas: {areas}.",
    "weakest_areas": "Main areas requiring improvement: {areas}.",
    "missing_summary": (
        "{count} result(s) could not be verified due to missing or unreliable evidence."
    ),
    "based_on": "based on {count} verified applicable {rules}",
    "rule": "rule",
    "rules": "rules",
    "insufficient": "Insufficient Evidence",
    "distribution_note": (
        "Not Verified and Not Applicable results remain visible but are excluded from the "
        "score denominator."
    ),
    "col_status": "Status",
    "col_count": "Count",
    "exam_summary_question_count": "Independently scorable questions",
    "exam_summary_declared": "Declared total marks",
    "exam_summary_calculated": "Calculated total marks",
    "exam_summary_materials": "Supporting materials",
    "exam_summary_missing_refs": "Missing or ambiguous references",
    "col_clo": "CLO",
    "col_clo_text": "CLO text",
    "col_topic": "Course Topic",
    "col_linked_questions": "Linked questions",
    "col_total_marks": "Total marks",
    "col_coverage_status": "Coverage status",
    "text_unavailable": "Source text unavailable.",
    "none": "None",
    "no_findings": "No findings are available for this analysis.",
    "col_check": "Check",
    "col_reason": "Reason",
    "col_referenced_item": "Referenced item",
    "col_relationship_result": "Relationship result",
    "col_page": "Page",
    "no_materials": "No question-to-material references were identified.",
    "strengths": "Strengths",
    "areas_for_improvement": "Areas for Improvement",
    "recommendation": "Recommendation",
    "no_recommendations": "None",
    "col_requirement": "Requirement",
    "col_rule": "Rule",
    "col_confidence": "Confidence",
    "col_evaluator": "Evaluation method",
    "col_provenance": "Technical provenance",
    "col_evidence_count": "Evidence items",
    "appendix_note": (
        "This concise appendix records rule-level traceability. Full evidence excerpts and "
        "item-level source/target links remain preserved in the platform audit records."
    ),
    "appendix_supporting_summary": (
        "{materials} supporting material(s) and {annotations} annotation(s) are preserved in "
        "the audit records; full code, table, and caption excerpts are not repeated here."
    ),
    "appendix_provenance": "Model provenance",
    "appendix_provenance_summary": "Recorded provider/model/prompt combinations: {values}.",
    "appendix_no_provenance": "No model provenance was recorded for this analysis.",
    "appendix_judgments": "Evidence-linked item judgments",
    "appendix_judgments_summary": (
        "{count} evidence-linked item judgments were evaluated for this analysis. Full source "
        "and target evidence citations remain preserved in the stored findings records and are "
        "available through the platform's findings data for detailed audit."
    ),
    "capability_legacy": "Not applicable (legacy analysis)",
    "col_source": "Source evidence",
    "col_target": "Target evidence",
    "page": "page",
    "exam_document": "Exam",
    "resolved": "Linked",
    "ambiguous": "Ambiguous reference",
    "unresolved": "Missing or unresolved reference",
}

_AR = {
    "title": "محلل جودة الاختبارات - تقرير التحليل",
    "exam": "اختبار",
    "report_id": "معرّف التقرير",
    "generated": "تاريخ الإنشاء",
    "language_label": "لغة التقرير",
    "scope": "إخلاء مسؤولية النطاق",
    "scope_text": (
        "يقتصر هذا التقرير على الاختبار المرفوع وتوصيف المقرر المطابق له. لا تصدر المنصة قرارات "
        "اعتماد، ولا تقيّم البرنامج الأكاديمي كاملًا، ولا تحل محل التقدير الأكاديمي. يظل عضو هيئة "
        "التدريس مسؤولًا عن القرار النهائي بشأن الاختبار."
    ),
    "s1_header": "١. ترويسة التقرير",
    "s2_summary": "٢. الملخص التنفيذي",
    "s3_score": "٣. الدرجة الإجمالية لجودة الاختبار",
    "s4_distribution": "٤. توزيع الحالات",
    "s5_exam_summary": "٥. ملخص الاختبار",
    "s6_clo": "٦. تحليل نواتج التعلم",
    "s7_topic": "٧. تحليل موضوعات المقرر",
    "s8_marks": "٨. الدرجات والبنية",
    "s9_materials": "٩. المواد المساندة والإحالات",
    "s10_findings": "١٠. أبرز النتائج",
    "s11_missing": "١١. الأدلة المفقودة أو غير المتحقق منها",
    "s12_recommendations": "١٢. التوصيات",
    "s13_scope": "١٣. إخلاء مسؤولية النطاق",
    "s14_appendix": "١٤. ملحق التتبع التقني",
    "summary_text": (
        "يحلل هذا التقرير الاختبار المرفوع مقارنةً بتوصيف المقرر، ويغطي وضوح الأسئلة، ومواءمة "
        "وتغطية نواتج التعلم والموضوعات، والدرجات والبنية، والمواد المساندة."
    ),
    "overall_result_scored": (
        "النتيجة الإجمالية: {score}% استنادًا إلى {count} فحصًا منطبقًا تم التحقق منه."
    ),
    "overall_result_label": "النتيجة الإجمالية: {label}.",
    "strongest_areas": "أقوى الجوانب التي تم التحقق منها: {areas}.",
    "weakest_areas": "أبرز الجوانب التي تحتاج إلى تحسين: {areas}.",
    "missing_summary": "تعذر التحقق من {count} نتيجة بسبب أدلة مفقودة أو غير موثوقة.",
    "based_on": "استنادًا إلى {count} قاعدة منطبقة تم التحقق منها",
    "rule": "قاعدة",
    "rules": "قواعد",
    "insufficient": "أدلة غير كافية",
    "distribution_note": (
        "تظل نتائج «غير متحقق» و«غير منطبق» ظاهرة، لكنها مستبعدة من مقام الدرجة."
    ),
    "col_status": "الحالة",
    "col_count": "العدد",
    "exam_summary_question_count": "الأسئلة القابلة للتقييم المستقل",
    "exam_summary_declared": "إجمالي الدرجات المعلن",
    "exam_summary_calculated": "إجمالي الدرجات المحسوب",
    "exam_summary_materials": "المواد المساندة",
    "exam_summary_missing_refs": "الإحالات المفقودة أو الملتبسة",
    "col_clo": "ناتج التعلم",
    "col_clo_text": "نص ناتج التعلم",
    "col_topic": "موضوع المقرر",
    "col_linked_questions": "الأسئلة المرتبطة",
    "col_total_marks": "إجمالي الدرجات",
    "col_coverage_status": "حالة التغطية",
    "text_unavailable": "نص المصدر غير متاح.",
    "none": "لا يوجد",
    "no_findings": "لا توجد نتائج تقييم متاحة لهذا التحليل.",
    "col_check": "الفحص",
    "col_reason": "السبب",
    "col_referenced_item": "العنصر المشار إليه",
    "col_relationship_result": "نتيجة الارتباط",
    "col_page": "الصفحة",
    "no_materials": "لم يُحدَّد أي ارتباط بين الأسئلة والمواد.",
    "strengths": "نقاط القوة",
    "areas_for_improvement": "جوانب تحتاج إلى تحسين",
    "recommendation": "التوصية",
    "no_recommendations": "لا يوجد",
    "col_requirement": "المتطلب",
    "col_rule": "القاعدة",
    "col_confidence": "الثقة",
    "col_evaluator": "طريقة التقييم",
    "col_provenance": "المصدر التقني",
    "col_evidence_count": "عدد الأدلة",
    "appendix_note": (
        "يسجل هذا الملحق المختصر التتبع على مستوى القواعد. تبقى مقتطفات الأدلة الكاملة وروابط "
        "المصدر والهدف على مستوى العناصر محفوظة في سجلات تدقيق المنصة."
    ),
    "appendix_supporting_summary": (
        "حُفظت {materials} مادة مساندة و{annotations} ملاحظة في سجلات التدقيق؛ ولا تتكرر هنا "
        "مقتطفات الأكواد والجداول والتعليقات كاملة."
    ),
    "appendix_provenance": "مصدر النموذج",
    "appendix_provenance_summary": "تركيبات المزوّد والنموذج والقالب المسجلة: {values}.",
    "appendix_no_provenance": "لم يُسجل مصدر نموذج لهذا التحليل.",
    "appendix_judgments": "أحكام العناصر المرتبطة بالأدلة",
    "appendix_judgments_summary": (
        "جرى تقييم {count} من أحكام العناصر المرتبطة بالأدلة لهذا التحليل. تبقى إحالات الأدلة "
        "المصدرية والمستهدفة كاملة محفوظة في سجلات نتائج التقييم المخزنة، وهي متاحة عبر بيانات "
        "المنصة للتدقيق التفصيلي."
    ),
    "capability_legacy": "غير منطبق (تحليل سابق)",
    "col_source": "الدليل المصدر",
    "col_target": "الدليل الهدف",
    "page": "صفحة",
    "exam_document": "الاختبار",
    "resolved": "مرتبط",
    "ambiguous": "إحالة ملتبسة",
    "unresolved": "إحالة مفقودة أو غير محلولة",
}

_STATUS_AR: dict[AcademicStatus, str] = {
    AcademicStatus.SATISFIED: "مستوفى",
    AcademicStatus.PARTIALLY_SATISFIED: "مستوفى جزئيًا",
    AcademicStatus.NOT_SATISFIED: "غير مستوفى",
    AcademicStatus.NOT_VERIFIED: "غير متحقق",
    AcademicStatus.NOT_APPLICABLE: "غير منطبق",
}

_STATUS_DISTRIBUTION_ORDER: tuple[AcademicStatus, ...] = (
    AcademicStatus.SATISFIED,
    AcademicStatus.PARTIALLY_SATISFIED,
    AcademicStatus.NOT_SATISFIED,
    AcademicStatus.NOT_VERIFIED,
    AcademicStatus.NOT_APPLICABLE,
)

_MARKS_STRUCTURE_DIMENSIONS = {"Marks and Totals", "Numbering and Structure"}
_ATTENTION_STATUSES = {AcademicStatus.PARTIALLY_SATISFIED, AcademicStatus.NOT_SATISFIED}


def _strings(language: ReportLanguage) -> dict[str, str]:
    return _AR if language is ReportLanguage.ARABIC else _EN


def _status(status: AcademicStatus, language: ReportLanguage) -> str:
    return _STATUS_AR[status] if language is ReportLanguage.ARABIC else status.value


def _confidence(value: str, language: ReportLanguage) -> str:
    if language is not ReportLanguage.ARABIC:
        return value
    return {"High": "مرتفع", "Medium": "متوسط", "Low": "منخفض"}.get(value, value)


def _align(language: ReportLanguage) -> Align:
    return Align.R if language is ReportLanguage.ARABIC else Align.L


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
    try:
        pdf.set_text_shaping(True)
    except FPDFException:
        # English reports and test environments must remain usable when the
        # optional HarfBuzz wheel is unavailable. Production images install
        # uharfbuzz, which enables correct Arabic joining and bidi shaping.
        logger.warning("Arabic text shaping is unavailable; rendering without HarfBuzz.")


def _set_font(pdf: FPDF, *, style: str = "", size: int = 11) -> None:
    pdf.set_font(_REPORT_FONT_FAMILY, style=style, size=size)


def _is_predominantly_arabic(text: str) -> bool:
    arabic_count = len(_ARABIC_CHARACTER.findall(text))
    latin_count = sum(char.isascii() and char.isalpha() for char in text)
    return arabic_count > latin_count


def _paragraph(pdf: FPDF, text: str, *, style: str = "", size: int = 11) -> None:
    _set_font(pdf, style=style, size=size)
    alignment = "R" if _is_predominantly_arabic(text) else "L"
    pdf.multi_cell(
        0,
        6,
        text,
        align=alignment,
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )


def _section_heading(pdf: FPDF, text: str, language: ReportLanguage) -> None:
    # Keep a section heading with at least the first paragraph/table header.
    # This prevents headings such as "CLO Analysis" from being stranded at
    # the bottom of one page while the table starts on the next page.
    if pdf.will_page_break(45):
        pdf.add_page()
    pdf.ln(1)
    _set_font(pdf, style="B", size=13)
    pdf.multi_cell(0, 7, text, align=_align(language), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(3)


def _subheading(pdf: FPDF, text: str) -> None:
    _paragraph(pdf, text, style="B", size=11)


def _score_line(content: ReportContent, language: ReportLanguage) -> str:
    strings = _strings(language)
    if content.score is None:
        return (
            strings["insufficient"]
            if language is ReportLanguage.ARABIC
            else (content.score_label or strings["insufficient"])
        )
    if language is ReportLanguage.ARABIC:
        basis = strings["based_on"].format(count=content.denominator, rules=strings["rules"])
    else:
        rules = strings["rule"] if content.denominator == 1 else strings["rules"]
        basis = strings["based_on"].format(count=content.denominator, rules=rules)
    return f"{content.score}% ({basis})"


def _table_headings_style() -> FontFace:
    return FontFace(emphasis="BOLD", fill_color=(235, 238, 242))


def _simple_table(
    pdf: FPDF,
    headers: list[str],
    rows: list[list[str]],
    *,
    language: ReportLanguage,
    col_widths: list[float] | None = None,
) -> None:
    if not rows:
        return
    align = "R" if language is ReportLanguage.ARABIC else "L"
    with pdf.table(
        headings_style=_table_headings_style(),
        text_align=align,
        col_widths=col_widths,
        line_height=5.2,
        padding=1.4,
    ) as table:
        header_row = table.row()
        for header in headers:
            header_row.cell(header)
        for data_row in rows:
            row = table.row()
            for value in data_row:
                row.cell(value)


def _executive_summary(pdf: FPDF, content: ReportContent, language: ReportLanguage) -> None:
    strings = _strings(language)
    _paragraph(pdf, strings["summary_text"], style="I")
    if content.score is not None:
        _paragraph(
            pdf,
            strings["overall_result_scored"].format(score=content.score, count=content.denominator),
        )
    else:
        _paragraph(
            pdf,
            strings["overall_result_label"].format(
                label=content.score_label or strings["insufficient"]
            ),
        )
    strengths = content.strengths
    areas = content.areas_for_improvement
    missing = content.missing_evidence
    if strengths:
        dimensions = list(dict.fromkeys(governed_label(f.dimension, language) for f in strengths))
        _paragraph(pdf, strings["strongest_areas"].format(areas=", ".join(dimensions[:3])))
    if areas:
        dimensions = list(dict.fromkeys(governed_label(f.dimension, language) for f in areas))
        _paragraph(pdf, strings["weakest_areas"].format(areas=", ".join(dimensions[:3])))
    if missing:
        _paragraph(pdf, strings["missing_summary"].format(count=len(missing)))


def _status_distribution_table(pdf: FPDF, content: ReportContent, language: ReportLanguage) -> None:
    strings = _strings(language)
    counts = {
        AcademicStatus.SATISFIED: content.satisfied_count,
        AcademicStatus.PARTIALLY_SATISFIED: content.partially_satisfied_count,
        AcademicStatus.NOT_SATISFIED: content.not_satisfied_count,
        AcademicStatus.NOT_VERIFIED: content.not_verified_count,
        AcademicStatus.NOT_APPLICABLE: content.not_applicable_count,
    }
    rows = [
        [_status(status, language), str(counts[status])] for status in _STATUS_DISTRIBUTION_ORDER
    ]
    _simple_table(
        pdf,
        [strings["col_status"], strings["col_count"]],
        rows,
        language=language,
        col_widths=[130, 40],
    )
    _paragraph(pdf, strings["distribution_note"], style="I", size=9)


def _exam_summary_section(pdf: FPDF, content: ReportContent, language: ReportLanguage) -> None:
    strings = _strings(language)
    summary = content.exam_summary
    if summary is None:
        return
    rows = [
        [strings["exam_summary_question_count"], str(summary.scorable_question_count)],
        [
            strings["exam_summary_declared"],
            "—" if summary.declared_total_marks is None else str(summary.declared_total_marks),
        ],
        [
            strings["exam_summary_calculated"],
            "—" if summary.calculated_total_marks is None else str(summary.calculated_total_marks),
        ],
        [strings["exam_summary_materials"], str(summary.supporting_material_count)],
        [
            strings["exam_summary_missing_refs"],
            str(summary.missing_or_ambiguous_reference_count),
        ],
    ]
    _simple_table(pdf, ["", ""], rows, language=language, col_widths=[110, 60])


def _source_text(text: str, fallback: str) -> str:
    """Preserve source-document wording exactly as extracted.

    Report language controls interface headings, statuses, summaries, and
    recommendations only. It must never translate, suppress, or duplicate an
    Arabic exam/Course Specification excerpt in an English report (or vice
    versa).
    """
    return text if text.strip() else fallback


def _relationship_table(
    pdf: FPDF,
    entries: tuple[ReportRelationshipEntry, ...],
    language: ReportLanguage,
    *,
    identifier_header: str,
    include_text_column: bool,
) -> None:
    strings = _strings(language)
    if not entries:
        _paragraph(pdf, strings["none"], style="I")
        return
    fallback = strings["text_unavailable"]
    if include_text_column:
        headers = [
            identifier_header,
            strings["col_clo_text"],
            strings["col_linked_questions"],
            strings["col_total_marks"],
            strings["col_coverage_status"],
        ]
        col_widths: list[float] = [22, 68, 40, 25, 35]
        rows = [
            [
                # A CLO's identifier is always a short language-neutral code
                # (e.g. "CLO1"), never source prose, so it is shown as-is.
                entry.identifier,
                _source_text(entry.text, fallback),
                ", ".join(entry.linked_question_labels) or strings["none"],
                str(entry.total_marks),
                _status(entry.coverage_status, language),
            ]
            for entry in entries
        ]
    else:
        headers = [
            identifier_header,
            strings["col_linked_questions"],
            strings["col_total_marks"],
            strings["col_coverage_status"],
        ]
        col_widths = [75, 40, 35, 40]
        rows = [
            [
                (
                    _source_text(entry.identifier, fallback)
                    if entry.identifier_is_source_text
                    # A genuine short code (e.g. a topic code) is
                    # language-neutral and always shown as-is.
                    else entry.identifier
                ),
                ", ".join(entry.linked_question_labels) or strings["none"],
                str(entry.total_marks),
                _status(entry.coverage_status, language),
            ]
            for entry in entries
        ]
    _simple_table(pdf, headers, rows, language=language, col_widths=col_widths)


def _marks_structure_section(pdf: FPDF, content: ReportContent, language: ReportLanguage) -> None:
    strings = _strings(language)
    checks = [f for f in content.findings if f.dimension in _MARKS_STRUCTURE_DIMENSIONS]
    if not checks:
        _paragraph(pdf, strings["none"], style="I")
        return
    for entry in checks:
        _subheading(pdf, requirement_name(entry.requirement_id, entry.requirement_name, language))
        _paragraph(pdf, f"{_status(entry.status, language)}", style="B", size=9)
        _paragraph(pdf, finding_explanation(entry.status, entry.explanation, language), size=10)
        pdf.ln(1)


def _materials_references_section(
    pdf: FPDF, content: ReportContent, language: ReportLanguage
) -> None:
    strings = _strings(language)
    references = content.document_references
    if not references:
        _paragraph(pdf, strings["no_materials"], style="I")
        return
    rows = [
        [
            reference.original_text,
            _structured_label(reference.target_type, language),
            strings.get(reference.resolution_status, reference.resolution_status),
            str(reference.page_number),
        ]
        for reference in references
    ]
    _simple_table(
        pdf,
        [
            strings["col_referenced_item"],
            strings["col_status"],
            strings["col_relationship_result"],
            strings["col_page"],
        ],
        rows,
        language=language,
        col_widths=[70, 30, 60, 25],
    )


def _structured_label(value: str, language: ReportLanguage) -> str:
    if language is not ReportLanguage.ARABIC:
        return value.replace("_", " ").title()
    return {
        "figure": "شكل",
        "table": "جدول",
        "code_block": "مقطع شفرة",
        "question": "سؤال",
    }.get(value, value)


def _key_findings_section(pdf: FPDF, content: ReportContent, language: ReportLanguage) -> None:
    strings = _strings(language)
    for label_key, group in (
        ("strengths", content.strengths),
        ("areas_for_improvement", content.areas_for_improvement),
    ):
        _subheading(pdf, strings[label_key])
        if not group:
            _paragraph(pdf, strings["none"], style="I", size=10)
            continue
        for entry in group:
            _render_concise_finding(pdf, entry, language)
        pdf.ln(1)


def _render_concise_finding(pdf: FPDF, entry: ReportFindingEntry, language: ReportLanguage) -> None:
    strings = _strings(language)
    _paragraph(
        pdf,
        f"{requirement_name(entry.requirement_id, entry.requirement_name, language)} - "
        f"{_status(entry.status, language)}",
        style="B",
        size=10,
    )
    _paragraph(pdf, finding_explanation(entry.status, entry.explanation, language), size=10)
    if entry.recommendations:
        recommendation = entry.recommendations[0]
        title, text = recommendation_text(
            recommendation.recommendation_id,
            recommendation.title,
            recommendation.text,
            language,
        )
        _paragraph(pdf, f"{strings['recommendation']}: {title} - {text}", size=9, style="I")
    pdf.ln(1)


def _missing_evidence_section(pdf: FPDF, content: ReportContent, language: ReportLanguage) -> None:
    strings = _strings(language)
    missing = content.missing_evidence
    if not missing:
        _paragraph(pdf, strings["none"], style="I")
        return
    for entry in missing:
        _render_concise_finding(pdf, entry, language)


_RECOMMENDATION_SECTION_DIMENSIONS: tuple[tuple[str, set[str]], ...] = (
    ("Questions", {"Question Clarity", "Question Completeness"}),
    (
        "Alignment & Coverage",
        {"CLO Alignment", "CLO Coverage", "Topic Alignment", "Topic Coverage"},
    ),
    ("Marks & Structure", {"Marks and Totals", "Numbering and Structure"}),
)
_RECOMMENDATION_SECTION_RULES: dict[str, set[str]] = {
    "Materials & References": {"RULE014", "RULE016", "RULE022"},
}


def _recommendation_section_label(entry: ReportFindingEntry) -> str | None:
    for label, dimensions in _RECOMMENDATION_SECTION_DIMENSIONS:
        if entry.dimension in dimensions:
            return label
    for label, rule_ids in _RECOMMENDATION_SECTION_RULES.items():
        if entry.rule_id in rule_ids:
            return label
    return None


def _recommendations_section(pdf: FPDF, content: ReportContent, language: ReportLanguage) -> None:
    strings = _strings(language)
    grouped: dict[str, list[ReportFindingEntry]] = {}
    seen: set[tuple[str, str]] = set()
    for entry in content.findings:
        if entry.status not in _ATTENTION_STATUSES or not entry.recommendations:
            continue
        label = _recommendation_section_label(entry)
        if label is None:
            continue
        key = (label, entry.requirement_id)
        if key in seen:
            continue
        seen.add(key)
        grouped.setdefault(label, []).append(entry)

    if not grouped:
        _paragraph(pdf, strings["no_recommendations"], style="I")
        return

    for label, entries in grouped.items():
        _subheading(pdf, label)
        for entry in entries:
            recommendation = entry.recommendations[0]
            title, text = recommendation_text(
                recommendation.recommendation_id,
                recommendation.title,
                recommendation.text,
                language,
            )
            _paragraph(pdf, f"{title}: {text}", size=10)
        pdf.ln(1)


def _supporting_evidence_appendix(
    pdf: FPDF, content: ReportContent, language: ReportLanguage
) -> None:
    strings = _strings(language)
    _paragraph(
        pdf,
        strings["appendix_supporting_summary"].format(
            materials=len(content.supporting_materials),
            annotations=len(content.supporting_annotations),
        ),
        size=9,
    )


def _appendix(pdf: FPDF, content: ReportContent, language: ReportLanguage) -> None:
    strings = _strings(language)
    _section_heading(pdf, strings["s14_appendix"], language)
    _paragraph(pdf, strings["appendix_note"], style="I", size=9)
    _paragraph(
        pdf,
        f"{strings['report_id']}: {content.analysis_id} | KB: {content.kb_version}",
        size=8,
        style="I",
    )
    pdf.ln(1)

    _supporting_evidence_appendix(pdf, content, language)

    if not content.findings:
        _paragraph(pdf, strings["no_findings"], style="I")
        return

    rows = [
        [
            entry.requirement_id,
            entry.rule_id,
            _status(entry.status, language),
            governed_label(entry.evaluator_type, language),
            str(len(entry.evidence)),
        ]
        for entry in content.findings
    ]
    _simple_table(
        pdf,
        [
            strings["col_requirement"],
            strings["col_rule"],
            strings["col_status"],
            strings["col_evaluator"],
            strings["col_evidence_count"],
        ],
        rows,
        language=language,
        col_widths=[28, 28, 35, 55, 24],
    )

    provenance_values = sorted(
        {
            " | ".join(
                value
                for value in (
                    entry.ai_provider,
                    entry.ai_model,
                    entry.prompt_template_version,
                    entry.finding_kb_version,
                )
                if value
            )
            for entry in content.findings
            if any(
                (
                    entry.ai_provider,
                    entry.ai_model,
                    entry.prompt_template_version,
                    entry.finding_kb_version,
                )
            )
        }
    )
    pdf.ln(2)
    _subheading(pdf, strings["appendix_provenance"])
    if provenance_values:
        _paragraph(
            pdf,
            strings["appendix_provenance_summary"].format(values="; ".join(provenance_values)),
            size=9,
        )
    else:
        _paragraph(pdf, strings["appendix_no_provenance"], size=9)

    judgment_count = sum(len(entry.item_judgments) for entry in content.findings)
    if judgment_count:
        pdf.ln(2)
        _subheading(pdf, strings["appendix_judgments"])
        _paragraph(
            pdf,
            strings["appendix_judgments_summary"].format(count=judgment_count),
            size=9,
        )


def render_report_pdf(
    content: ReportContent,
    *,
    language: ReportLanguage = ReportLanguage.ENGLISH,
) -> bytes:
    strings = _strings(language)
    pdf = FPDF()
    pdf.set_title(strings["title"])
    pdf.set_creator("Exam Quality Analyzer")
    pdf.set_subject(strings["scope"])
    pdf.set_auto_page_break(auto=True, margin=15)
    _configure_report_fonts(pdf)
    pdf.add_page()

    # Section 1 - Report Header. Deliberately excludes the full analysis
    # UUID, storage identifiers, and capability/provider details from the
    # primary body - see the Technical Traceability Appendix for those.
    _section_heading(pdf, strings["s1_header"], language)
    _paragraph(pdf, strings["title"], style="B", size=16)
    _paragraph(pdf, f"{content.course_code} - {content.course_name}")
    exam_type = (
        ("اختبار نصفي" if content.exam_type.value == "Midterm" else "اختبار نهائي")
        if language is ReportLanguage.ARABIC
        else content.exam_type.value
    )
    _paragraph(pdf, f"{exam_type} {strings['exam']}، {content.term}")
    _paragraph(
        pdf,
        f"{strings['report_id']}: {content.analysis_id} | {strings['generated']}: "
        f"{content.generated_at.isoformat(timespec='seconds')} | "
        f"{strings['language_label']}: "
        f"{('Arabic' if language is ReportLanguage.ARABIC else 'English')}",
        size=9,
    )

    _section_heading(pdf, strings["s2_summary"], language)
    _executive_summary(pdf, content, language)

    _section_heading(pdf, strings["s3_score"], language)
    _paragraph(pdf, _score_line(content, language), style="B", size=13)

    _section_heading(pdf, strings["s4_distribution"], language)
    _status_distribution_table(pdf, content, language)

    _section_heading(pdf, strings["s5_exam_summary"], language)
    _exam_summary_section(pdf, content, language)

    _section_heading(pdf, strings["s6_clo"], language)
    _relationship_table(
        pdf,
        content.clo_entries,
        language,
        identifier_header=strings["col_clo"],
        include_text_column=True,
    )

    _section_heading(pdf, strings["s7_topic"], language)
    _relationship_table(
        pdf,
        content.topic_entries,
        language,
        identifier_header=strings["col_topic"],
        include_text_column=False,
    )

    _section_heading(pdf, strings["s8_marks"], language)
    _marks_structure_section(pdf, content, language)

    _section_heading(pdf, strings["s9_materials"], language)
    _materials_references_section(pdf, content, language)

    _section_heading(pdf, strings["s10_findings"], language)
    _key_findings_section(pdf, content, language)

    _section_heading(pdf, strings["s11_missing"], language)
    _missing_evidence_section(pdf, content, language)

    _section_heading(pdf, strings["s12_recommendations"], language)
    _recommendations_section(pdf, content, language)

    _section_heading(pdf, strings["s13_scope"], language)
    _paragraph(pdf, strings["scope_text"], style="I")

    output = pdf.output()
    return bytes(output)
