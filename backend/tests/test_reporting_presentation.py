from app.core.domain import AcademicStatus, ReportLanguage
from app.services.reporting.presentation import (
    finding_explanation,
    recommendation_text,
    requirement_name,
)


def test_arabic_report_presentation_uses_stable_ids_and_preserves_english_path() -> None:
    assert (
        requirement_name("REQ001", "Question-to-CLO Mapping", ReportLanguage.ARABIC)
        == "ربط السؤال بناتج التعلم للمقرر"
    )
    assert (
        requirement_name("REQ001", "Question-to-CLO Mapping", ReportLanguage.ENGLISH)
        == "Question-to-CLO Mapping"
    )
    assert "تعذر التحقق" in finding_explanation(
        AcademicStatus.NOT_VERIFIED,
        "Original governed explanation.",
        ReportLanguage.ARABIC,
    )
    assert (
        finding_explanation(
            AcademicStatus.NOT_VERIFIED,
            "Original governed explanation.",
            ReportLanguage.ENGLISH,
        )
        == "Original governed explanation."
    )
    assert (
        recommendation_text(
            "REC001",
            "Map the Question to a CLO",
            "Original recommendation.",
            ReportLanguage.ARABIC,
        )[0]
        == "راجع علاقة السؤال بناتج التعلم"
    )
    english = recommendation_text(
        "REC001",
        "Map the Question to a CLO",
        "Original recommendation.",
        ReportLanguage.ENGLISH,
    )
    assert english[0] == "Review the question-to-CLO relationship"
    assert "otherwise leave it unassigned" in english[1]

    unsupported_english = recommendation_text(
        "REC007",
        "Align the Question with Course Topics",
        "Remove the unsupported part.",
        ReportLanguage.ENGLISH,
    )
    assert unsupported_english[1] == (
        "Verify the approved course specification. If the topic is officially included but "
        "missing from the uploaded specification, update the specification. Otherwise, review "
        "or replace the question."
    )
    unsupported_arabic = recommendation_text(
        "REC007",
        "Align the Question with Course Topics",
        "Remove the unsupported part.",
        ReportLanguage.ARABIC,
    )
    assert unsupported_arabic[1] == (
        "تحقّق من توصيف المقرر المعتمد. إذا كان الموضوع معتمدًا لكنه غير مدرج في الملف "
        "المرفوع، فحدّث التوصيف؛ وإلا فراجع السؤال أو استبدله."
    )
