from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol

from app.core.domain import AcademicStatus

_STATUS_VALUES: dict[AcademicStatus, Decimal] = {
    AcademicStatus.SATISFIED: Decimal("1.0"),
    AcademicStatus.PARTIALLY_SATISFIED: Decimal("0.5"),
    AcademicStatus.NOT_SATISFIED: Decimal("0.0"),
}


_LOCAL_RELATIONSHIP_RULE_IDS = frozenset({
    "RULE001",  # question-to-CLO mapping
    "RULE002",  # CLO relevance
    "RULE004",  # question-format suitability against a CLO
    "RULE005",  # applicable CLO coverage derived from mapping
    "RULE007",  # question-to-topic alignment
    "RULE008",  # out-of-scope content against topics
    "RULE009",  # applicable topic coverage derived from mapping
})


class ScoreFinding(Protocol):
    rule_id: str
    evaluator_type: str
    status: AcademicStatus


def scoreable_statuses(findings: Iterable[ScoreFinding]) -> tuple[list[AcademicStatus], bool, int]:
    """Return score statuses under the controlled local-pilot contract.

    Local lexical semantic relationships remain visible as faculty-review
    suggestions, but they are not reliable enough to change the numeric score.
    When a local semantic baseline is present, relationship-dependent rules are
    therefore excluded from the denominator. AI-backed and deterministic runs
    preserve the governed status scoring contract unchanged.
    """

    rows = list(findings)
    local_only = any(item.evaluator_type == "local_semantic_baseline" for item in rows)
    if not local_only:
        return [item.status for item in rows], False, 0
    score_rows = [item for item in rows if item.rule_id not in _LOCAL_RELATIONSHIP_RULE_IDS]
    return [item.status for item in score_rows], True, len(rows) - len(score_rows)


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
