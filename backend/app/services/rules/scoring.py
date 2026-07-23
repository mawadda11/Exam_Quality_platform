from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.core.domain import AcademicStatus

_STATUS_VALUES: dict[AcademicStatus, Decimal] = {
    AcademicStatus.SATISFIED: Decimal("1.0"),
    AcademicStatus.PARTIALLY_SATISFIED: Decimal("0.5"),
    AcademicStatus.NOT_SATISFIED: Decimal("0.0"),
}


@dataclass(frozen=True)
class ScoreResult:
    score: Decimal | None
    denominator: int
    label: str | None = None


def calculate_overall_score(statuses: list[AcademicStatus]) -> ScoreResult:
    scored = [_STATUS_VALUES[status] for status in statuses if status in _STATUS_VALUES]
    if not scored:
        return ScoreResult(score=None, denominator=0, label="Insufficient Evidence")

    raw = sum(scored, start=Decimal("0")) / Decimal(len(scored)) * Decimal("100")
    score = raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return ScoreResult(score=score, denominator=len(scored))


def count_statuses(statuses: Sequence[AcademicStatus]) -> dict[AcademicStatus, int]:
    """Per SCORE023/SCORE024 (docs/SCORING_POLICY.md "Reporting" section):
    the report must show counts of every status, with Not Verified/Not
    Applicable counted separately rather than only folded into the
    excluded-from-scoring denominator math. Always returns all five members
    (zero-filled), so a UI can render a stable five-column layout."""
    counts = dict.fromkeys(AcademicStatus, 0)
    for status in statuses:
        counts[status] += 1
    return counts
