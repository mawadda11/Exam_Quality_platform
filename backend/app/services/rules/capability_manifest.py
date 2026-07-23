"""Capability coverage manifest: a small, source-controlled, versioned
record of which official KB rules this system's deterministic rule engine
actually evaluates at runtime, and why the rest don't produce Findings.

This exists to keep AcademicStatus.NOT_VERIFIED evidence-conditioned (per
the M8 correction): a missing evaluation *capability* must never be
represented as a Finding, unconditional or otherwise. Rules the engine
cannot genuinely judge are documented here instead - not persisted per
analysis, not exposed via a new API endpoint, just an importable Python
structure other code (and, later, M10's denominator/excluded-count
reporting) can read.

Only rules the runtime system has actually touched (M6 and M8) are listed
here. Do not add illustrative or future (e.g. M9) entries to
CAPABILITY_MANIFEST - the schema's ability to represent other categories of
gap (language-quality, OCR/vision, institutional-configuration, meta-rules)
is proven with test-only CapabilityEntry instances, not production rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SupportStatus(StrEnum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class CapabilityEntry:
    requirement_id: str
    rule_id: str
    requirement_name: str
    support_status: SupportStatus
    implemented_milestone: str | None = None
    reason: str | None = None
    planned_milestone_or_dependency: str | None = None

    def __post_init__(self) -> None:
        if self.support_status is not SupportStatus.SUPPORTED and not (
            self.reason and self.reason.strip()
        ):
            raise ValueError(
                f"{self.rule_id}: {self.support_status.value} entries require a non-empty "
                "reason (or, for partially supported entries, a scope description of exactly "
                "which branches are and are not supported)."
            )


CAPABILITY_MANIFEST: tuple[CapabilityEntry, ...] = (
    CapabilityEntry(
        requirement_id="REQ001",
        rule_id="RULE001",
        requirement_name="Question-to-CLO Mapping",
        support_status=SupportStatus.SUPPORTED,
        implemented_milestone="M8",
    ),
    CapabilityEntry(
        requirement_id="REQ005",
        rule_id="RULE005",
        requirement_name="Applicable CLO Coverage",
        support_status=SupportStatus.SUPPORTED,
        implemented_milestone="M8",
    ),
    CapabilityEntry(
        requirement_id="REQ006",
        rule_id="RULE006",
        requirement_name="CLO Coverage Distribution",
        support_status=SupportStatus.PARTIALLY_SUPPORTED,
        implemented_milestone="M8",
        reason=(
            "Supported: zero applicable CLOs (Finding = Not Verified - required source data "
            "unavailable) and exactly one applicable CLO (Finding = Not Applicable, per the "
            "official KB condition 'Only one CLO is applicable.'). Unsupported: two or more "
            "applicable CLOs - the KB's Satisfied/Partially Satisfied split requires judging "
            "the degree of evidence concentration, and the KB defines no numeric threshold "
            "for that judgment. No Finding is produced for this case; none is invented."
        ),
    ),
    CapabilityEntry(
        requirement_id="REQ007",
        rule_id="RULE007",
        requirement_name="Question-to-Topic Alignment",
        support_status=SupportStatus.SUPPORTED,
        implemented_milestone="M8",
    ),
    CapabilityEntry(
        requirement_id="REQ009",
        rule_id="RULE009",
        requirement_name="Applicable Topic Coverage",
        support_status=SupportStatus.SUPPORTED,
        implemented_milestone="M8",
    ),
    CapabilityEntry(
        requirement_id="REQ018",
        rule_id="RULE018",
        requirement_name="Correct Total Marks",
        support_status=SupportStatus.SUPPORTED,
        implemented_milestone="M6",
    ),
    CapabilityEntry(
        requirement_id="REQ019",
        rule_id="RULE019",
        requirement_name="Consistent Numbering",
        support_status=SupportStatus.SUPPORTED,
        implemented_milestone="M6",
    ),
    CapabilityEntry(
        requirement_id="REQ002",
        rule_id="RULE002",
        requirement_name="CLO Relevance",
        support_status=SupportStatus.UNSUPPORTED,
        reason=(
            "Requires judging whether an existing question-to-CLO mapping's content is "
            "genuinely relevant (a KB-classified Semantic Rule). Citation presence - the only "
            "deterministic signal available - answers a different question ('was a mapping "
            "declared') than this one ('is the mapping good'). No Finding is produced rather "
            "than inventing a relevance heuristic."
        ),
    ),
    CapabilityEntry(
        requirement_id="REQ008",
        rule_id="RULE008",
        requirement_name="Out-of-Scope Content",
        support_status=SupportStatus.UNSUPPORTED,
        reason=(
            "Requires judging whether question content substantively falls outside "
            "documented topics (a KB-classified Semantic Rule). Absence of a topic citation "
            "does not deterministically prove content is out of scope. No Finding is produced "
            "rather than inventing a scope-boundary heuristic."
        ),
    ),
)
