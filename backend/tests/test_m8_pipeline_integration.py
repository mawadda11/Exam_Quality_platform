from __future__ import annotations

import io
import time

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

from app.core.domain import AcademicStatus
from app.services.rules.scoring import calculate_overall_score

ANALYSIS_PAYLOAD = {
    "course": {"code": "CPIT-450", "name": "Software Engineering"},
    "exam_type": "Midterm",
    "term": "2026 Spring",
}

ALL_NINE_RULE_IDS = {
    "RULE001",
    "RULE002",
    "RULE005",
    "RULE006",
    "RULE007",
    "RULE008",
    "RULE009",
    "RULE018",
    "RULE019",
}


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


def test_all_nine_findings_present_together_m6_and_m8(client: TestClient) -> None:
    # M6's marks/numbering findings must keep being produced alongside M8's
    # seven - run_applying_rules extends, never replaces.
    findings = _run_to_completion_and_get_findings(
        client,
        "m8-1@kau.edu.sa",
        build_exam_citing_all_clos_and_topics_pdf(),
        build_complete_tp153_pdf(),
    )
    assert set(findings) == ALL_NINE_RULE_IDS


def test_full_citations_satisfies_all_deterministic_alignment_and_coverage_rules(
    client: TestClient,
) -> None:
    findings = _run_to_completion_and_get_findings(
        client,
        "m8-2@kau.edu.sa",
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

    # 3 CLOs are applicable here (not exactly 1), so RULE006 cannot reach
    # its Not Applicable branch - it and the two always-deferred rules are
    # Not Verified regardless of how many citations exist.
    assert findings["RULE002"]["status"] == "Not Verified"
    assert findings["RULE006"]["status"] == "Not Verified"
    assert findings["RULE008"]["status"] == "Not Verified"


def test_no_citations_is_not_verified_for_alignment_and_coverage(client: TestClient) -> None:
    # Absence of any citation must never be reported as Not Satisfied - only
    # Not Verified (we have no evidence either way).
    findings = _run_to_completion_and_get_findings(
        client,
        "m8-3@kau.edu.sa",
        build_exam_citing_no_clos_or_topics_pdf(),
        build_complete_tp153_pdf(),
    )
    assert findings["RULE001"]["status"] == "Not Verified"
    assert findings["RULE007"]["status"] == "Not Verified"
    assert findings["RULE005"]["status"] == "Not Verified"
    assert findings["RULE009"]["status"] == "Not Verified"
    for rule_id in ALL_NINE_RULE_IDS:
        assert findings[rule_id]["status"] != "Not Satisfied"


def test_some_citations_is_partially_satisfied_for_alignment_and_coverage(
    client: TestClient,
) -> None:
    findings = _run_to_completion_and_get_findings(
        client,
        "m8-4@kau.edu.sa",
        build_exam_citing_some_clos_and_topics_pdf(),
        build_complete_tp153_pdf(),
    )
    assert findings["RULE001"]["status"] == "Partially Satisfied"
    assert findings["RULE007"]["status"] == "Partially Satisfied"
    # Only CLO1/T1 were ever cited out of 3 applicable each - some but not
    # every applicable CLO/topic is covered.
    assert findings["RULE005"]["status"] == "Partially Satisfied"
    assert findings["RULE009"]["status"] == "Partially Satisfied"
    for rule_id in ALL_NINE_RULE_IDS:
        assert findings[rule_id]["status"] != "Not Satisfied"


def test_hyphenated_and_bracketed_citation_variants_are_recognized(client: TestClient) -> None:
    findings = _run_to_completion_and_get_findings(
        client,
        "m8-5@kau.edu.sa",
        build_exam_citing_hyphenated_and_bracketed_variants_pdf(),
        build_complete_tp153_pdf(),
    )
    assert findings["RULE001"]["status"] == "Satisfied"
    assert findings["RULE007"]["status"] == "Satisfied"
    assert findings["RULE005"]["status"] == "Satisfied"
    assert findings["RULE009"]["status"] == "Satisfied"


def test_missing_clo_section_is_not_verified_and_excluded_from_score(client: TestClient) -> None:
    findings = _run_to_completion_and_get_findings(
        client,
        "m8-6@kau.edu.sa",
        build_exam_citing_two_topics_pdf(),
        build_missing_clo_section_tp153_pdf(),
    )
    assert findings["RULE001"]["status"] == "Not Verified"
    assert findings["RULE005"]["status"] == "Not Verified"
    # Zero CLOs is not "exactly one CLO", so RULE006 falls to Not Verified
    # too, same as the two always-deferred rules.
    assert findings["RULE002"]["status"] == "Not Verified"
    assert findings["RULE006"]["status"] == "Not Verified"
    assert findings["RULE008"]["status"] == "Not Verified"
    # Topics/assessment records are still present in this TP-153 fixture -
    # only the CLO section is missing (see tp153_pdf_fixtures.py).
    assert findings["RULE007"]["status"] == "Satisfied"
    assert findings["RULE009"]["status"] == "Satisfied"

    statuses = [AcademicStatus(f["status"]) for f in findings.values()]
    not_verified_count = sum(1 for s in statuses if s == AcademicStatus.NOT_VERIFIED)
    assert not_verified_count == 5

    # calculate_overall_score excludes both Not Verified and Not Applicable
    # (RULE018 marks/total is Not Applicable here - this exam has no
    # declared total line, which is unrelated to the missing CLO section).
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
        "m8-7@kau.edu.sa",
        build_exam_citing_all_clos_and_topics_pdf(),
        build_incomplete_assessment_tp153_pdf(),
    )
    assert findings["RULE006"]["status"] == "Not Applicable"
