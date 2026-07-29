from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from helpers import auth_header
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.domain import (
    AssociationBasis,
    ReferenceResolutionStatus,
    ReferenceTargetType,
    SupportingAnnotationType,
    SupportingMaterialType,
    UploadedFileType,
)
from app.models.document_reference import DocumentReference
from app.models.extraction_review_revision import ExtractionReviewRevision
from app.models.reference_association import ReferenceAssociation
from app.models.supporting_material import SupportingMaterial
from app.models.supporting_material_annotation import SupportingMaterialAnnotation

ANALYSIS_PAYLOAD = {
    "course": {"code": "B4-API", "name": "Structured Evidence API"},
    "exam_type": "Midterm",
    "term": "2026",
}


def _create_analysis(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/analyses",
        json=ANALYSIS_PAYLOAD,
        headers=auth_header(email),
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def _insert_structured_records(db_engine: Engine, analysis_id: str) -> None:
    with Session(db_engine) as session:
        material = SupportingMaterial(
            analysis_id=uuid.UUID(analysis_id),
            source_document=UploadedFileType.EXAM,
            material_type=SupportingMaterialType.FIGURE,
            page_number=2,
            source_text="",
            geometry={"x0": 10, "top": 20, "x1": 200, "bottom": 180},
            confidence=0.94,
            extraction_method="direct_text",
        )
        session.add(material)
        session.flush()
        annotation = SupportingMaterialAnnotation(
            analysis_id=uuid.UUID(analysis_id),
            material_id=material.id,
            source_document=UploadedFileType.EXAM,
            annotation_type=SupportingAnnotationType.CAPTION,
            original_text="Figure 1: Architecture ةرامعلا:1 لكشلا",
            normalized_label="figure:1",
            page_number=2,
            geometry={"x0": 10, "top": 181, "x1": 200, "bottom": 195},
            confidence=0.93,
            extraction_method="direct_text",
        )
        reference = DocumentReference(
            analysis_id=uuid.UUID(analysis_id),
            source_document=UploadedFileType.EXAM,
            target_type=ReferenceTargetType.FIGURE,
            original_text="Figure 1",
            target_label="Figure 1",
            normalized_target_label="figure:1",
            page_number=1,
            geometry={"x0": 10, "top": 20, "x1": 100, "bottom": 30},
            confidence=0.96,
            extraction_method="direct_text",
            machine_resolution_status=ReferenceResolutionStatus.RESOLVED,
        )
        session.add_all([annotation, reference])
        session.flush()
        session.add(
            ReferenceAssociation(
                reference_id=reference.id,
                target_material_id=material.id,
                basis=AssociationBasis.EXACT_LABEL,
                confidence=0.93,
                exact_label_match=True,
                selected=True,
            )
        )
        session.commit()


def test_historical_analysis_endpoints_return_empty_structured_collections(
    client: TestClient,
) -> None:
    email = "batch4-empty@example.test"
    analysis_id = _create_analysis(client, email)
    for suffix in (
        "supporting-materials",
        "supporting-material-annotations",
        "document-references",
    ):
        response = client.get(
            f"/api/v1/analyses/{analysis_id}/{suffix}",
            headers=auth_header(email),
        )
        assert response.status_code == 200
        assert response.json() == []


def test_structured_endpoints_preserve_provenance_and_candidates(
    client: TestClient,
    db_engine: Engine,
) -> None:
    email = "batch4-owner@example.test"
    analysis_id = _create_analysis(client, email)
    _insert_structured_records(db_engine, analysis_id)

    materials = client.get(
        f"/api/v1/analyses/{analysis_id}/supporting-materials",
        headers=auth_header(email),
    )
    annotations = client.get(
        f"/api/v1/analyses/{analysis_id}/supporting-material-annotations",
        headers=auth_header(email),
    )
    references = client.get(
        f"/api/v1/analyses/{analysis_id}/document-references",
        headers=auth_header(email),
    )

    assert materials.status_code == annotations.status_code == references.status_code == 200
    assert materials.json()[0]["geometry"] == {
        "x0": 10,
        "top": 20,
        "x1": 200,
        "bottom": 180,
    }
    assert annotations.json()[0]["original_text"] == "الشكل 1: Architecture"
    with Session(db_engine) as session:
        persisted = session.get(
            SupportingMaterialAnnotation,
            uuid.UUID(annotations.json()[0]["id"]),
        )
        assert persisted is not None
        assert persisted.original_text == "Figure 1: Architecture ةرامعلا:1 لكشلا"
    reference = references.json()[0]
    assert reference["original_text"] == "Figure 1"
    assert reference["normalized_target_label"] == "figure:1"
    assert reference["resolution_status"] == "resolved"
    assert reference["association_candidates"][0]["basis"] == "exact_label"
    assert reference["association_candidates"][0]["selected"] is True


def test_document_reference_endpoint_exposes_only_active_revision_candidates(
    client: TestClient,
    db_engine: Engine,
) -> None:
    email = "batch4-active-candidates@example.test"
    analysis_id = _create_analysis(client, email)
    _insert_structured_records(db_engine, analysis_id)

    with Session(db_engine) as session:
        analysis_uuid = uuid.UUID(analysis_id)
        reference = session.query(DocumentReference).filter_by(
            analysis_id=analysis_uuid
        ).one()
        material = session.query(SupportingMaterial).filter_by(
            analysis_id=analysis_uuid
        ).one()
        revision = ExtractionReviewRevision(
            analysis_id=analysis_uuid,
            revision_number=1,
            snapshot={
                "schema_version": 1,
                "questions": [],
                "evidence": [],
                "clos": [],
                "topics": [],
                "assessment_records": [],
                "supporting_materials": [],
                "supporting_annotations": [],
                "document_references": [],
                "reference_associations": [],
            },
        )
        session.add(revision)
        session.flush()
        session.add(
            ReferenceAssociation(
                reference_id=reference.id,
                target_material_id=material.id,
                review_revision_id=revision.id,
                basis=AssociationBasis.EXACT_LABEL,
                confidence=0.93,
                exact_label_match=True,
                selected=True,
            )
        )
        analysis = reference.analysis
        analysis.confirmed_review_id = revision.id
        session.commit()

    response = client.get(
        f"/api/v1/analyses/{analysis_id}/document-references",
        headers=auth_header(email),
    )

    assert response.status_code == 200
    reference = response.json()[0]
    assert reference["resolution_status"] == "resolved"
    assert len(reference["association_candidates"]) == 1
    assert reference["association_candidates"][0]["review_revision_id"] is not None


def test_structured_endpoints_are_owner_scoped(
    client: TestClient,
    db_engine: Engine,
) -> None:
    analysis_id = _create_analysis(client, "batch4-real-owner@example.test")
    _insert_structured_records(db_engine, analysis_id)

    for suffix in (
        "supporting-materials",
        "supporting-material-annotations",
        "document-references",
    ):
        response = client.get(
            f"/api/v1/analyses/{analysis_id}/{suffix}",
            headers=auth_header("batch4-intruder@example.test"),
        )
        assert response.status_code == 404
