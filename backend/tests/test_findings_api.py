from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from helpers import auth_header
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.domain import AcademicStatus, UploadedFileType
from app.models.evidence import Evidence
from app.models.finding import Finding, FindingEvidence

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


def _insert_findings(db_engine: Engine, analysis_id: str) -> None:
    with Session(db_engine) as session:
        ev = Evidence(
            analysis_id=uuid.UUID(analysis_id),
            source_document=UploadedFileType.EXAM,
            evidence_type="question_text",
            page_number=1,
            item_reference="Q1",
            extracted_text="Q1. Explain the concept. [5 marks]",
            confidence=1.0,
        )
        session.add(ev)
        session.flush()

        # created_at is set explicitly (rather than left to the real-clock
        # default) so primary sort order is unambiguous regardless of flush
        # timing - marks_finding is deliberately earlier than numbering_finding.
        base_time = datetime.now(UTC)
        marks_finding = Finding(
            analysis_id=uuid.UUID(analysis_id),
            requirement_id="REQ018",
            rule_id="RULE018",
            status=AcademicStatus.NOT_APPLICABLE,
            explanation="No declared total marks were found in the exam.",
            confidence=1.0,
            evaluator_type="deterministic_rule",
            created_at=base_time,
        )
        numbering_finding = Finding(
            analysis_id=uuid.UUID(analysis_id),
            requirement_id="REQ019",
            rule_id="RULE019",
            status=AcademicStatus.SATISFIED,
            explanation="Question numbering is unique and consistent.",
            confidence=1.0,
            evaluator_type="deterministic_rule",
            created_at=base_time + timedelta(seconds=1),
        )
        session.add_all([numbering_finding, marks_finding])
        session.flush()

        session.add(FindingEvidence(finding_id=numbering_finding.id, evidence_id=ev.id))
        session.commit()


def test_findings_returns_404_for_non_owner(client: TestClient, db_engine: Engine) -> None:
    analysis_id = _create_analysis(client, "finding-owner@kau.edu.sa")
    _insert_findings(db_engine, analysis_id)
    response = client.get(
        f"/api/v1/analyses/{analysis_id}/findings",
        headers=auth_header("finding-intruder@kau.edu.sa"),
    )
    assert response.status_code == 404


def test_findings_returns_404_for_unknown_analysis(client: TestClient) -> None:
    response = client.get(
        f"/api/v1/analyses/{uuid.uuid4()}/findings", headers=auth_header("someone@kau.edu.sa")
    )
    assert response.status_code == 404


def test_findings_missing_auth_header_returns_401(client: TestClient) -> None:
    analysis_id = _create_analysis(client, "finding-auth@kau.edu.sa")
    response = client.get(f"/api/v1/analyses/{analysis_id}/findings")
    assert response.status_code == 401


def test_findings_returned_in_deterministic_order(client: TestClient, db_engine: Engine) -> None:
    email = "finding-order@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _insert_findings(db_engine, analysis_id)

    response = client.get(f"/api/v1/analyses/{analysis_id}/findings", headers=auth_header(email))
    assert response.status_code == 200
    body = response.json()
    assert [f["rule_id"] for f in body] == ["RULE018", "RULE019"]


def test_findings_response_schema_fields(client: TestClient, db_engine: Engine) -> None:
    email = "finding-schema@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    _insert_findings(db_engine, analysis_id)

    response = client.get(f"/api/v1/analyses/{analysis_id}/findings", headers=auth_header(email))
    body = response.json()
    numbering = next(f for f in body if f["rule_id"] == "RULE019")

    assert numbering["analysis_id"] == analysis_id
    assert numbering["requirement_id"] == "REQ019"
    assert numbering["status"] == "Satisfied"
    assert numbering["explanation"] == "Question numbering is unique and consistent."
    assert numbering["confidence"] == 1.0
    assert numbering["evaluator_type"] == "deterministic_rule"
    assert "id" in numbering
    assert "created_at" in numbering
    # No aggregate analysis score field anywhere in a finding row.
    assert "score" not in numbering

    assert len(numbering["evidence"]) == 1
    ev = numbering["evidence"][0]
    assert ev["source_document"] == "exam"
    assert ev["evidence_type"] == "question_text"
    assert ev["page_number"] == 1
    assert ev["item_reference"] == "Q1"

    marks = next(f for f in body if f["rule_id"] == "RULE018")
    assert marks["status"] == "Not Applicable"
    assert marks["evidence"] == []


def test_findings_empty_list_when_rules_not_run_yet(client: TestClient) -> None:
    email = "finding-empty@kau.edu.sa"
    analysis_id = _create_analysis(client, email)
    response = client.get(f"/api/v1/analyses/{analysis_id}/findings", headers=auth_header(email))
    assert response.status_code == 200
    assert response.json() == []
