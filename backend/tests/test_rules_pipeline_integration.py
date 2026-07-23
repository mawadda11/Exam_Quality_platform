from __future__ import annotations

import io
import time

from fastapi.testclient import TestClient
from helpers import auth_header
from pdf_fixtures import build_blank_pdf
from rules_pdf_fixtures import (
    build_exam_with_correct_total_pdf,
    build_exam_with_duplicate_top_level_numbering_pdf,
    build_exam_with_incorrect_total_pdf,
    build_exam_with_missing_marks_evidence_pdf,
    build_exam_with_valid_child_numbering_pdf,
)
from tp153_pdf_fixtures import build_complete_tp153_pdf

ANALYSIS_PAYLOAD = {
    "course": {"code": "CPIT-450", "name": "Software Engineering"},
    "exam_type": "Midterm",
    "term": "2026 Spring",
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
    client: TestClient, email: str, exam_pdf: bytes
) -> dict[str, dict]:
    analysis_id = _create_analysis(client, email)
    _upload(client, analysis_id, email, "exam", "exam.pdf", exam_pdf)
    _upload(client, analysis_id, email, "tp153", "tp153.pdf", build_complete_tp153_pdf())

    headers = auth_header(email)
    run_response = client.post(f"/api/v1/analyses/{analysis_id}/run", headers=headers)
    assert run_response.status_code == 202

    progress = _poll_until_terminal(client, analysis_id, headers)
    assert progress["state"] == "completed", progress

    findings = client.get(f"/api/v1/analyses/{analysis_id}/findings", headers=headers).json()
    by_rule_id = {f["rule_id"]: f for f in findings}
    assert set(by_rule_id) == {"RULE018", "RULE019"}
    return by_rule_id


def test_correct_declared_total_is_satisfied(client: TestClient) -> None:
    findings = _run_to_completion_and_get_findings(
        client, "rules1@kau.edu.sa", build_exam_with_correct_total_pdf()
    )
    assert findings["RULE018"]["status"] == "Satisfied"
    assert findings["RULE018"]["requirement_id"] == "REQ018"
    assert len(findings["RULE018"]["evidence"]) > 0


def test_incorrect_declared_total_is_not_satisfied(client: TestClient) -> None:
    findings = _run_to_completion_and_get_findings(
        client, "rules2@kau.edu.sa", build_exam_with_incorrect_total_pdf()
    )
    assert findings["RULE018"]["status"] == "Not Satisfied"


def test_duplicate_top_level_numbering_is_not_satisfied(client: TestClient) -> None:
    findings = _run_to_completion_and_get_findings(
        client, "rules3@kau.edu.sa", build_exam_with_duplicate_top_level_numbering_pdf()
    )
    assert findings["RULE019"]["status"] == "Not Satisfied"
    assert "Q2" in findings["RULE019"]["explanation"]


def test_valid_child_numbering_under_different_parents_is_satisfied(client: TestClient) -> None:
    findings = _run_to_completion_and_get_findings(
        client, "rules4@kau.edu.sa", build_exam_with_valid_child_numbering_pdf()
    )
    assert findings["RULE019"]["status"] == "Satisfied"


def test_missing_marks_evidence_is_not_verified(client: TestClient) -> None:
    findings = _run_to_completion_and_get_findings(
        client, "rules5@kau.edu.sa", build_exam_with_missing_marks_evidence_pdf()
    )
    assert findings["RULE018"]["status"] == "Not Verified"
    assert "Q2" in findings["RULE018"]["explanation"]


def test_missing_numbering_evidence_is_not_verified(client: TestClient) -> None:
    findings = _run_to_completion_and_get_findings(client, "rules6@kau.edu.sa", build_blank_pdf())
    assert findings["RULE019"]["status"] == "Not Verified"
    # No declared total and no questions at all - Not Applicable, not a crash.
    assert findings["RULE018"]["status"] == "Not Applicable"


def test_findings_have_no_duplicate_evidence_links(client: TestClient) -> None:
    findings = _run_to_completion_and_get_findings(
        client, "rules7@kau.edu.sa", build_exam_with_correct_total_pdf()
    )
    for finding in findings.values():
        evidence_ids = [e["id"] for e in finding["evidence"]]
        assert len(evidence_ids) == len(set(evidence_ids))
