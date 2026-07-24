"""Milestone 11's one performance test, deliberately not a load/benchmark
test - the SRS's only Performance NFR is "background jobs and progress
polling" (docs/SRS.md), and TEST_PLAN.md defines no throughput/latency
target to benchmark against. What's actually verifiable, faithfully, is the
architectural *contract* behind that NFR: POST /run schedules the pipeline
and returns the pre-processing state immediately, rather than awaiting the
pipeline inline before responding.

This is deliberately not a wall-clock timing assertion (e.g. "responds in
under N ms"). Two reasons: no latency budget exists anywhere in the docs to
assert against (inventing one would be exactly the kind of undocumented
threshold this milestone was told to avoid), and FastAPI's TestClient does
not decouple response-completion from background-task-completion the way a
real deployed ASGI server does - a real client's connection receives the
response before the server process necessarily finishes the background
task, but TestClient's in-process ASGI call does not return control to the
test until the whole call (including the awaited background task) is done.
Timing TestClient itself would therefore measure TestClient's execution
model, not this application's behavior.

The contract that *is* testable regardless of that difference: the
response body is built from the analysis row's state at the moment
`run_analysis` schedules the task - before that task's own effects, if any,
have happened - proving the request-handling code path never awaits the
pipeline inline.
"""

from __future__ import annotations

import io
import uuid

import pytest
from fastapi.testclient import TestClient
from helpers import auth_header

ANALYSIS_PAYLOAD = {
    "course": {"code": "CPIT-450", "name": "Software Engineering"},
    "exam_type": "Midterm",
    "term": "2026 Spring",
}

# Upload-time validation (app.services.storage.validation) only checks the
# filename extension, declared MIME type, PDF magic bytes, and trailer - real
# parsing happens later, inside the pipeline stages this test's fake pipeline
# replaces. A minimal-but-valid PDF byte string is therefore sufficient here
# and keeps this test fast, unlike test_run_progress_api.py's real fixture
# PDFs, which that file needs because it runs the real pipeline.
MINIMAL_VALID_PDF = b"%PDF-1.4\n0000\n%%EOF"


def _make_ready_analysis(client: TestClient, email: str) -> str:
    create = client.post("/api/v1/analyses", json=ANALYSIS_PAYLOAD, headers=auth_header(email))
    assert create.status_code == 201
    analysis_id: str = create.json()["id"]

    for file_type in ("exam", "tp153"):
        response = client.post(
            f"/api/v1/analyses/{analysis_id}/files",
            headers=auth_header(email),
            data={"file_type": file_type},
            files={"file": (f"{file_type}.pdf", io.BytesIO(MINIMAL_VALID_PDF), "application/pdf")},
        )
        assert response.status_code == 201
    return analysis_id


def test_run_response_reflects_pre_scheduling_state_not_the_pipelines_outcome(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Proves POST /run's response body is computed from the analysis row
    as it stood *before* the background task's effects - i.e. the request
    handler schedules and returns; it does not run the pipeline inline.
    A fake pipeline that immediately marks the analysis COMPLETED is used
    precisely so that if the handler ever regressed into awaiting the
    pipeline before building its response, this test would see "completed"
    instead of "queued" and fail."""
    calls: list[uuid.UUID] = []

    def fake_pipeline(analysis_id: uuid.UUID) -> None:
        calls.append(analysis_id)
        # Deliberately does NOT touch the database - if this function's
        # effects ever leaked into the /run response, that would itself
        # prove the request path is no longer non-blocking.

    monkeypatch.setattr("app.api.analyses.run_analysis_pipeline", fake_pipeline)

    analysis_id = _make_ready_analysis(client, "perf@kau.edu.sa")
    headers = auth_header("perf@kau.edu.sa")

    response = client.post(f"/api/v1/analyses/{analysis_id}/run", headers=headers)

    assert response.status_code == 202
    assert response.json()["state"] == "queued"
    assert calls == [uuid.UUID(analysis_id)]
