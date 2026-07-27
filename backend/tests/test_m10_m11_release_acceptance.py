from __future__ import annotations

import io
import time

from clo_topic_pdf_fixtures import build_exam_citing_all_clos_and_topics_pdf
from fastapi.testclient import TestClient
from helpers import auth_header
from tp153_pdf_fixtures import build_complete_tp153_pdf

from app.core.config import Settings

ANALYSIS_PAYLOAD = {
    "course": {"code": "CPIT-450", "name": "Software Engineering"},
    "exam_type": "Midterm",
    "term": "2026 Spring",
}


def _upload(
    client: TestClient,
    analysis_id: str,
    email: str,
    file_type: str,
    filename: str,
    content: bytes,
) -> None:
    response = client.post(
        f"/api/v1/analyses/{analysis_id}/files",
        headers=auth_header(email),
        data={"file_type": file_type},
        files={"file": (filename, io.BytesIO(content), "application/pdf")},
    )
    assert response.status_code == 201, response.text


def _wait_for_state(
    client: TestClient,
    analysis_id: str,
    email: str,
    expected: set[str],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for _ in range(80):
        response = client.get(
            f"/api/v1/analyses/{analysis_id}/progress",
            headers=auth_header(email),
        )
        assert response.status_code == 200
        result = response.json()
        if result["state"] in expected:
            return result
        time.sleep(0.025)
    raise AssertionError(f"Analysis did not reach one of {expected}: {result}")


def test_m10_m11_complete_confirmed_workflow_and_report_is_owner_scoped(
    client: TestClient,
    test_settings: Settings,
) -> None:
    """Acceptance path for the post-M9 governed release.

    This test crosses every public boundary that M10 presents and M11 must
    release-validate: secure upload, review pause, exact confirmation,
    semantic/deterministic findings, denominator, runtime coverage, report
    generation/download, and owner-safe access control.
    """

    test_settings.ai_provider = "local"
    test_settings.ai_model = "local-governed-baseline-v1"

    owner = "m10-m11-owner@kau.edu.sa"
    intruder = "m10-m11-intruder@kau.edu.sa"
    created = client.post(
        "/api/v1/analyses",
        json=ANALYSIS_PAYLOAD,
        headers=auth_header(owner),
    )
    assert created.status_code == 201
    analysis_id = created.json()["id"]

    _upload(
        client,
        analysis_id,
        owner,
        "exam",
        "exam.pdf",
        build_exam_citing_all_clos_and_topics_pdf(),
    )
    _upload(
        client,
        analysis_id,
        owner,
        "tp153",
        "tp153.pdf",
        build_complete_tp153_pdf(),
    )

    started = client.post(
        f"/api/v1/analyses/{analysis_id}/run",
        headers=auth_header(owner),
    )
    assert started.status_code == 202
    paused = _wait_for_state(client, analysis_id, owner, {"review_ready", "failed"})
    assert paused["state"] == "review_ready", paused

    review = client.get(
        f"/api/v1/analyses/{analysis_id}/extraction-review",
        headers=auth_header(owner),
    )
    assert review.status_code == 200
    review_body = review.json()
    assert review_body["can_confirm"] is True
    assert review_body["confirmation_blockers"] == []

    confirmed = client.post(
        f"/api/v1/analyses/{analysis_id}/extraction-review/confirm",
        headers=auth_header(owner),
        json={"revision_id": review_body["revision_id"]},
    )
    assert confirmed.status_code == 202, confirmed.text

    completed = _wait_for_state(client, analysis_id, owner, {"completed", "failed"})
    assert completed["state"] == "completed", completed

    findings_response = client.get(
        f"/api/v1/analyses/{analysis_id}/findings",
        headers=auth_header(owner),
    )
    assert findings_response.status_code == 200
    findings = findings_response.json()
    semantic = [item for item in findings if item["confidence_level"] is not None]
    assert semantic
    assert all(item["evaluation_details"] is not None for item in semantic)
    assert all(item["confidence_level"] in {"High", "Medium", "Low"} for item in semantic)
    relationships = [item for item in findings if item["rule_id"] in {"RULE001", "RULE007"}]
    assert all(item["evaluation_details"]["item_judgments"] for item in relationships)

    score = client.get(
        f"/api/v1/analyses/{analysis_id}/score",
        headers=auth_header(owner),
    )
    assert score.status_code == 200
    score_body = score.json()
    assert score_body["denominator"] > 0
    assert score_body["score"] is not None
    assert score_body["denominator"] == (
        score_body["satisfied_count"]
        + score_body["partially_satisfied_count"]
        + score_body["not_satisfied_count"]
    )

    coverage = client.get(
        f"/api/v1/analyses/{analysis_id}/rule-coverage",
        headers=auth_header(owner),
    )
    assert coverage.status_code == 200
    coverage_body = coverage.json()
    assert coverage_body["total_rules"] == 21
    assert coverage_body["runtime_integrity_ok"] is True
    assert coverage_body["not_run_rules"] == 0
    assert any(
        entry["runtime_disposition"] == "conditional_capability_gap"
        and entry["finding_status"] is None
        for entry in coverage_body["entries"]
    )

    generated = client.post(
        f"/api/v1/analyses/{analysis_id}/reports",
        headers=auth_header(owner),
    )
    assert generated.status_code == 201, generated.text
    report = generated.json()
    assert report["score"] == score_body["score"]
    assert report["denominator"] == score_body["denominator"]

    download = client.get(
        f"/api/v1/reports/{report['id']}/download",
        headers=auth_header(owner),
    )
    assert download.status_code == 200
    assert download.content.startswith(b"%PDF")
    assert len(download.content) == report["size_bytes"]

    for path in (
        f"/api/v1/analyses/{analysis_id}/findings",
        f"/api/v1/analyses/{analysis_id}/score",
        f"/api/v1/analyses/{analysis_id}/rule-coverage",
        f"/api/v1/reports/{report['id']}/download",
    ):
        denied = client.get(path, headers=auth_header(intruder))
        assert denied.status_code == 404
