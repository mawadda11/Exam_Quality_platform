from decimal import Decimal

from app.core.domain import AcademicStatus
from app.services.rules.scoring import calculate_overall_score


def test_score_excludes_not_verified_and_not_applicable() -> None:
    result = calculate_overall_score(
        [
            AcademicStatus.SATISFIED,
            AcademicStatus.PARTIALLY_SATISFIED,
            AcademicStatus.NOT_SATISFIED,
            AcademicStatus.NOT_VERIFIED,
            AcademicStatus.NOT_APPLICABLE,
        ]
    )
    assert result.score == Decimal("50.00")
    assert result.denominator == 3


def test_score_returns_insufficient_evidence_for_zero_denominator() -> None:
    result = calculate_overall_score([AcademicStatus.NOT_VERIFIED, AcademicStatus.NOT_APPLICABLE])
    assert result.score is None
    assert result.denominator == 0
    assert result.label == "Insufficient Evidence"
