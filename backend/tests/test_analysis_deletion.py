from __future__ import annotations

import io
import uuid
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from helpers import auth_header, valid_pdf_bytes
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.domain import ProcessingStage, ReportFormat, ReportLanguage
from app.models.analysis import Analysis
from app.models.extraction_review_revision import ExtractionReviewRevision
from app.models.report import Report

PAYLOAD = {
    "course": {"code": "DEL-101", "name": "Deletion Safety"},
    "exam_type": "Final",
    "term": "2026",
}


def _create(client: TestClient, email: str) -> str:
    response = client.post("/api/v1/analyses", json=PAYLOAD, headers=auth_header(email))
    assert response.status_code == 201
    return str(response.json()["id"])


def _upload_exam(client: TestClient, analysis_id: str, email: str) -> None:
    response = client.post(
        f"/api/v1/analyses/{analysis_id}/files",
        headers=auth_header(email),
        data={"file_type": "exam"},
        files={"file": ("exam.pdf", io.BytesIO(valid_pdf_bytes()), "application/pdf")},
    )
    assert response.status_code == 201


def test_owner_can_delete_queued_analysis_and_uploaded_artifact(
    client: TestClient,
    upload_root: Path,
) -> None:
    email = "delete-owner@example.edu"
    analysis_id = _create(client, email)
    _upload_exam(client, analysis_id, email)
    artifacts = list(upload_root.rglob("*.pdf"))
    assert len(artifacts) == 1
    cache_path = artifacts[0].with_name(f".{artifacts[0].name}.gemini-structure-cache.json")
    cache_path.write_text('{"cache_key":"test","output":{}}', encoding="utf-8")

    response = client.delete(f"/api/v1/analyses/{analysis_id}", headers=auth_header(email))

    assert response.status_code == 204
    assert not artifacts[0].exists()
    assert not cache_path.exists()
    assert (
        client.get(f"/api/v1/analyses/{analysis_id}", headers=auth_header(email)).status_code == 404
    )


def test_non_owner_delete_is_private_404(client: TestClient) -> None:
    analysis_id = _create(client, "owner-delete@example.edu")
    response = client.delete(
        f"/api/v1/analyses/{analysis_id}",
        headers=auth_header("not-owner-delete@example.edu"),
    )
    assert response.status_code == 404


def test_exam_preview_is_owner_authorized_and_never_exposes_storage_path(
    client: TestClient,
) -> None:
    email = "preview-owner@example.edu"
    analysis_id = _create(client, email)
    _upload_exam(client, analysis_id, email)

    owner = client.get(
        f"/api/v1/analyses/{analysis_id}/files/exam/content",
        headers=auth_header(email),
    )
    assert owner.status_code == 200
    assert owner.headers["content-type"].startswith("application/pdf")
    assert owner.headers["cache-control"] == "private, no-store"
    assert "storage" not in owner.headers.get("content-disposition", "").casefold()
    assert (
        client.get(
            f"/api/v1/analyses/{analysis_id}/files/exam/content",
            headers=auth_header("preview-intruder@example.edu"),
        ).status_code
        == 404
    )


@pytest.mark.parametrize(
    "active_state",
    [
        ProcessingStage.VALIDATING,
        ProcessingStage.EXTRACTING_EXAM,
        ProcessingStage.EXTRACTING_TP153,
        ProcessingStage.BUILDING_EVIDENCE,
        ProcessingStage.RETRIEVING_KNOWLEDGE,
        ProcessingStage.APPLYING_RULES,
        ProcessingStage.GENERATING_REPORT,
    ],
)
def test_active_analysis_deletion_returns_409(
    client: TestClient,
    db_engine: Engine,
    active_state: ProcessingStage,
) -> None:
    email = f"active-{active_state.value}@example.edu"
    analysis_id = uuid.UUID(_create(client, email))
    with Session(db_engine) as session:
        analysis = session.get(Analysis, analysis_id)
        assert analysis is not None
        analysis.state = active_state
        session.commit()

    response = client.delete(f"/api/v1/analyses/{analysis_id}", headers=auth_header(email))
    assert response.status_code == 409
    with Session(db_engine) as session:
        assert session.get(Analysis, analysis_id) is not None


@pytest.mark.parametrize(
    "safe_state",
    [ProcessingStage.REVIEW_READY, ProcessingStage.COMPLETED, ProcessingStage.FAILED],
)
def test_safe_terminal_analysis_states_can_be_deleted(
    client: TestClient,
    db_engine: Engine,
    safe_state: ProcessingStage,
) -> None:
    email = f"safe-{safe_state.value}@example.edu"
    analysis_id = uuid.UUID(_create(client, email))
    with Session(db_engine) as session:
        analysis = session.get(Analysis, analysis_id)
        assert analysis is not None
        analysis.state = safe_state
        session.commit()
    assert (
        client.delete(f"/api/v1/analyses/{analysis_id}", headers=auth_header(email)).status_code
        == 204
    )


def test_confirmed_review_and_report_are_deleted_without_circular_fk_failure(
    client: TestClient,
    db_engine: Engine,
    report_root: Path,
) -> None:
    email = "confirmed-delete@example.edu"
    analysis_id = uuid.UUID(_create(client, email))
    report_path: Path
    with Session(db_engine) as session:
        analysis = session.get(Analysis, analysis_id)
        assert analysis is not None
        revision = ExtractionReviewRevision(
            analysis_id=analysis.id,
            revision_number=1,
            snapshot={
                "schema_version": 1,
                "questions": [],
                "evidence": [],
                "clos": [],
                "topics": [],
                "assessment_records": [],
            },
        )
        session.add(revision)
        session.flush()
        analysis.confirmed_review_id = revision.id
        analysis.state = ProcessingStage.COMPLETED
        report_id = uuid.uuid4()
        storage_key = f"{analysis.id}/{report_id}.pdf"
        report_path = report_root / storage_key
        report_path.parent.mkdir(parents=True)
        report_path.write_bytes(b"report")
        session.add(
            Report(
                id=report_id,
                analysis_id=analysis.id,
                format=ReportFormat.PDF,
                language=ReportLanguage.ENGLISH,
                storage_key=storage_key,
                size_bytes=6,
                sha256_hash="a" * 64,
                kb_version="test",
                score=Decimal("100.00"),
                score_label="Excellent",
                denominator=1,
                satisfied_count=1,
                partially_satisfied_count=0,
                not_satisfied_count=0,
                not_verified_count=0,
                not_applicable_count=0,
            )
        )
        session.commit()

    response = client.delete(f"/api/v1/analyses/{analysis_id}", headers=auth_header(email))
    assert response.status_code == 204
    assert not report_path.exists()


def test_predecessor_reference_restricts_delete_and_missing_file_is_harmless(
    client: TestClient,
    db_engine: Engine,
) -> None:
    email = "history-delete@example.edu"
    predecessor_id = uuid.UUID(_create(client, email))
    successor_id = uuid.UUID(_create(client, email))
    with Session(db_engine) as session:
        successor = session.get(Analysis, successor_id)
        assert successor is not None
        successor.predecessor_analysis_id = predecessor_id
        session.commit()

    blocked = client.delete(f"/api/v1/analyses/{predecessor_id}", headers=auth_header(email))
    assert blocked.status_code == 409

    # No uploaded/report artifact exists for the successor; cleanup remains successful.
    deleted = client.delete(f"/api/v1/analyses/{successor_id}", headers=auth_header(email))
    assert deleted.status_code == 204
