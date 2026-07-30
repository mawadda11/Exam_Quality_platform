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
        == "اربط السؤال بناتج تعلم"
    )
