from __future__ import annotations

import io
import uuid

import pytest
from fastapi.testclient import TestClient
from helpers import auth_header
from pdf_fixtures import build_synthetic_exam_pdf
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from tp153_pdf_fixtures import build_complete_tp153_pdf

import app.services.processing.stages as stages
from app.core.config import Settings
from app.core.domain import ProcessingStage
from app.models.analysis import Analysis
from app.models.evidence import Evidence
from app.models.extraction_review_revision import ExtractionReviewRevision
from app.models.finding import Finding
from app.models.processing_event import ProcessingEvent
from app.models.report import Report

ANALYSIS_PAYLOAD = {
    "course": {"code": "CPIT-450", "name": "Software Engineering"},
    "exam_type": "Midterm",
    "term": "2026 Spring",
}


def _ready_analysis(client: TestClient, email: str) -> str:
    created = client.post(
        "/api/v1/analyses",
        json=ANALYSIS_PAYLOAD,
        headers=auth_header(email),
    )
    assert created.status_code == 201
    analysis_id: str = created.json()["id"]
    for file_type, content in (
        ("exam", build_synthetic_exam_pdf()),
        ("tp153", build_complete_tp153_pdf()),
    ):
        uploaded = client.post(
            f"/api/v1/analyses/{analysis_id}/files",
            headers=auth_header(email),
            data={"file_type": file_type},
            files={"file": (f"{file_type}.pdf", io.BytesIO(content), "application/pdf")},
        )
        assert uploaded.status_code == 201
    return analysis_id


def test_initial_pipeline_pauses_without_post_confirmation_work(
    client: TestClient,
    db_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("A post-confirmation stage ran before confirmation.")

    for stage in stages.POST_CONFIRMATION_STAGES:
        monkeypatch.setitem(stages.STAGE_HANDLERS, stage, forbidden)

    email = "m3-pause@example.test"
    analysis_id = _ready_analysis(client, email)
    response = client.post(
        f"/api/v1/analyses/{analysis_id}/run",
        headers=auth_header(email),
    )

    assert response.status_code == 202
    progress = client.get(
        f"/api/v1/analyses/{analysis_id}/progress",
        headers=auth_header(email),
    )
    assert progress.json()["state"] == "review_ready"

    with Session(db_engine) as session:
        analysis_uuid = uuid.UUID(analysis_id)
        analysis = session.get(Analysis, analysis_uuid)
        assert analysis is not None
        assert analysis.confirmed_review_id is None
        assert (
            session.scalar(
                select(func.count())
                .select_from(ExtractionReviewRevision)
                .where(ExtractionReviewRevision.analysis_id == analysis_uuid)
            )
            == 1
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(ProcessingEvent)
                .where(
                    ProcessingEvent.analysis_id == analysis_uuid,
                    ProcessingEvent.stage == ProcessingStage.REVIEW_READY,
                )
            )
            == 1
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(Evidence)
                .where(
                    Evidence.analysis_id == analysis_uuid,
                    Evidence.evidence_type == "missing_semantic_input",
                )
            )
            == 0
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(Finding)
                .where(Finding.analysis_id == analysis_uuid)
            )
            == 0
        )
        assert (
            session.scalar(
                select(func.count()).select_from(Report).where(Report.analysis_id == analysis_uuid)
            )
            == 0
        )

    score = client.get(
        f"/api/v1/analyses/{analysis_id}/score",
        headers=auth_header(email),
    )
    assert score.status_code == 200
    assert score.json()["score"] is None
    assert score.json()["label"] == "Insufficient Evidence"

    report = client.post(
        f"/api/v1/analyses/{analysis_id}/reports",
        headers=auth_header(email),
    )
    assert report.status_code == 409


@pytest.mark.parametrize(
    "handler",
    [
        stages.run_building_evidence,
        stages.run_retrieving_knowledge,
        stages.run_applying_rules,
        stages.run_generating_report,
    ],
)
def test_central_guard_rejects_every_post_confirmation_handler(
    client: TestClient,
    db_engine: Engine,
    test_settings: Settings,
    handler: object,
) -> None:
    email = "m3-guard@example.test"
    analysis_id = _ready_analysis(client, email)
    client.post(
        f"/api/v1/analyses/{analysis_id}/run",
        headers=auth_header(email),
    )

    with Session(db_engine) as session:
        analysis = session.get(Analysis, uuid.UUID(analysis_id))
        assert analysis is not None
        with pytest.raises(stages.ReviewConfirmationRequiredError):
            handler(analysis, session, test_settings)  # type: ignore[operator]
