"""Capability coverage manifest: a small, source-controlled, versioned
record of which official KB rules the combined deterministic and approved
semantic rule engine evaluates at runtime, and why partial branches do not
produce Findings.

This exists to keep AcademicStatus.NOT_VERIFIED evidence-conditioned (per
the M8 correction): a missing evaluation *capability* must never be
represented as a Finding, unconditional or otherwise. Rules the engine
cannot genuinely judge are documented here instead - not persisted per
analysis, not exposed via a new API endpoint, just an importable Python
structure other code (and, later, M10's denominator/excluded-count
reporting) can read.

Only rules the runtime system actually evaluates are listed here. The
semantic/RAG continuation adds its explicitly approved RULE002/RULE004/
RULE008 scope; other illustrative future gaps remain test-only entries.
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
        support_status=SupportStatus.SUPPORTED,
        implemented_milestone="Semantic AI/RAG",
    ),
    CapabilityEntry(
        requirement_id="REQ004",
        rule_id="RULE004",
        requirement_name="Question Format Suitability",
        support_status=SupportStatus.SUPPORTED,
        implemented_milestone="Semantic AI/RAG",
    ),
    CapabilityEntry(
        requirement_id="REQ008",
        rule_id="RULE008",
        requirement_name="Out-of-Scope Content",
        support_status=SupportStatus.SUPPORTED,
        implemented_milestone="Semantic AI/RAG",
    ),
)
