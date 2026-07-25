"""Capability coverage manifest for every exam-facing Version 1 KB rule.

This exists to keep AcademicStatus.NOT_VERIFIED evidence-conditioned (per
the M8 correction): a missing evaluation *capability* must never be
represented as a Finding, unconditional or otherwise. Rules the engine
cannot genuinely judge are documented here instead.

M1 adds a second, independent axis:

- ``support_status`` describes the current runtime.
- ``target_evaluation_mode`` and ``design_disposition`` describe the
  design-authorized hybrid target.

Design authorization never claims that a planned evaluator is operational.

System/governance rules (RULE010 and RULE023-RULE030) are enforced by
construction and do not create scored exam-facing Findings. Their IDs are
declared separately in ``SYSTEM_GOVERNANCE_RULE_IDS``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SupportStatus(StrEnum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNSUPPORTED = "unsupported"


class EvaluationMode(StrEnum):
    DETERMINISTIC = "deterministic"
    SEMANTIC_OR_HYBRID = "semantic_or_hybrid"
    NO_AUTHORIZED_METHOD = "no_authorized_method"


class DesignDisposition(StrEnum):
    DESIGN_AUTHORIZED = "design_authorized"
    DEFERRED = "deferred"


@dataclass(frozen=True)
class CapabilityEntry:
    requirement_id: str
    rule_id: str
    requirement_name: str
    support_status: SupportStatus
    target_evaluation_mode: EvaluationMode
    design_disposition: DesignDisposition = DesignDisposition.DESIGN_AUTHORIZED
    # Most current KB rows use the same Requirement_Name and Rule_Name.
    # RULE013 and RULE022 do not, so preserve both official values rather
    # than forcing one field to misrepresent one of the source workbooks.
    rule_name: str | None = None
    implemented_milestone: str | None = None
    reason: str | None = None
    planned_milestone_or_dependency: str | None = None

    @property
    def effective_rule_name(self) -> str:
        return self.rule_name or self.requirement_name

    def __post_init__(self) -> None:
        if self.support_status is not SupportStatus.SUPPORTED and not (
            self.reason and self.reason.strip()
        ):
            raise ValueError(
                f"{self.rule_id}: {self.support_status.value} entries require a non-empty "
                "reason (or, for partially supported entries, a scope description of exactly "
                "which branches are and are not supported)."
            )
        if (
            self.design_disposition is DesignDisposition.DEFERRED
            and self.target_evaluation_mode is not EvaluationMode.NO_AUTHORIZED_METHOD
        ):
            raise ValueError(
                f"{self.rule_id}: deferred entries must use "
                f"{EvaluationMode.NO_AUTHORIZED_METHOD.value!r}."
            )
        if (
            self.target_evaluation_mode is EvaluationMode.NO_AUTHORIZED_METHOD
            and self.design_disposition is not DesignDisposition.DEFERRED
        ):
            raise ValueError(
                f"{self.rule_id}: {EvaluationMode.NO_AUTHORIZED_METHOD.value!r} requires a "
                f"deferred design disposition."
            )


SYSTEM_GOVERNANCE_RULE_IDS: frozenset[str] = frozenset(
    {
        "RULE010",
        "RULE023",
        "RULE024",
        "RULE025",
        "RULE026",
        "RULE027",
        "RULE028",
        "RULE029",
        "RULE030",
    }
)


CAPABILITY_MANIFEST: tuple[CapabilityEntry, ...] = (
    CapabilityEntry(
        requirement_id="REQ001",
        rule_id="RULE001",
        requirement_name="Question-to-CLO Mapping",
        support_status=SupportStatus.SUPPORTED,
        target_evaluation_mode=EvaluationMode.SEMANTIC_OR_HYBRID,
        implemented_milestone="M8",
        planned_milestone_or_dependency="M7 semantic relationship implementation",
    ),
    CapabilityEntry(
        requirement_id="REQ005",
        rule_id="RULE005",
        requirement_name="Applicable CLO Coverage",
        support_status=SupportStatus.SUPPORTED,
        target_evaluation_mode=EvaluationMode.DETERMINISTIC,
        implemented_milestone="M8",
        planned_milestone_or_dependency="M7 confirmed semantic relationship inputs",
    ),
    CapabilityEntry(
        requirement_id="REQ006",
        rule_id="RULE006",
        requirement_name="CLO Coverage Distribution",
        support_status=SupportStatus.PARTIALLY_SUPPORTED,
        target_evaluation_mode=EvaluationMode.DETERMINISTIC,
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
        target_evaluation_mode=EvaluationMode.SEMANTIC_OR_HYBRID,
        implemented_milestone="M8",
        planned_milestone_or_dependency="M7 semantic relationship implementation",
    ),
    CapabilityEntry(
        requirement_id="REQ009",
        rule_id="RULE009",
        requirement_name="Applicable Topic Coverage",
        support_status=SupportStatus.SUPPORTED,
        target_evaluation_mode=EvaluationMode.DETERMINISTIC,
        implemented_milestone="M8",
        planned_milestone_or_dependency="M7 confirmed semantic relationship inputs",
    ),
    CapabilityEntry(
        requirement_id="REQ018",
        rule_id="RULE018",
        requirement_name="Correct Total Marks",
        support_status=SupportStatus.SUPPORTED,
        target_evaluation_mode=EvaluationMode.DETERMINISTIC,
        implemented_milestone="M6",
    ),
    CapabilityEntry(
        requirement_id="REQ019",
        rule_id="RULE019",
        requirement_name="Consistent Numbering",
        support_status=SupportStatus.SUPPORTED,
        target_evaluation_mode=EvaluationMode.DETERMINISTIC,
        implemented_milestone="M6",
    ),
    CapabilityEntry(
        requirement_id="REQ002",
        rule_id="RULE002",
        requirement_name="CLO Relevance",
        support_status=SupportStatus.SUPPORTED,
        target_evaluation_mode=EvaluationMode.SEMANTIC_OR_HYBRID,
        implemented_milestone="Semantic AI/RAG",
        planned_milestone_or_dependency="M6 categorical semantic contract",
    ),
    CapabilityEntry(
        requirement_id="REQ004",
        rule_id="RULE004",
        requirement_name="Question Format Suitability",
        support_status=SupportStatus.SUPPORTED,
        target_evaluation_mode=EvaluationMode.SEMANTIC_OR_HYBRID,
        implemented_milestone="Semantic AI/RAG",
        planned_milestone_or_dependency="M6-M7 categorical and mapping contract",
    ),
    CapabilityEntry(
        requirement_id="REQ008",
        rule_id="RULE008",
        requirement_name="Out-of-Scope Content",
        support_status=SupportStatus.SUPPORTED,
        target_evaluation_mode=EvaluationMode.SEMANTIC_OR_HYBRID,
        implemented_milestone="Semantic AI/RAG",
        planned_milestone_or_dependency="M6-M7 categorical and confirmed-scope contract",
    ),
    CapabilityEntry(
        requirement_id="REQ003",
        rule_id="RULE003",
        requirement_name="Assessment Method Consistency",
        support_status=SupportStatus.UNSUPPORTED,
        target_evaluation_mode=EvaluationMode.SEMANTIC_OR_HYBRID,
        reason=(
            "Retained for Version 1, but no runtime evaluator currently compares explicit exam "
            "metadata with TP-153 assessment-method and assessment-activity evidence. Until that "
            "conservative comparison is implemented, no Finding is released."
        ),
        planned_milestone_or_dependency="M8 semantic/hybrid implementation",
    ),
    CapabilityEntry(
        requirement_id="REQ011",
        rule_id="RULE011",
        requirement_name="Clear Task Statement",
        support_status=SupportStatus.UNSUPPORTED,
        target_evaluation_mode=EvaluationMode.SEMANTIC_OR_HYBRID,
        reason=(
            "Retained for governed semantic implementation in Version 1. The current runtime has "
            "no evaluator for the KB's clear-action and expected-response conditions."
        ),
        planned_milestone_or_dependency="M9 semantic implementation",
    ),
    CapabilityEntry(
        requirement_id="REQ012",
        rule_id="RULE012",
        requirement_name="Unambiguous Wording",
        support_status=SupportStatus.UNSUPPORTED,
        target_evaluation_mode=EvaluationMode.SEMANTIC_OR_HYBRID,
        reason=(
            "Retained for governed semantic implementation in Version 1. The current runtime has "
            "no evaluator for material ambiguity, contradiction, or missing conditions."
        ),
        planned_milestone_or_dependency="M9 semantic implementation",
    ),
    CapabilityEntry(
        requirement_id="REQ013",
        rule_id="RULE013",
        requirement_name="Complete Information",
        rule_name="Complete Question Information",
        support_status=SupportStatus.UNSUPPORTED,
        target_evaluation_mode=EvaluationMode.SEMANTIC_OR_HYBRID,
        reason=(
            "Retained for governed semantic implementation in Version 1. Structured question and "
            "question-specific instruction evidence must be available before evaluation."
        ),
        planned_milestone_or_dependency="M9 semantic implementation",
    ),
    CapabilityEntry(
        requirement_id="REQ014",
        rule_id="RULE014",
        requirement_name="Referenced Material Availability",
        support_status=SupportStatus.UNSUPPORTED,
        target_evaluation_mode=EvaluationMode.DETERMINISTIC,
        reason=(
            "Retained for deterministic structural implementation in Version 1. The runtime does "
            "not yet extract and associate referenced figures, tables, code, or attachments."
        ),
        planned_milestone_or_dependency="V1 structured extraction and retained-rule implementation",
    ),
    CapabilityEntry(
        requirement_id="REQ015",
        rule_id="RULE015",
        requirement_name="Supporting Material Legibility",
        support_status=SupportStatus.UNSUPPORTED,
        target_evaluation_mode=EvaluationMode.NO_AUTHORIZED_METHOD,
        design_disposition=DesignDisposition.DEFERRED,
        reason=(
            "Explicitly deferred from Version 1 findings: the KB defines no approved visual "
            "quality, OCR-confidence, resolution, contrast, size, or usability threshold, and "
            "the project has no governed vision evaluator. Assets may be extracted as evidence, "
            "but their legibility must not be invented."
        ),
    ),
    CapabilityEntry(
        requirement_id="REQ016",
        rule_id="RULE016",
        requirement_name="Supporting Material Association",
        support_status=SupportStatus.UNSUPPORTED,
        target_evaluation_mode=EvaluationMode.DETERMINISTIC,
        reason=(
            "Retained for conservative Version 1 implementation using exact labels, explicit "
            "references, page geometry, and unique associations. The runtime does not yet persist "
            "that structured layout evidence; ambiguous proximity must remain Not Verified."
        ),
        planned_milestone_or_dependency="V1 structured extraction and retained-rule implementation",
    ),
    CapabilityEntry(
        requirement_id="REQ017",
        rule_id="RULE017",
        requirement_name="Visible Marks",
        support_status=SupportStatus.UNSUPPORTED,
        target_evaluation_mode=EvaluationMode.NO_AUTHORIZED_METHOD,
        design_disposition=DesignDisposition.DEFERRED,
        reason=(
            "Explicitly deferred from Version 1 findings: applicability depends on an undefined "
            "institutional visible-marks policy, and the KB does not resolve the overlap between "
            "one incomplete allocation and one missing valid allocation."
        ),
    ),
    CapabilityEntry(
        requirement_id="REQ020",
        rule_id="RULE020",
        requirement_name="Exam Identification",
        support_status=SupportStatus.UNSUPPORTED,
        target_evaluation_mode=EvaluationMode.NO_AUTHORIZED_METHOD,
        design_disposition=DesignDisposition.DEFERRED,
        reason=(
            "Explicitly deferred from Version 1 findings: the KB requires a configurable "
            "institutional field set but does not define which fields are required or which are "
            "essential. Exam metadata may be extracted without inventing that policy."
        ),
    ),
    CapabilityEntry(
        requirement_id="REQ021",
        rule_id="RULE021",
        requirement_name="Complete Instructions",
        support_status=SupportStatus.UNSUPPORTED,
        target_evaluation_mode=EvaluationMode.SEMANTIC_OR_HYBRID,
        reason=(
            "Retained for conservative governed semantic implementation in Version 1. The current "
            "runtime does not evaluate general and question-specific instruction evidence."
        ),
        planned_milestone_or_dependency="M8 semantic/hybrid implementation",
    ),
    CapabilityEntry(
        requirement_id="REQ022",
        rule_id="RULE022",
        requirement_name="Resolvable References",
        rule_name="Resolvable Cross-References",
        support_status=SupportStatus.UNSUPPORTED,
        target_evaluation_mode=EvaluationMode.DETERMINISTIC,
        reason=(
            "Retained for deterministic layout implementation in Version 1. The runtime does not "
            "yet extract explicit relative references and uniquely identifiable layout targets."
        ),
        planned_milestone_or_dependency="V1 structured extraction and retained-rule implementation",
    ),
)
