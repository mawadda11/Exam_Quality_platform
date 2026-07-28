"""Render a governed :class:`ReportContent` snapshot to PDF bytes.

Localization is applied only while rendering. Governed wording and reasoning
remain unchanged in storage and are retained as clearly labelled original
source wording in Arabic reports.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from fpdf import FPDF, XPos, YPos
from fpdf.errors import FPDFException

from app.core.domain import AcademicStatus, ReportLanguage
from app.services.reporting.content import (
    EvidenceCitation,
    ReportContent,
    ReportFindingEntry,
    ReportItemJudgment,
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
    "analysis_id": "Analysis ID",
    "generated": "Generated",
    "kb_version": "KB version",
    "scope": "Scope",
    "scope_text": (
        "This report is limited to the uploaded examination and its populated TP-153 Course "
        "Specification. It does not evaluate student answers or grades, estimate difficulty, "
        "classify Bloom's Taxonomy levels, or issue an accreditation, approval, or rejection "
        "decision. Recommendations are academic support for human review, not institutional "
        "decisions."
    ),
    "overall_score": "Overall Exam Quality Score",
    "based_on": "based on {count} verified applicable {rules}",
    "rule": "rule",
    "rules": "rules",
    "insufficient": "Insufficient Evidence",
    "score_note": (
        "Not Verified and Not Applicable are visible but excluded from the denominator. "
        "Semantic confidence never changes scoring weight."
    ),
    "missing_evidence": "Missing Evidence",
    "missing_note": (
        "Excluded from the score because required evidence was missing, unreadable, or "
        "insufficient - not because the exam failed the requirement."
    ),
    "findings": "Findings",
    "no_findings": "No findings are available for this analysis.",
    "semantic_confidence": "Semantic confidence",
    "confidence_note": "categorical only; not a score, severity, priority, probability, or weight",
    "decision_reasoning": "Governed decision reasoning",
    "confidence_basis": "Confidence basis",
    "item_judgments": "Evidence-linked item judgments",
    "derived_relationship": "Derived advisory relationship",
    "governed_judgment": "Governed item judgment",
    "derived_note": (
        "This relationship is an analysis output, not an official TP-153 mapping, and does "
        "not overwrite source evidence."
    ),
    "source": "Source",
    "source_unavailable": "Source evidence reference unavailable",
    "related_evidence": "Related evidence",
    "related_unresolved": (
        "Related evidence references were retained but could not be resolved "
        "in this report snapshot."
    ),
    "no_target": "No target relationship was asserted.",
    "reasoning": "Concise reasoning",
    "linked_evidence": "Linked evidence",
    "no_evidence": "No evidence was linked to this finding.",
    "kb_references": "Controlled KB references",
    "ai_provenance": "Technical audit details",
    "original_wording": "Original source wording",
    "provider": "Provider",
    "model": "Model",
    "prompt": "Prompt",
    "recommendation": "Recommendation",
    "page": "page",
    "exam_document": "Exam",
}

_AR = {
    "title": "محلل جودة الاختبارات - تقرير التحليل",
    "exam": "اختبار",
    "analysis_id": "معرّف التحليل",
    "generated": "تاريخ الإنشاء",
    "kb_version": "إصدار قاعدة المعرفة",
    "scope": "نطاق التقرير",
    "scope_text": (
        "يقتصر هذا التقرير على الاختبار المرفوع وتوصيف المقرر TP-153 المعبأ. ولا يقيّم "
        "إجابات الطلبة أو درجاتهم، ولا يقدّر صعوبة الاختبار، ولا يصنف مستويات بلوم، ولا "
        "يصدر قرار اعتماد أو قبول أو رفض. التوصيات دعم أكاديمي للمراجعة البشرية وليست "
        "قرارات مؤسسية."
    ),
    "overall_score": "الدرجة الإجمالية لجودة الاختبار",
    "based_on": "استنادًا إلى {count} قاعدة منطبقة تم التحقق منها",
    "rule": "قاعدة",
    "rules": "قواعد",
    "insufficient": "أدلة غير كافية",
    "score_note": (
        "تظهر حالتا غير متحقق وغير منطبق في التقرير، لكنهما مستبعدتان من مقام الدرجة. "
        "ولا يغيّر مستوى الثقة الدلالية وزن احتساب الدرجة."
    ),
    "missing_evidence": "الأدلة المفقودة",
    "missing_note": (
        "استُبعدت من الدرجة لأن الأدلة المطلوبة كانت مفقودة أو غير مقروءة أو غير كافية، "
        "وليس لأن الاختبار أخفق في المتطلب."
    ),
    "findings": "نتائج التقييم",
    "no_findings": "لا توجد نتائج تقييم متاحة لهذا التحليل.",
    "semantic_confidence": "الثقة الدلالية",
    "confidence_note": "تصنيف وصفي فقط، وليست درجة أو شدة أو أولوية أو احتمالًا أو وزنًا",
    "decision_reasoning": "مبررات القرار المحكوم",
    "confidence_basis": "أساس الثقة",
    "item_judgments": "أحكام العناصر المرتبطة بالأدلة",
    "derived_relationship": "علاقة استرشادية مستنتجة",
    "governed_judgment": "حكم عنصر محكوم",
    "derived_note": ("هذه العلاقة ناتج تحليلي وليست ربطًا رسميًا في TP-153، ولا تستبدل أدلة المصدر."),
    "source": "المصدر",
    "source_unavailable": "مرجع دليل المصدر غير متاح",
    "related_evidence": "الدليل المرتبط",
    "related_unresolved": "حُفظت مراجع الأدلة المرتبطة، لكن تعذر حلها في لقطة التقرير.",
    "no_target": "لم تُثبت علاقة مع هدف.",
    "reasoning": "التعليل المختصر",
    "linked_evidence": "الأدلة المرتبطة",
    "no_evidence": "لم يُربط أي دليل بهذه النتيجة.",
    "kb_references": "مراجع قاعدة المعرفة المحكومة",
    "ai_provenance": "تفاصيل التدقيق التقني",
    "original_wording": "النص المصدري الأصلي",
    "provider": "المزوّد",
    "model": "النموذج",
    "prompt": "قالب التعليمات",
    "recommendation": "التوصية",
    "page": "صفحة",
    "exam_document": "الاختبار",
}

_STATUS_AR: dict[AcademicStatus, str] = {
    AcademicStatus.SATISFIED: "مستوفى",
    AcademicStatus.PARTIALLY_SATISFIED: "مستوفى جزئيًا",
    AcademicStatus.NOT_SATISFIED: "غير مستوفى",
    AcademicStatus.NOT_VERIFIED: "غير متحقق",
    AcademicStatus.NOT_APPLICABLE: "غير منطبق",
}


def _strings(language: ReportLanguage) -> dict[str, str]:
    return _AR if language is ReportLanguage.ARABIC else _EN


def _status(status: AcademicStatus, language: ReportLanguage) -> str:
    return _STATUS_AR[status] if language is ReportLanguage.ARABIC else status.value


def _confidence(value: str, language: ReportLanguage) -> str:
    if language is not ReportLanguage.ARABIC:
        return value
    return {"High": "مرتفع", "Medium": "متوسط", "Low": "منخفض"}.get(value, value)


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


def _heading(pdf: FPDF, text: str) -> None:
    _paragraph(pdf, text, style="B", size=13)


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


def _citation_line(item: EvidenceCitation, language: ReportLanguage) -> str:
    strings = _strings(language)
    document = strings["exam_document"] if item.source_document.value == "exam" else "TP-153"
    evidence_type = item.evidence_type
    if language is ReportLanguage.ARABIC:
        evidence_type = {
            "question_text": "نص السؤال",
            "marks": "الدرجات",
            "declared_total": "المجموع المعلن",
            "instructions": "التعليمات",
            "clo": "مرجع ناتج التعلم",
            "topic": "مرجع موضوع المقرر",
            "assessment_record": "سجل التقييم",
            "missing_section": "قسم مفقود",
            "exam_metadata": "بيانات الاختبار",
        }.get(item.evidence_type, "دليل مرتبط")
    return (
        f"{item.item_reference} | {document} {strings['page']} {item.page_number} | {evidence_type}"
    )


def _render_item_judgment(
    pdf: FPDF,
    entry: ReportFindingEntry,
    judgment: ReportItemJudgment,
    language: ReportLanguage,
) -> None:
    strings = _strings(language)
    relationship = entry.rule_id in {"RULE001", "RULE007"} and judgment.is_derived_relationship
    label = strings["derived_relationship"] if relationship else strings["governed_judgment"]
    _paragraph(pdf, f"{label} - {_status(judgment.status, language)}", style="B", size=9)
    if relationship:
        _paragraph(pdf, strings["derived_note"], style="I", size=8)

    if judgment.source_evidence is not None:
        _paragraph(
            pdf,
            f"{strings['source']}: {_citation_line(judgment.source_evidence, language)}",
            size=9,
        )
    else:
        _paragraph(
            pdf,
            f"{strings['source_unavailable']}: {judgment.source_evidence_id}",
            style="I",
            size=9,
        )

    if judgment.target_evidence:
        for target in judgment.target_evidence:
            _paragraph(
                pdf,
                f"{strings['related_evidence']}: {_citation_line(target, language)}",
                size=9,
            )
    elif judgment.target_evidence_ids:
        _paragraph(pdf, strings["related_unresolved"], style="I", size=9)
    else:
        _paragraph(pdf, strings["no_target"], style="I", size=9)

    if language is ReportLanguage.ARABIC:
        _paragraph(
            pdf,
            f"{strings['reasoning']}: تدعم الأدلة المرتبطة الحكم التفصيلي المعروض أعلاه.",
            size=9,
        )
        _paragraph(
            pdf,
            f"{strings['original_wording']}: {judgment.reasoning}",
            style="I",
            size=8,
        )
    else:
        _paragraph(pdf, f"{strings['reasoning']}: {judgment.reasoning}", size=9)


def _render_finding(
    pdf: FPDF,
    entry: ReportFindingEntry,
    language: ReportLanguage,
) -> None:
    strings = _strings(language)
    _paragraph(
        pdf,
        f"{requirement_name(entry.requirement_id, entry.requirement_name, language)} - "
        f"{_status(entry.status, language)}",
        style="B",
        size=11,
    )
    _paragraph(
        pdf,
        f"{governed_label(entry.dimension, language)} | "
        f"{governed_label(entry.source_type, language)} "
        f"({governed_label(entry.officiality, language)}) | "
        f"{entry.requirement_id} / {entry.rule_id}",
        style="I",
        size=9,
    )
    _paragraph(pdf, finding_explanation(entry.status, entry.explanation, language))
    if language is ReportLanguage.ARABIC:
        _paragraph(
            pdf,
            f"{strings['original_wording']}: {entry.explanation}",
            style="I",
            size=8,
        )

    if entry.confidence_level is not None:
        _paragraph(
            pdf,
            f"{strings['semantic_confidence']}: "
            f"{_confidence(entry.confidence_level.value, language)} "
            f"({strings['confidence_note']})",
            style="B",
            size=9,
        )
    if entry.evaluation_reasoning:
        _paragraph(
            pdf,
            f"{strings['decision_reasoning']}: "
            + (
                "يستند القرار إلى المتطلب المحكوم والأدلة المرتبطة."
                if language is ReportLanguage.ARABIC
                else entry.evaluation_reasoning
            ),
            size=9,
        )
        if language is ReportLanguage.ARABIC:
            _paragraph(
                pdf,
                f"{strings['original_wording']}: {entry.evaluation_reasoning}",
                style="I",
                size=8,
            )
    for basis in entry.confidence_basis:
        presented_basis = (
            "يعكس مستوى الثقة جودة الأدلة المرتبطة واكتمالها."
            if language is ReportLanguage.ARABIC
            else basis
        )
        _paragraph(pdf, f"{strings['confidence_basis']}: {presented_basis}", size=9)
        if language is ReportLanguage.ARABIC:
            _paragraph(pdf, f"{strings['original_wording']}: {basis}", style="I", size=8)

    if entry.item_judgments:
        _paragraph(
            pdf,
            f"{strings['item_judgments']} ({len(entry.item_judgments)}):",
            style="B",
            size=9,
        )
        for judgment in entry.item_judgments:
            _render_item_judgment(pdf, entry, judgment, language)

    if entry.evidence:
        _paragraph(
            pdf,
            f"{strings['linked_evidence']} ({len(entry.evidence)}):",
            style="B",
            size=9,
        )
        for item in entry.evidence:
            _paragraph(pdf, f"- {_citation_line(item, language)}", size=9)
    else:
        _paragraph(pdf, strings["no_evidence"], style="I", size=9)

    if entry.retrieved_knowledge_ids:
        _paragraph(
            pdf,
            f"{strings['kb_references']}: " + ", ".join(entry.retrieved_knowledge_ids),
            size=9,
        )

    provenance = [
        value
        for value in (
            f"{strings['provider']}: {entry.ai_provider}" if entry.ai_provider else None,
            f"{strings['model']}: {entry.ai_model}" if entry.ai_model else None,
            f"{strings['prompt']}: {entry.prompt_template_version}"
            if entry.prompt_template_version
            else None,
            f"KB: {entry.finding_kb_version}" if entry.finding_kb_version else None,
        )
        if value is not None
    ]
    if provenance:
        _paragraph(pdf, f"{strings['ai_provenance']}: " + " | ".join(provenance), style="I", size=8)

    for recommendation in entry.recommendations:
        title, text = recommendation_text(
            recommendation.recommendation_id,
            recommendation.title,
            recommendation.text,
            language,
        )
        _paragraph(pdf, f"{strings['recommendation']}: {title}", style="B", size=9)
        _paragraph(pdf, text, size=9)
        if language is ReportLanguage.ARABIC:
            _paragraph(
                pdf,
                f"{strings['original_wording']}: {recommendation.title}. {recommendation.text}",
                style="I",
                size=8,
            )

    pdf.ln(3)


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
        f"{strings['analysis_id']}: {content.analysis_id} | {strings['generated']}: "
        f"{content.generated_at.isoformat(timespec='seconds')} | {strings['kb_version']}: "
        f"{content.kb_version}",
        size=9,
    )
    pdf.ln(2)

    _heading(pdf, strings["scope"])
    _paragraph(pdf, strings["scope_text"], style="I")
    pdf.ln(2)

    _heading(pdf, strings["overall_score"])
    _paragraph(pdf, _score_line(content, language))
    counts = (
        f"{_status(AcademicStatus.SATISFIED, language)}: {content.satisfied_count} | "
        f"{_status(AcademicStatus.PARTIALLY_SATISFIED, language)}: "
        f"{content.partially_satisfied_count} | "
        f"{_status(AcademicStatus.NOT_SATISFIED, language)}: {content.not_satisfied_count} | "
        f"{_status(AcademicStatus.NOT_VERIFIED, language)}: {content.not_verified_count} | "
        f"{_status(AcademicStatus.NOT_APPLICABLE, language)}: {content.not_applicable_count}"
    )
    _paragraph(pdf, counts, size=10)
    _paragraph(pdf, strings["score_note"], style="I", size=9)
    pdf.ln(2)

    missing = content.missing_evidence
    if missing:
        _heading(pdf, f"{strings['missing_evidence']} ({len(missing)})")
        _paragraph(pdf, strings["missing_note"], style="I")
        for entry in missing:
            _subheading(
                pdf,
                requirement_name(entry.requirement_id, entry.requirement_name, language),
            )
            _paragraph(
                pdf,
                finding_explanation(entry.status, entry.explanation, language),
                size=10,
            )
        pdf.ln(2)

    _heading(pdf, f"{strings['findings']} ({len(content.findings)})")
    if not content.findings:
        _paragraph(pdf, strings["no_findings"], style="I")
    for entry in content.findings:
        _render_finding(pdf, entry, language)

    output = pdf.output()
    return bytes(output)
