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

import app.services.processing.runner as runner
import app.services.processing.stages as stages
from app.core.config import Settings
from app.core.domain import AcademicStatus
from app.models.analysis import Analysis
from app.services.ai.fake_provider import FakeAiProvider
from app.services.extraction.review_snapshot import materialize_initial_review_revision
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

RELATIONSHIP_SEMANTIC_RULE_IDS = {"RULE001", "RULE007"}
JUDGMENT_SEMANTIC_RULE_IDS = {
    "RULE002",
    "RULE003",
    "RULE004",
    "RULE008",
    "RULE011",
    "RULE012",
    "RULE013",
    "RULE021",
}
SEMANTIC_RULE_IDS = RELATIONSHIP_SEMANTIC_RULE_IDS | JUDGMENT_SEMANTIC_RULE_IDS
DETERMINISTIC_RULE_IDS = {
    "RULE005",
    "RULE009",
    "RULE014",
    "RULE016",
    "RULE018",
    "RULE019",
    "RULE022",
}
UNCONDITIONAL_RULE_IDS = SEMANTIC_RULE_IDS | DETERMINISTIC_RULE_IDS


@pytest.fixture(autouse=True)
def confirmed_downstream_stage_fixture(
    monkeypatch: pytest.MonkeyPatch, test_settings: Settings
) -> None:
    """Run confirmed M6-M9 stages with the offline governed semantic baseline."""

    test_settings.ai_provider = "local"
    test_settings.ai_model = "local-governed-baseline-v1"

    def run_confirmed_stages(analysis: Analysis, session: object, settings: object) -> None:
        revision = materialize_initial_review_revision(session, analysis.id)
        analysis.confirmed_review_id = revision.id
        session.flush()
        for stage in stages.POST_CONFIRMATION_STAGES:
            stages.STAGE_HANDLERS[stage](analysis, session, settings)

    monkeypatch.setattr(runner, "run_materializing_review", run_confirmed_stages)


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
        if result["state"] in ("review_ready", "completed", "failed"):
            break
        time.sleep(0.05)
    return result


def _run_to_completion_and_get_findings(
    client: TestClient, email: str, exam_pdf: bytes, tp153_pdf: bytes
) -> tuple[str, dict[str, dict]]:
    analysis_id = _create_analysis(client, email)
    _upload(client, analysis_id, email, "exam", "exam.pdf", exam_pdf)
    _upload(client, analysis_id, email, "tp153", "tp153.pdf", tp153_pdf)

    headers = auth_header(email)
    run_response = client.post(f"/api/v1/analyses/{analysis_id}/run", headers=headers)
    assert run_response.status_code == 202

    progress = _poll_until_terminal(client, analysis_id, headers)
    assert progress["state"] == "review_ready", progress

    response = client.get(f"/api/v1/analyses/{analysis_id}/findings", headers=headers)
    assert response.status_code == 200
    findings = {finding["rule_id"]: finding for finding in response.json()}
    return analysis_id, findings


def test_complete_inputs_execute_all_unconditional_m6_m9_rules_and_reduce_not_verified(
    client: TestClient,
) -> None:
    analysis_id, findings = _run_to_completion_and_get_findings(
        client,
        "m6-m9-complete@kau.edu.sa",
        build_exam_citing_all_clos_and_topics_pdf(),
        build_complete_tp153_pdf(),
    )

    assert set(findings) == UNCONDITIONAL_RULE_IDS
    assert "RULE006" not in findings  # documented partial branch for 2+ CLOs
    assert len(findings) == 17

    for rule_id in ("RULE001", "RULE005", "RULE007", "RULE009"):
        assert findings[rule_id]["status"] == "Satisfied"
        assert findings[rule_id]["evidence"]

    semantic = [findings[rule_id] for rule_id in SEMANTIC_RULE_IDS]
    assert all(finding["status"] != "Not Verified" for finding in semantic)
    assert all(finding["confidence_level"] == "High" for finding in semantic)
    assert all(finding["evaluation_details"] is not None for finding in semantic)
    assert all(finding["prompt_template_version"] for finding in semantic)
    assert all(finding["kb_version"] for finding in semantic)

    coverage = client.get(
        f"/api/v1/analyses/{analysis_id}/rule-coverage",
        headers=auth_header("m6-m9-complete@kau.edu.sa"),
    )
    assert coverage.status_code == 200
    body = coverage.json()
    assert body["total_rules"] == 21
    assert body["evaluated_rules"] == 17
    assert body["conditional_capability_gap_rules"] == 1
    assert body["unsupported_rules"] == 3
    assert body["not_run_rules"] == 0
    assert body["runtime_integrity_ok"] is True


def test_semantic_alignment_evaluates_uncited_questions_instead_of_defaulting_not_verified(
    client: TestClient,
) -> None:
    _, findings = _run_to_completion_and_get_findings(
        client,
        "m6-m9-uncited@kau.edu.sa",
        build_exam_citing_no_clos_or_topics_pdf(),
        build_complete_tp153_pdf(),
    )

    assert set(findings) == UNCONDITIONAL_RULE_IDS
    for rule_id in ("RULE001", "RULE002", "RULE004", "RULE007", "RULE008"):
        assert findings[rule_id]["status"] != "Not Verified"
        assert findings[rule_id]["evaluator_type"] == "local_semantic_baseline"
        assert findings[rule_id]["confidence_level"] == "High"

    # Complete item judgments with no supported relationship are a negative
    # academic result, not missing evidence.
    assert findings["RULE005"]["status"] == "Not Satisfied"
    assert findings["RULE009"]["status"] == "Not Satisfied"


def test_partial_relationships_produce_traceable_non_default_results(client: TestClient) -> None:
    _, findings = _run_to_completion_and_get_findings(
        client,
        "m6-m9-partial@kau.edu.sa",
        build_exam_citing_some_clos_and_topics_pdf(),
        build_complete_tp153_pdf(),
    )

    for rule_id in ("RULE001", "RULE002", "RULE004", "RULE007", "RULE008"):
        assert findings[rule_id]["status"] != "Not Verified"
        details = findings[rule_id]["evaluation_details"]
        assert details["item_judgments"]
        assert set(details["evidence_used"]) == {
            evidence["id"] for evidence in findings[rule_id]["evidence"]
        }

    assert findings["RULE001"]["status"] in {"Satisfied", "Partially Satisfied"}
    assert findings["RULE005"]["status"] in {
        "Partially Satisfied",
        "Not Satisfied",
    }


def test_hyphenated_and_bracketed_controlled_identifiers_are_recognized(
    client: TestClient,
) -> None:
    _, findings = _run_to_completion_and_get_findings(
        client,
        "m6-m9-identifier-variants@kau.edu.sa",
        build_exam_citing_hyphenated_and_bracketed_variants_pdf(),
        build_complete_tp153_pdf(),
    )

    assert findings["RULE001"]["status"] == "Satisfied"
    assert findings["RULE007"]["status"] == "Satisfied"
    assert findings["RULE005"]["status"] == "Satisfied"
    assert findings["RULE009"]["status"] == "Satisfied"


def test_missing_clo_source_is_the_genuine_not_verified_case_and_score_excludes_it(
    client: TestClient,
) -> None:
    _, findings = _run_to_completion_and_get_findings(
        client,
        "m6-m9-missing-clo@kau.edu.sa",
        build_exam_citing_two_topics_pdf(),
        build_missing_clo_section_tp153_pdf(),
    )

    assert set(findings) == UNCONDITIONAL_RULE_IDS | {"RULE006"}
    for rule_id in ("RULE001", "RULE002", "RULE004"):
        assert findings[rule_id]["status"] == "Not Verified"
        assert findings[rule_id]["evaluator_type"] == "semantic_precondition"
        assert findings[rule_id]["confidence_level"] == "Low"
    assert findings["RULE005"]["status"] == "Not Verified"
    assert findings["RULE006"]["status"] == "Not Verified"

    # Independent topic, method and question-writing rules still execute.
    for rule_id in ("RULE003", "RULE007", "RULE008", "RULE011", "RULE012", "RULE013"):
        assert findings[rule_id]["status"] != "Not Verified"

    statuses = [AcademicStatus(finding["status"]) for finding in findings.values()]
    excluded = sum(
        status in (AcademicStatus.NOT_VERIFIED, AcademicStatus.NOT_APPLICABLE)
        for status in statuses
    )
    score = calculate_overall_score(statuses)
    assert score.denominator == len(statuses) - excluded


def test_single_applicable_clo_makes_distribution_not_applicable(
    client: TestClient,
) -> None:
    _, findings = _run_to_completion_and_get_findings(
        client,
        "m6-m9-single-clo@kau.edu.sa",
        build_exam_citing_all_clos_and_topics_pdf(),
        build_incomplete_assessment_tp153_pdf(),
    )

    assert findings["RULE006"]["status"] == "Not Applicable"
    assert set(findings) == UNCONDITIONAL_RULE_IDS | {"RULE006"}


def test_exactly_the_ten_governed_semantic_rules_execute(client: TestClient) -> None:
    _, findings = _run_to_completion_and_get_findings(
        client,
        "m6-m9-semantic-scope@kau.edu.sa",
        build_exam_citing_all_clos_and_topics_pdf(),
        build_complete_tp153_pdf(),
    )

    semantic_findings = {
        rule_id
        for rule_id, finding in findings.items()
        if finding["evaluator_type"]
        in {"semantic_ai", "local_semantic_baseline", "semantic_precondition"}
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
        "The TP-153 Course Specification could not be extracted. Review the PDF and retry."
    )
    assert progress["failed_stage"] == "extracting_tp153"
    assert progress["error_code"] == "TP153_EXTRACTION_FAILED"
    assert progress["can_retry"] is True
    findings = client.get(
        f"/api/v1/analyses/{analysis_id}/findings",
        headers=headers,
    )
    assert findings.status_code == 200
    assert findings.json() == []
