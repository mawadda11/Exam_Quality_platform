from __future__ import annotations

import io
import time
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from helpers import auth_header
from pdf_fixtures import build_synthetic_exam_pdf
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from tp153_pdf_fixtures import build_complete_tp153_pdf, build_missing_clo_section_tp153_pdf

from app.core.domain import UploadedFileType
from app.models.evidence import Evidence
from app.services.extraction.digital_tp153_extractor import PdfPlumberTp153Extractor
from app.services.extraction.types import ExtractionError, Tp153ExtractionResult
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
        if result["state"] in ("review_ready", "completed", "failed"):
            break
        time.sleep(0.05)
    return result


def test_pipeline_extracts_and_persists_tp153_records(client: TestClient) -> None:
    email = "tp153pipeline1@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _upload(client, analysis_id, email, "exam", "exam.pdf", build_synthetic_exam_pdf())
    _upload(client, analysis_id, email, "tp153", "tp153.pdf", build_complete_tp153_pdf())

    headers = auth_header(email)
    run_response = client.post(f"/api/v1/analyses/{analysis_id}/run", headers=headers)
    assert run_response.status_code == 202

    progress = _poll_until_terminal(client, analysis_id, headers)
    assert progress["state"] == "review_ready"
    assert progress["message"] == "Extraction is ready for review."

    clos = client.get(f"/api/v1/analyses/{analysis_id}/clos", headers=headers).json()
    topics = client.get(f"/api/v1/analyses/{analysis_id}/topics", headers=headers).json()
    records = client.get(
        f"/api/v1/analyses/{analysis_id}/assessment-records", headers=headers
    ).json()

    assert [c["code"] for c in clos] == ["CLO1", "CLO2", "CLO3"]
    assert [t["code"] for t in topics] == ["T1", "T2", "T3"]
    assert [r["method"] for r in records] == ["Midterm Exam", "Final Exam", "Assignments"]
    assert records[0]["percentage"] == 20.0


def test_pipeline_persists_tp153_evidence_with_traceable_fields(
    client: TestClient, db_engine: Engine
) -> None:
    email = "tp153pipeline2@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _upload(client, analysis_id, email, "exam", "exam.pdf", build_synthetic_exam_pdf())
    _upload(client, analysis_id, email, "tp153", "tp153.pdf", build_complete_tp153_pdf())

    headers = auth_header(email)
    client.post(f"/api/v1/analyses/{analysis_id}/run", headers=headers)
    progress = _poll_until_terminal(client, analysis_id, headers)
    assert progress["state"] == "review_ready"

    with Session(db_engine) as session:
        tp153_evidence = (
            session.execute(
                select(Evidence).where(
                    Evidence.analysis_id == uuid.UUID(analysis_id),
                    Evidence.source_document == UploadedFileType.TP153,
                )
            )
            .scalars()
            .all()
        )
        # 3 CLOs + 3 topics + 3 assessment records = 9 TP-153 evidence rows.
        assert len(tp153_evidence) == 9
        assert all(e.source_document == UploadedFileType.TP153 for e in tp153_evidence)


def test_pipeline_missing_clo_section_persists_marker_not_invented_clo(
    client: TestClient, db_engine: Engine
) -> None:
    email = "tp153pipeline3@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _upload(client, analysis_id, email, "exam", "exam.pdf", build_synthetic_exam_pdf())
    _upload(client, analysis_id, email, "tp153", "tp153.pdf", build_missing_clo_section_tp153_pdf())

    headers = auth_header(email)
    client.post(f"/api/v1/analyses/{analysis_id}/run", headers=headers)
    progress = _poll_until_terminal(client, analysis_id, headers)
    assert progress["state"] == "review_ready"

    clos = client.get(f"/api/v1/analyses/{analysis_id}/clos", headers=headers).json()
    assert clos == []  # never an invented CLO

    with Session(db_engine) as session:
        missing_marker = (
            session.execute(
                select(Evidence).where(
                    Evidence.analysis_id == uuid.UUID(analysis_id),
                    Evidence.evidence_type == "missing_section",
                )
            )
            .scalars()
            .one()
        )
        assert missing_marker.item_reference == "clos"
        assert missing_marker.source_document == UploadedFileType.TP153


def test_pipeline_tp153_extraction_failure_yields_failed_state_with_safe_message(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_extract(self: PdfPlumberTp153Extractor, pdf_path: Path) -> Tp153ExtractionResult:
        raise ExtractionError(f"Injected parser failure for {pdf_path.name}")

    monkeypatch.setattr(PdfPlumberTp153Extractor, "extract", fail_extract)

    email = "tp153pipeline4@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _upload(client, analysis_id, email, "exam", "exam.pdf", build_synthetic_exam_pdf())
    # Parser-invalid PDFs are now rejected at upload time, so retain this
    # independent processing-failure test by injecting a TP-153 extractor
    # failure after a genuinely readable upload.
    _upload(client, analysis_id, email, "tp153", "tp153.pdf", build_complete_tp153_pdf())

    headers = auth_header(email)
    client.post(f"/api/v1/analyses/{analysis_id}/run", headers=headers)

    progress = _poll_until_terminal(client, analysis_id, headers)
    assert progress["state"] == "failed"
    assert progress["message"] == SAFE_FAILURE_MESSAGE
    assert "pdfminer" not in progress["message"].lower()

    clos_response = client.get(f"/api/v1/analyses/{analysis_id}/clos", headers=headers)
    assert clos_response.status_code == 200
    assert clos_response.json() == []
