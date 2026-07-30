from __future__ import annotations

import io
import time
import uuid

from fastapi.testclient import TestClient
from helpers import auth_header
from pdf_fixtures import build_synthetic_exam_pdf
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from tp153_pdf_fixtures import build_complete_tp153_pdf

from app.models.uploaded_file import UploadedFile

_ANALYSIS_PAYLOAD = {
    "course": {"code": "CPIT-452", "name": "Database Systems"},
    "exam_type": "Midterm",
    "term": "2026 Spring",
}


def _poll_review_ready(client: TestClient, analysis_id: str, headers: dict[str, str]) -> None:
    for _ in range(60):
        response = client.get(f"/api/v1/analyses/{analysis_id}/progress", headers=headers)
        assert response.status_code == 200
        if response.json()["state"] in {"review_ready", "failed"}:
            assert response.json()["state"] == "review_ready"
            return
        time.sleep(0.05)
    raise AssertionError("Analysis did not reach Extraction Review.")


def test_pipeline_persists_language_method_confidence_and_parser_layout(
    client: TestClient,
    db_engine: Engine,
) -> None:
    email = "bilingual-metadata@kau.edu.sa"
    headers = auth_header(email)
    response = client.post("/api/v1/analyses", json=_ANALYSIS_PAYLOAD, headers=headers)
    assert response.status_code == 201
    analysis_id = response.json()["id"]

    for file_type, filename, content in (
        ("exam", "exam.pdf", build_synthetic_exam_pdf()),
        ("tp153", "course-specification.pdf", build_complete_tp153_pdf()),
    ):
        upload = client.post(
            f"/api/v1/analyses/{analysis_id}/files",
            headers=headers,
            data={"file_type": file_type},
            files={"file": (filename, io.BytesIO(content), "application/pdf")},
        )
        assert upload.status_code == 201

    run = client.post(f"/api/v1/analyses/{analysis_id}/run", headers=headers)
    assert run.status_code == 202
    _poll_review_ready(client, analysis_id, headers)

    with Session(db_engine) as session:
        rows = (
            session.execute(
                select(UploadedFile).where(UploadedFile.analysis_id == uuid.UUID(analysis_id))
            )
            .scalars()
            .all()
        )

    by_type = {row.file_type.value: row for row in rows}
    assert by_type["exam"].detected_language == "english"
    assert by_type["exam"].extraction_method == "direct_text"
    assert by_type["exam"].extraction_confidence is not None
    assert by_type["exam"].review_recommended is False
    assert by_type["tp153"].detected_language == "english"
    assert by_type["tp153"].extraction_method == "direct_text"
    assert by_type["tp153"].parser_layout == "section_heading"
