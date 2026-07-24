from __future__ import annotations

import io
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from helpers import (
    auth_header,
    corrupted_pdf_bytes,
    encrypted_pdf_bytes,
    non_pdf_bytes,
    pdf_bytes_of_size,
    truncated_pdf_bytes,
    valid_pdf_bytes,
)
from pdf_fixtures import build_scanned_looking_exam_pdf
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.uploaded_file import UploadedFile
from app.services.storage.validation import PDF_READABILITY_ERROR

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
    client: TestClient,
    analysis_id: str,
    email: str,
    file_type: str,
    filename: str,
    content: bytes,
    content_type: str,
):
    return client.post(
        f"/api/v1/analyses/{analysis_id}/files",
        headers=auth_header(email),
        data={"file_type": file_type},
        files={"file": (filename, io.BytesIO(content), content_type)},
    )


def test_upload_valid_exam_pdf_returns_201(client: TestClient) -> None:
    analysis_id = _create_analysis(client, "u1@kau.edu.sa")

    response = _upload(
        client,
        analysis_id,
        "u1@kau.edu.sa",
        "exam",
        "exam.pdf",
        valid_pdf_bytes(),
        "application/pdf",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["file_type"] == "exam"
    assert len(body["sha256_hash"]) == 64
    assert "storage_key" not in body


@pytest.mark.parametrize("file_type", ["exam", "tp153"])
def test_upload_valid_scanned_pdf_without_digital_text_returns_201(
    client: TestClient, file_type: str
) -> None:
    analysis_id = _create_analysis(client, f"scanned-{file_type}@kau.edu.sa")

    response = _upload(
        client,
        analysis_id,
        f"scanned-{file_type}@kau.edu.sa",
        file_type,
        f"{file_type}.pdf",
        build_scanned_looking_exam_pdf(),
        "application/pdf",
    )

    assert response.status_code == 201
    assert response.json()["file_type"] == file_type


def test_upload_on_analysis_not_owned_returns_404(client: TestClient) -> None:
    analysis_id = _create_analysis(client, "owner@kau.edu.sa")

    response = _upload(
        client,
        analysis_id,
        "intruder@kau.edu.sa",
        "exam",
        "exam.pdf",
        valid_pdf_bytes(),
        "application/pdf",
    )

    assert response.status_code == 404


def test_upload_wrong_extension_returns_422(client: TestClient) -> None:
    analysis_id = _create_analysis(client, "u2@kau.edu.sa")

    response = _upload(
        client,
        analysis_id,
        "u2@kau.edu.sa",
        "exam",
        "exam.txt",
        valid_pdf_bytes(),
        "application/pdf",
    )

    assert response.status_code == 422


def test_upload_wrong_declared_mime_returns_422(client: TestClient) -> None:
    analysis_id = _create_analysis(client, "u3@kau.edu.sa")

    response = _upload(
        client, analysis_id, "u3@kau.edu.sa", "exam", "exam.pdf", valid_pdf_bytes(), "text/plain"
    )

    assert response.status_code == 422


def test_upload_bad_magic_bytes_returns_422(client: TestClient) -> None:
    analysis_id = _create_analysis(client, "u4@kau.edu.sa")

    response = _upload(
        client, analysis_id, "u4@kau.edu.sa", "exam", "exam.pdf", non_pdf_bytes(), "application/pdf"
    )

    assert response.status_code == 422


def test_upload_missing_eof_trailer_returns_422(client: TestClient) -> None:
    analysis_id = _create_analysis(client, "u5@kau.edu.sa")

    response = _upload(
        client,
        analysis_id,
        "u5@kau.edu.sa",
        "exam",
        "exam.pdf",
        truncated_pdf_bytes(),
        "application/pdf",
    )

    assert response.status_code == 422


@pytest.mark.parametrize("file_type", ["exam", "tp153"])
def test_upload_corrupted_pdf_is_rejected_for_both_slots_without_file_or_record(
    client: TestClient,
    db_engine: Engine,
    upload_root: Path,
    file_type: str,
) -> None:
    email = f"corrupted-{file_type}@kau.edu.sa"
    analysis_id = _create_analysis(client, email)

    response = _upload(
        client,
        analysis_id,
        email,
        file_type,
        f"{file_type}.pdf",
        corrupted_pdf_bytes(),
        "application/pdf",
    )

    assert response.status_code == 422
    assert response.json()["detail"] == PDF_READABILITY_ERROR
    assert list(upload_root.rglob("*")) == []

    with Session(db_engine) as session:
        records = (
            session.execute(
                select(UploadedFile).where(UploadedFile.analysis_id == UUID(analysis_id))
            )
            .scalars()
            .all()
        )
        assert records == []


def test_upload_inaccessible_encrypted_pdf_returns_422(client: TestClient) -> None:
    email = "encrypted@kau.edu.sa"
    analysis_id = _create_analysis(client, email)

    response = _upload(
        client,
        analysis_id,
        email,
        "exam",
        "exam.pdf",
        encrypted_pdf_bytes(),
        "application/pdf",
    )

    assert response.status_code == 422
    assert response.json()["detail"] == PDF_READABILITY_ERROR
    assert "password" not in response.text.lower()


def test_upload_at_size_limit_succeeds(client: TestClient, test_settings: Settings) -> None:
    analysis_id = _create_analysis(client, "u6@kau.edu.sa")
    limit_bytes = test_settings.max_upload_mb * 1024 * 1024

    response = _upload(
        client,
        analysis_id,
        "u6@kau.edu.sa",
        "exam",
        "exam.pdf",
        pdf_bytes_of_size(limit_bytes),
        "application/pdf",
    )

    assert response.status_code == 201


def test_upload_over_size_limit_returns_413(client: TestClient, test_settings: Settings) -> None:
    analysis_id = _create_analysis(client, "u7@kau.edu.sa")
    limit_bytes = test_settings.max_upload_mb * 1024 * 1024

    response = _upload(
        client,
        analysis_id,
        "u7@kau.edu.sa",
        "exam",
        "exam.pdf",
        pdf_bytes_of_size(limit_bytes + 1),
        "application/pdf",
    )

    assert response.status_code == 413


def test_upload_invalid_file_type_returns_422(client: TestClient) -> None:
    analysis_id = _create_analysis(client, "u8@kau.edu.sa")

    response = _upload(
        client,
        analysis_id,
        "u8@kau.edu.sa",
        "syllabus",
        "exam.pdf",
        valid_pdf_bytes(),
        "application/pdf",
    )

    assert response.status_code == 422


def test_upload_duplicate_file_type_returns_409(client: TestClient) -> None:
    analysis_id = _create_analysis(client, "u9@kau.edu.sa")
    first = _upload(
        client,
        analysis_id,
        "u9@kau.edu.sa",
        "exam",
        "exam.pdf",
        valid_pdf_bytes(),
        "application/pdf",
    )
    assert first.status_code == 201

    second = _upload(
        client,
        analysis_id,
        "u9@kau.edu.sa",
        "exam",
        "exam-v2.pdf",
        valid_pdf_bytes(),
        "application/pdf",
    )

    assert second.status_code == 409


def test_upload_same_bytes_as_different_file_types_both_succeed(client: TestClient) -> None:
    analysis_id = _create_analysis(client, "u10@kau.edu.sa")
    content = valid_pdf_bytes()

    exam_resp = _upload(
        client, analysis_id, "u10@kau.edu.sa", "exam", "exam.pdf", content, "application/pdf"
    )
    tp153_resp = _upload(
        client, analysis_id, "u10@kau.edu.sa", "tp153", "tp153.pdf", content, "application/pdf"
    )

    assert exam_resp.status_code == 201
    assert tp153_resp.status_code == 201
    assert exam_resp.json()["sha256_hash"] == tp153_resp.json()["sha256_hash"]


def test_dual_file_state_transitions_to_ready(client: TestClient) -> None:
    analysis_id = _create_analysis(client, "u11@kau.edu.sa")
    headers = auth_header("u11@kau.edu.sa")

    initial = client.get(f"/api/v1/analyses/{analysis_id}", headers=headers).json()
    assert initial["ready_for_analysis"] is False

    _upload(
        client,
        analysis_id,
        "u11@kau.edu.sa",
        "exam",
        "exam.pdf",
        valid_pdf_bytes(),
        "application/pdf",
    )
    after_exam = client.get(f"/api/v1/analyses/{analysis_id}", headers=headers).json()
    assert after_exam["exam_uploaded"] is True
    assert after_exam["tp153_uploaded"] is False
    assert after_exam["ready_for_analysis"] is False

    _upload(
        client,
        analysis_id,
        "u11@kau.edu.sa",
        "tp153",
        "tp153.pdf",
        valid_pdf_bytes(),
        "application/pdf",
    )
    after_both = client.get(f"/api/v1/analyses/{analysis_id}", headers=headers).json()
    assert after_both["exam_uploaded"] is True
    assert after_both["tp153_uploaded"] is True
    assert after_both["ready_for_analysis"] is True
    assert len(after_both["uploaded_files"]) == 2


def test_path_traversal_filename_does_not_escape_upload_root(
    client: TestClient, upload_root: Path
) -> None:
    analysis_id = _create_analysis(client, "u13@kau.edu.sa")
    malicious_name = "../../../../evil.pdf"

    response = _upload(
        client,
        analysis_id,
        "u13@kau.edu.sa",
        "exam",
        malicious_name,
        valid_pdf_bytes(),
        "application/pdf",
    )

    assert response.status_code == 201
    escaped = upload_root.parent.parent.parent / "evil.pdf"
    assert not escaped.exists()
    stored_files = list(upload_root.rglob("*.pdf"))
    assert len(stored_files) == 1
