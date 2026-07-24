from __future__ import annotations

import io
import time
from pathlib import Path

import pytest
from clo_topic_pdf_fixtures import (
    build_exam_citing_all_clos_and_topics_pdf,
    build_exam_citing_hyphenated_and_bracketed_variants_pdf,
    build_exam_citing_no_clos_or_topics_pdf,
    build_exam_citing_some_clos_and_topics_pdf,
    build_exam_citing_two_topics_pdf,
)
from fastapi.testclient import TestClient
from helpers import auth_header
from tp153_pdf_fixtures import (
    build_complete_tp153_pdf,
    build_incomplete_assessment_tp153_pdf,
    build_missing_clo_section_tp153_pdf,
)

import app.services.processing.stages as stages
from app.core.domain import AcademicStatus
from app.services.ai.fake_provider import FakeAiProvider
from app.services.knowledge_base.runtime import SemanticRuntime, load_kb_snapshot
from app.services.knowledge_base.vector_store import InMemoryVectorStore
from app.services.rules.scoring import calculate_overall_score

REPO_ROOT = Path(__file__).resolve().parents[2]
KB_SOURCE = REPO_ROOT / "knowledge_base" / "source"

ANALYSIS_PAYLOAD = {
    "course": {"code": "CPIT-450", "name": "Software Engineering"},
    "exam_type": "Midterm",
    "term": "2026 Spring",
}

# The deterministic M8 rules and the three approved semantic rules are
# unconditional runtime evaluations. RULE006 remains intentionally partial
# and only joins them for zero or one applicable CLO.
DETERMINISTIC_RULE_IDS = {"RULE001", "RULE005", "RULE007", "RULE009", "RULE018", "RULE019"}
SEMANTIC_RULE_IDS = {"RULE002", "RULE004", "RULE008"}
UNCONDITIONAL_RULE_IDS = DETERMINISTIC_RULE_IDS | SEMANTIC_RULE_IDS


def _create_analysis(client: TestClient, email: str) -> str:
    response = client.post("/api/v1/analyses", json=ANALYSIS_PAYLOAD, headers=auth_header(email))
    assert response.status_code == 201
    analysis_id: str = response.json()["id"]
    return analysis_id


def _upload(
    client: TestClient, analysis_id: str, email: str, file_type: str, filename: str, content: bytes
) -> None:
    response = client.post(
        f"/api/v1/analyses/{analysis_id}/files",
        headers=auth_header(email),
        data={"file_type": file_type},
        files={"file": (filename, io.BytesIO(content), "application/pdf")},
    )
    assert response.status_code == 201


def _poll_until_terminal(client: TestClient, analysis_id: str, headers: dict[str, str]) -> dict:
    result: dict = {}
    for _ in range(40):
        response = client.get(f"/api/v1/analyses/{analysis_id}/progress", headers=headers)
        assert response.status_code == 200
        result = response.json()
        if result["state"] in ("completed", "failed"):
            break
        time.sleep(0.05)
    return result


def _run_to_completion_and_get_findings(
    client: TestClient, email: str, exam_pdf: bytes, tp153_pdf: bytes
) -> dict[str, dict]:
    analysis_id = _create_analysis(client, email)
    _upload(client, analysis_id, email, "exam", "exam.pdf", exam_pdf)
    _upload(client, analysis_id, email, "tp153", "tp153.pdf", tp153_pdf)

    headers = auth_header(email)
    run_response = client.post(f"/api/v1/analyses/{analysis_id}/run", headers=headers)
    assert run_response.status_code == 202

    progress = _poll_until_terminal(client, analysis_id, headers)
    assert progress["state"] == "completed", progress

    findings = client.get(f"/api/v1/analyses/{analysis_id}/findings", headers=headers).json()
    return {f["rule_id"]: f for f in findings}


def test_multiple_clos_yields_runtime_findings_but_rule006_remains_absent(
    client: TestClient,
) -> None:
    # build_complete_tp153_pdf() has 3 CLOs - RULE006 cannot judge
    # concentration for 2+ CLOs, so no Finding is persisted for it at all.
    findings = _run_to_completion_and_get_findings(
        client,
        "m8c-1@kau.edu.sa",
        build_exam_citing_all_clos_and_topics_pdf(),
        build_complete_tp153_pdf(),
    )
    assert set(findings) == UNCONDITIONAL_RULE_IDS
    assert "RULE006" not in findings


def test_full_citations_satisfies_all_deterministic_alignment_and_coverage_rules(
    client: TestClient,
) -> None:
    findings = _run_to_completion_and_get_findings(
        client,
        "m8c-2@kau.edu.sa",
        build_exam_citing_all_clos_and_topics_pdf(),
        build_complete_tp153_pdf(),
    )
    assert findings["RULE001"]["status"] == "Satisfied"
    assert findings["RULE005"]["status"] == "Satisfied"
    assert findings["RULE007"]["status"] == "Satisfied"
    assert findings["RULE009"]["status"] == "Satisfied"
    for rule_id in ("RULE001", "RULE005", "RULE007", "RULE009"):
        assert findings[rule_id]["requirement_id"].startswith("REQ")
        assert len(findings[rule_id]["evidence"]) > 0
    for rule_id in SEMANTIC_RULE_IDS:
        assert findings[rule_id]["status"] == "Not Verified"
        assert findings[rule_id]["prompt_template_version"]
        assert findings[rule_id]["kb_version"]


def test_no_citations_is_not_verified_for_alignment_and_coverage(client: TestClient) -> None:
    # Absence of any citation must never be reported as Not Satisfied - only
    # Not Verified (we have no evidence either way).
    findings = _run_to_completion_and_get_findings(
        client,
        "m8c-3@kau.edu.sa",
        build_exam_citing_no_clos_or_topics_pdf(),
        build_complete_tp153_pdf(),
    )
    assert set(findings) == UNCONDITIONAL_RULE_IDS
    assert findings["RULE001"]["status"] == "Not Verified"
    assert findings["RULE007"]["status"] == "Not Verified"
    assert findings["RULE005"]["status"] == "Not Verified"
    assert findings["RULE009"]["status"] == "Not Verified"
    for rule_id in DETERMINISTIC_RULE_IDS:
        assert findings[rule_id]["status"] != "Not Satisfied"


def test_some_citations_is_partially_satisfied_for_alignment_and_coverage(
    client: TestClient,
) -> None:
    findings = _run_to_completion_and_get_findings(
        client,
        "m8c-4@kau.edu.sa",
        build_exam_citing_some_clos_and_topics_pdf(),
        build_complete_tp153_pdf(),
    )
    assert findings["RULE001"]["status"] == "Partially Satisfied"
    assert findings["RULE007"]["status"] == "Partially Satisfied"
    # Only CLO1/T1 were ever cited out of 3 applicable each - some but not
    # every applicable CLO/topic is covered.
    assert findings["RULE005"]["status"] == "Partially Satisfied"
    assert findings["RULE009"]["status"] == "Partially Satisfied"
    for rule_id in DETERMINISTIC_RULE_IDS:
        assert findings[rule_id]["status"] != "Not Satisfied"


def test_hyphenated_and_bracketed_citation_variants_are_recognized(client: TestClient) -> None:
    findings = _run_to_completion_and_get_findings(
        client,
        "m8c-5@kau.edu.sa",
        build_exam_citing_hyphenated_and_bracketed_variants_pdf(),
        build_complete_tp153_pdf(),
    )
    assert findings["RULE001"]["status"] == "Satisfied"
    assert findings["RULE007"]["status"] == "Satisfied"
    assert findings["RULE005"]["status"] == "Satisfied"
    assert findings["RULE009"]["status"] == "Satisfied"


def test_zero_clos_yields_rule006_not_verified_and_excluded_from_score(client: TestClient) -> None:
    findings = _run_to_completion_and_get_findings(
        client,
        "m8c-6@kau.edu.sa",
        build_exam_citing_two_topics_pdf(),
        build_missing_clo_section_tp153_pdf(),
    )
    assert findings["RULE001"]["status"] == "Not Verified"
    assert findings["RULE005"]["status"] == "Not Verified"
    assert findings["RULE006"]["status"] == "Not Verified"
    # Topics/assessment records are still present in this TP-153 fixture -
    # only the CLO section is missing (see tp153_pdf_fixtures.py).
    assert findings["RULE007"]["status"] == "Satisfied"
    assert findings["RULE009"]["status"] == "Satisfied"
    assert set(findings) == UNCONDITIONAL_RULE_IDS | {"RULE006"}

    statuses = [AcademicStatus(f["status"]) for f in findings.values()]
    not_verified_count = sum(1 for s in statuses if s == AcademicStatus.NOT_VERIFIED)
    assert not_verified_count == 6  # RULE001/005/006 plus all three semantic rules

    # calculate_overall_score excludes both Not Verified and Not Applicable
    # (RULE018 marks/total is Not Applicable here - this exam has no
    # declared total line, unrelated to the missing CLO section).
    excluded = sum(
        1 for s in statuses if s in (AcademicStatus.NOT_VERIFIED, AcademicStatus.NOT_APPLICABLE)
    )
    score = calculate_overall_score(statuses)
    assert score.denominator == len(statuses) - excluded


def test_single_applicable_clo_makes_coverage_distribution_not_applicable(
    client: TestClient,
) -> None:
    # build_incomplete_assessment_tp153_pdf() (M5) has exactly one CLO -
    # RULE006's one KB-defined, reachable-without-invented-logic Not
    # Applicable condition, exercised here through the real pipeline.
    findings = _run_to_completion_and_get_findings(
        client,
        "m8c-7@kau.edu.sa",
        build_exam_citing_all_clos_and_topics_pdf(),
        build_incomplete_assessment_tp153_pdf(),
    )
    assert findings["RULE006"]["status"] == "Not Applicable"
    assert set(findings) == UNCONDITIONAL_RULE_IDS | {"RULE006"}


def test_exactly_the_three_approved_semantic_rules_appear(client: TestClient) -> None:
    # Covers every fixture combination used above and guards against both
    # accidentally omitting an approved evaluator and expanding semantic scope.
    scenarios = [
        (build_exam_citing_all_clos_and_topics_pdf(), build_complete_tp153_pdf()),
        (build_exam_citing_no_clos_or_topics_pdf(), build_complete_tp153_pdf()),
        (build_exam_citing_two_topics_pdf(), build_missing_clo_section_tp153_pdf()),
        (build_exam_citing_all_clos_and_topics_pdf(), build_incomplete_assessment_tp153_pdf()),
    ]
    for i, (exam_pdf, tp153_pdf) in enumerate(scenarios):
        findings = _run_to_completion_and_get_findings(
            client, f"m8c-removed-{i}@kau.edu.sa", exam_pdf, tp153_pdf
        )
        semantic_findings = {
            rule_id
            for rule_id, finding in findings.items()
            if finding["evaluator_type"] in {"semantic_ai", "semantic_precondition"}
        }
        assert semantic_findings == SEMANTIC_RULE_IDS


def test_invalid_semantic_output_fails_pipeline_and_rolls_back_all_findings(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = load_kb_snapshot(KB_SOURCE)
    runtime = SemanticRuntime(
        provider=FakeAiProvider(responses=["{bad", "{still-bad"]),
        vector_store=InMemoryVectorStore(),
        snapshot=snapshot,
    )
    monkeypatch.setattr(stages, "get_semantic_runtime", lambda settings: runtime)

    email = "semantic-failure@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _upload(
        client,
        analysis_id,
        email,
        "exam",
        "exam.pdf",
        build_exam_citing_all_clos_and_topics_pdf(),
    )
    _upload(
        client,
        analysis_id,
        email,
        "tp153",
        "tp153.pdf",
        build_complete_tp153_pdf(),
    )
    headers = auth_header(email)

    response = client.post(f"/api/v1/analyses/{analysis_id}/run", headers=headers)
    assert response.status_code == 202
    progress = _poll_until_terminal(client, analysis_id, headers)

    assert progress["state"] == "failed"
    assert progress["message"] == (
        "Processing failed due to an internal error. Please try again later."
    )
    findings = client.get(
        f"/api/v1/analyses/{analysis_id}/findings",
        headers=headers,
    )
    assert findings.status_code == 200
    assert findings.json() == []
