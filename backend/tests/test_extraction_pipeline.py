from __future__ import annotations

import io
import time
import uuid

from fastapi.testclient import TestClient
from helpers import auth_header, valid_pdf_bytes
from pdf_fixtures import build_synthetic_exam_pdf
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.domain import UploadedFileType
from app.models.evidence import Evidence
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


def test_pipeline_extracts_and_persists_questions_from_real_exam(client: TestClient) -> None:
    email = "pipeline1@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _upload(client, analysis_id, email, "exam", "exam.pdf", build_synthetic_exam_pdf())
    _upload(client, analysis_id, email, "tp153", "tp153.pdf", valid_pdf_bytes())

    headers = auth_header(email)
    run_response = client.post(f"/api/v1/analyses/{analysis_id}/run", headers=headers)
    assert run_response.status_code == 202

    progress = _poll_until_terminal(client, analysis_id, headers)
    assert progress["state"] == "completed"
    assert progress["message"] is None

    questions_response = client.get(f"/api/v1/analyses/{analysis_id}/questions", headers=headers)
    assert questions_response.status_code == 200
    questions = questions_response.json()
    assert len(questions) == 8
    assert [q["number_label"] for q in questions] == [
        "Q1",
        "Q2",
        "Q2(a)",
        "Q2(b)",
        "Q3",
        "Q3(a)",
        "Q3(b)",
        "Q4",
    ]
    assert questions[0]["marks"] == 5.0
    assert questions[0]["page_number"] == 1
    assert questions[4]["page_number"] == 2  # Q3 is the first question on page 2


def test_pipeline_persists_evidence_with_traceable_fields(
    client: TestClient, db_engine: Engine
) -> None:
    email = "pipeline2@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _upload(client, analysis_id, email, "exam", "exam.pdf", build_synthetic_exam_pdf())
    _upload(client, analysis_id, email, "tp153", "tp153.pdf", valid_pdf_bytes())

    headers = auth_header(email)
    client.post(f"/api/v1/analyses/{analysis_id}/run", headers=headers)
    progress = _poll_until_terminal(client, analysis_id, headers)
    assert progress["state"] == "completed"

    with Session(db_engine) as session:
        evidence_rows = (
            session.execute(select(Evidence).where(Evidence.analysis_id == uuid.UUID(analysis_id)))
            .scalars()
            .all()
        )
        assert len(evidence_rows) == 15  # 1 instructions + 8 question_text + 6 marks

        marks_row = next(
            e for e in evidence_rows if e.evidence_type == "marks" and e.item_reference == "Q1"
        )
        assert marks_row.source_document == UploadedFileType.EXAM
        assert marks_row.page_number == 1
        assert marks_row.confidence == 1.0
        assert marks_row.extracted_text == "[5 marks]"


def test_pipeline_extraction_failure_yields_failed_state_with_safe_message(
    client: TestClient,
) -> None:
    email = "pipeline3@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    # Passes upload validation (correct magic bytes/EOF marker) but is not a
    # structurally real PDF - pdfplumber cannot parse it, exercising the
    # extraction-failure path without needing a special corrupt fixture.
    _upload(client, analysis_id, email, "exam", "exam.pdf", valid_pdf_bytes())
    _upload(client, analysis_id, email, "tp153", "tp153.pdf", valid_pdf_bytes())

    headers = auth_header(email)
    client.post(f"/api/v1/analyses/{analysis_id}/run", headers=headers)

    progress = _poll_until_terminal(client, analysis_id, headers)
    assert progress["state"] == "failed"
    assert progress["message"] == SAFE_FAILURE_MESSAGE
    assert "pdfminer" not in progress["message"].lower()
    assert "traceback" not in progress["message"].lower()

    questions_response = client.get(f"/api/v1/analyses/{analysis_id}/questions", headers=headers)
    assert questions_response.status_code == 200
    assert questions_response.json() == []
