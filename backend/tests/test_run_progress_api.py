from __future__ import annotations

import io
import time

import pytest
from fastapi.testclient import TestClient
from helpers import auth_header, valid_pdf_bytes
from pdf_fixtures import build_synthetic_exam_pdf

import app.services.processing.stages as stages
from app.core.domain import ProcessingStage
from app.models.analysis import Analysis
from app.services.processing.runner import SAFE_FAILURE_MESSAGE

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


def _make_ready_analysis(client: TestClient, email: str) -> str:
    # A real, parseable exam PDF is required here (not the minimal fake-PDF
    # fixture) since M4 wired real extraction into EXTRACTING_EXAM - these
    # tests care about run/progress mechanics succeeding end-to-end, not
    # extraction correctness itself (see test_extraction_pipeline.py).
    analysis_id = _create_analysis(client, email)
    _upload(client, analysis_id, email, "exam", "exam.pdf", build_synthetic_exam_pdf())
    _upload(client, analysis_id, email, "tp153", "tp153.pdf", valid_pdf_bytes())
    return analysis_id


def _poll_until_terminal(client: TestClient, analysis_id: str, headers: dict[str, str]) -> dict:
    result: dict = {}
    for _ in range(20):
        response = client.get(f"/api/v1/analyses/{analysis_id}/progress", headers=headers)
        assert response.status_code == 200
        result = response.json()
        if result["state"] in ("completed", "failed"):
            break
        time.sleep(0.05)
    return result


def test_run_rejects_when_files_are_missing(client: TestClient) -> None:
    analysis_id = _create_analysis(client, "u1@kau.edu.sa")
    response = client.post(
        f"/api/v1/analyses/{analysis_id}/run", headers=auth_header("u1@kau.edu.sa")
    )
    assert response.status_code == 409


def test_run_rejects_on_analysis_not_owned(client: TestClient) -> None:
    analysis_id = _make_ready_analysis(client, "owner@kau.edu.sa")
    response = client.post(
        f"/api/v1/analyses/{analysis_id}/run", headers=auth_header("intruder@kau.edu.sa")
    )
    assert response.status_code == 404


def test_run_missing_auth_header_returns_401(client: TestClient) -> None:
    analysis_id = _make_ready_analysis(client, "u_auth@kau.edu.sa")
    response = client.post(f"/api/v1/analyses/{analysis_id}/run")
    assert response.status_code == 401


def test_run_starts_pipeline_and_reaches_completed(client: TestClient) -> None:
    analysis_id = _make_ready_analysis(client, "u2@kau.edu.sa")
    headers = auth_header("u2@kau.edu.sa")

    run_response = client.post(f"/api/v1/analyses/{analysis_id}/run", headers=headers)
    assert run_response.status_code == 202

    progress = _poll_until_terminal(client, analysis_id, headers)
    assert progress["state"] == "completed"
    assert progress["message"] is None


def test_run_twice_returns_conflict(client: TestClient) -> None:
    analysis_id = _make_ready_analysis(client, "u3@kau.edu.sa")
    headers = auth_header("u3@kau.edu.sa")

    first = client.post(f"/api/v1/analyses/{analysis_id}/run", headers=headers)
    assert first.status_code == 202

    second = client.post(f"/api/v1/analyses/{analysis_id}/run", headers=headers)
    assert second.status_code == 409


def test_progress_not_owned_returns_404(client: TestClient) -> None:
    analysis_id = _create_analysis(client, "owner2@kau.edu.sa")
    response = client.get(
        f"/api/v1/analyses/{analysis_id}/progress", headers=auth_header("intruder2@kau.edu.sa")
    )
    assert response.status_code == 404


def test_progress_before_run_shows_queued_with_no_message(client: TestClient) -> None:
    analysis_id = _create_analysis(client, "u4@kau.edu.sa")
    response = client.get(
        f"/api/v1/analyses/{analysis_id}/progress", headers=auth_header("u4@kau.edu.sa")
    )
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "queued"
    assert body["message"] is None


def test_progress_reports_failed_with_safe_message(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(analysis: Analysis, session: object, settings: object) -> None:
        raise RuntimeError("sensitive internal detail")

    monkeypatch.setitem(stages.STAGE_HANDLERS, ProcessingStage.EXTRACTING_EXAM, boom)

    analysis_id = _make_ready_analysis(client, "u5@kau.edu.sa")
    headers = auth_header("u5@kau.edu.sa")
    client.post(f"/api/v1/analyses/{analysis_id}/run", headers=headers)

    progress = _poll_until_terminal(client, analysis_id, headers)
    assert progress["state"] == "failed"
    assert progress["message"] == SAFE_FAILURE_MESSAGE
    assert "sensitive internal detail" not in (progress["message"] or "")
