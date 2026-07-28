from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from helpers import auth_header

from app.core.domain import AcademicStatus
from app.models.finding import Finding
from app.schemas.rule_coverage import RuleRuntimeDisposition
from app.services.rules.capability_manifest import CAPABILITY_MANIFEST, SupportStatus
from app.services.rules.coverage_audit import build_rule_coverage_audit
from app.services.rules.versioning import (
    BATCH4_CAPABILITY_VERSION,
    LEGACY_CAPABILITY_VERSION,
)

ANALYSIS_PAYLOAD = {
    "course": {"code": "CPIT-450", "name": "Software Engineering"},
    "exam_type": "Midterm",
    "term": "2026 Spring",
}


def _finding(analysis_id: uuid.UUID, rule_id: str, requirement_id: str) -> Finding:
    return Finding(
        analysis_id=analysis_id,
        requirement_id=requirement_id,
        rule_id=rule_id,
        status=AcademicStatus.SATISFIED,
        explanation="Governed test finding.",
        confidence=1.0,
        evaluator_type="test_evaluator",
    )


def test_coverage_audit_accounts_for_every_exam_facing_rule() -> None:
    analysis_id = uuid.uuid4()
    findings = [
        _finding(analysis_id, item.rule_id, item.requirement_id)
        for item in CAPABILITY_MANIFEST
        if item.support_status is SupportStatus.SUPPORTED
    ]

    audit = build_rule_coverage_audit(
        analysis_id,
        findings,
        capability_version=BATCH4_CAPABILITY_VERSION,
    )

    assert audit.total_rules == 21
    assert len(audit.entries) == audit.total_rules
    assert len({item.rule_id for item in audit.entries}) == audit.total_rules
    assert audit.evaluated_rules == 17
    assert audit.conditional_capability_gap_rules == 1
    assert audit.unsupported_rules == 3
    assert audit.not_run_rules == 0
    assert audit.runtime_integrity_ok is True

    rule006 = next(item for item in audit.entries if item.rule_id == "RULE006")
    assert rule006.runtime_disposition is RuleRuntimeDisposition.CONDITIONAL_CAPABILITY_GAP
    assert rule006.finding_status is None
    assert rule006.reason

    rule015 = next(item for item in audit.entries if item.rule_id == "RULE015")
    assert rule015.runtime_disposition is RuleRuntimeDisposition.UNSUPPORTED
    assert rule015.design_disposition == "deferred"
    assert rule015.reason


def test_supported_rule_missing_at_runtime_is_not_disguised_as_not_verified() -> None:
    analysis_id = uuid.uuid4()
    audit = build_rule_coverage_audit(
        analysis_id,
        [],
        capability_version=BATCH4_CAPABILITY_VERSION,
    )

    rule001 = next(item for item in audit.entries if item.rule_id == "RULE001")
    assert rule001.runtime_disposition is RuleRuntimeDisposition.NOT_RUN
    assert rule001.finding_status is None
    assert "runtime coverage gap" in (rule001.reason or "")
    assert audit.not_run_rules == 17
    assert audit.runtime_integrity_ok is False


def test_rule_coverage_endpoint_is_owned_and_exposes_complete_accounting(
    client: TestClient,
) -> None:
    owner = "coverage-owner@kau.edu.sa"
    created = client.post("/api/v1/analyses", json=ANALYSIS_PAYLOAD, headers=auth_header(owner))
    assert created.status_code == 201
    analysis_id = created.json()["id"]

    response = client.get(
        f"/api/v1/analyses/{analysis_id}/rule-coverage",
        headers=auth_header(owner),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["analysis_id"] == analysis_id
    assert body["scope"] == "exam_facing_rules"
    assert body["total_rules"] == 21
    assert body["evaluated_rules"] == 0
    assert body["not_run_rules"] == 17
    assert body["conditional_capability_gap_rules"] == 1
    assert body["unsupported_rules"] == 3
    assert body["runtime_integrity_ok"] is False
    assert len(body["entries"]) == 21

    denied = client.get(
        f"/api/v1/analyses/{analysis_id}/rule-coverage",
        headers=auth_header("coverage-intruder@kau.edu.sa"),
    )
    assert denied.status_code == 404


def test_historical_capability_version_keeps_batch4_rules_unsupported() -> None:
    audit = build_rule_coverage_audit(
        uuid.uuid4(),
        [],
        capability_version=LEGACY_CAPABILITY_VERSION,
    )
    batch4_entries = [
        entry for entry in audit.entries if entry.rule_id in {"RULE014", "RULE016", "RULE022"}
    ]

    assert all(
        entry.runtime_disposition is RuleRuntimeDisposition.UNSUPPORTED for entry in batch4_entries
    )
    assert all(LEGACY_CAPABILITY_VERSION in (entry.reason or "") for entry in batch4_entries)
