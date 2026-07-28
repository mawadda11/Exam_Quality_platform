"""Account for every governed exam-facing rule without hiding system gaps.

Academic findings use the exact five KB statuses.  This service is a separate
implementation-coverage audit: unsupported capability and a supported rule
that failed to run are operational facts, not academic ``Not Verified``
results.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from app.models.finding import Finding
from app.schemas.rule_coverage import (
    RuleCoverageAuditResponse,
    RuleCoverageEntryResponse,
    RuleRuntimeDisposition,
)
from app.services.rules.capability_manifest import CAPABILITY_MANIFEST, SupportStatus
from app.services.rules.versioning import LEGACY_CAPABILITY_VERSION

_BATCH4_RULE_IDS = {"RULE014", "RULE016", "RULE022"}


def build_rule_coverage_audit(
    analysis_id: UUID,
    findings: Sequence[Finding],
    *,
    capability_version: str = LEGACY_CAPABILITY_VERSION,
) -> RuleCoverageAuditResponse:
    findings_by_rule = {finding.rule_id: finding for finding in findings}
    if len(findings_by_rule) != len(findings):
        raise ValueError("An analysis contains duplicate persisted rule findings.")

    entries: list[RuleCoverageEntryResponse] = []
    for capability in CAPABILITY_MANIFEST:
        finding = findings_by_rule.get(capability.rule_id)
        if finding is not None:
            disposition = RuleRuntimeDisposition.EVALUATED
            reason = capability.reason
        elif (
            capability_version == LEGACY_CAPABILITY_VERSION
            and capability.rule_id in _BATCH4_RULE_IDS
        ):
            disposition = RuleRuntimeDisposition.UNSUPPORTED
            reason = (
                f"{capability.rule_id} was not part of the stored {capability_version} "
                "capability set used for this analysis."
            )
        elif capability.support_status is SupportStatus.UNSUPPORTED:
            disposition = RuleRuntimeDisposition.UNSUPPORTED
            reason = capability.reason
        elif capability.support_status is SupportStatus.PARTIALLY_SUPPORTED:
            disposition = RuleRuntimeDisposition.CONDITIONAL_CAPABILITY_GAP
            reason = capability.reason
        else:
            disposition = RuleRuntimeDisposition.NOT_RUN
            reason = (
                "No Finding was persisted although the capability manifest declares this rule "
                "supported. This is a runtime coverage gap, not an academic Not Verified result."
            )

        entries.append(
            RuleCoverageEntryResponse(
                requirement_id=capability.requirement_id,
                rule_id=capability.rule_id,
                requirement_name=capability.requirement_name,
                rule_name=capability.effective_rule_name,
                support_status=capability.support_status,
                evaluation_mode=capability.target_evaluation_mode,
                design_disposition=capability.design_disposition,
                runtime_disposition=disposition,
                finding_status=finding.status if finding is not None else None,
                evaluator_type=finding.evaluator_type if finding is not None else None,
                implemented_milestone=capability.implemented_milestone,
                reason=reason,
                planned_milestone_or_dependency=(capability.planned_milestone_or_dependency),
            )
        )

    evaluated = sum(
        item.runtime_disposition is RuleRuntimeDisposition.EVALUATED for item in entries
    )
    conditional = sum(
        item.runtime_disposition is RuleRuntimeDisposition.CONDITIONAL_CAPABILITY_GAP
        for item in entries
    )
    unsupported = sum(
        item.runtime_disposition is RuleRuntimeDisposition.UNSUPPORTED for item in entries
    )
    not_run = sum(item.runtime_disposition is RuleRuntimeDisposition.NOT_RUN for item in entries)

    return RuleCoverageAuditResponse(
        analysis_id=analysis_id,
        capability_version=capability_version,
        total_rules=len(entries),
        evaluated_rules=evaluated,
        conditional_capability_gap_rules=conditional,
        unsupported_rules=unsupported,
        not_run_rules=not_run,
        runtime_integrity_ok=not_run == 0,
        entries=entries,
    )
