from __future__ import annotations

import hashlib
import io
import time
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from helpers import auth_header
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.domain import (
    AcademicStatus,
    AssociationBasis,
    ExamType,
    ProcessingStage,
    ReferenceResolutionStatus,
    SupportingMaterialType,
)
from app.models.analysis import Analysis
from app.models.course import Course
from app.models.document_reference import DocumentReference
from app.models.evidence import Evidence
from app.models.reference_association import ReferenceAssociation
from app.models.supporting_material_annotation import SupportingMaterialAnnotation
from app.models.user import User
from app.services.extraction.digital_pdf_extractor import PdfPlumberExamExtractor
from app.services.extraction.digital_tp153_extractor import PdfPlumberTp153Extractor
from app.services.extraction.line_classification import parse_declared_total
from app.services.extraction.persistence import persist_extraction_result
from app.services.extraction.review_snapshot import materialize_initial_review_revision
from app.services.extraction.review_workflow import (
    append_extraction_review_revision,
    confirm_extraction_review,
    get_extraction_review,
)
from app.services.extraction.structured_evidence import logical_annotation_text
from app.services.extraction.tp153_persistence import persist_tp153_extraction_result
from app.services.rules.marks_total import evaluate_marks_and_total
from app.services.rules.structured_evidence import (
    evaluate_referenced_material_availability,
    evaluate_resolvable_cross_references,
    evaluate_supporting_material_association,
)
from app.services.rules.versioning import CURRENT_CAPABILITY_VERSION

FIXTURES = Path(__file__).parent / "fixtures" / "batch4"
EXAM = FIXTURES / "01_Batch4_Test_Exam.pdf"
SPECIFICATION = FIXTURES / "02_Batch4_Mixed_Course_Specification.pdf"
EXPECTED_HASHES = {
    EXAM.name: "8442dbd868d7261e4d8fd5eaec4002c7c0876cb672cac153c3e3e1f6758df956",
    SPECIFICATION.name: "c1fa24f887ac62424ebc69d21fb076218296742e0ada88ad248b3efd0d2c2f0f",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _analysis(session: Session) -> Analysis:
    suffix = uuid.uuid4().hex
    user = User(email=f"batch4-acceptance-{suffix}@example.test", display_name="Batch 4")
    course = Course(code=f"B4A-{suffix[:8]}", name="Batch 4 Acceptance")
    session.add_all([user, course])
    session.flush()
    analysis = Analysis(
        user_id=user.id,
        course_id=course.id,
        exam_type=ExamType.FINAL,
        term="Batch 4 fixture",
        capability_version="v2-b4-structured-evidence",
    )
    session.add(analysis)
    session.flush()
    return analysis


def _wait_for_state(
    client: TestClient,
    analysis_id: str,
    email: str,
    expected: set[str],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for _ in range(100):
        response = client.get(
            f"/api/v1/analyses/{analysis_id}/progress",
            headers=auth_header(email),
        )
        assert response.status_code == 200
        result = response.json()
        if result["state"] in expected:
            return result
        time.sleep(0.025)
    raise AssertionError(f"Analysis did not reach one of {expected}: {result}")


def test_batch4_acceptance_fixture_checksums_are_pinned() -> None:
    assert {_path.name: _sha256(_path) for _path in (EXAM, SPECIFICATION)} == EXPECTED_HASHES


def test_exact_fixtures_complete_the_public_api_workflow_and_bilingual_reports(
    client: TestClient,
    test_settings: Settings,
) -> None:
    test_settings.ai_provider = "local"
    test_settings.ai_model = "local-governed-baseline-v1"
    email = "pilot-fixture-owner@example.test"
    created = client.post(
        "/api/v1/analyses",
        headers=auth_header(email),
        json={
            "course": {"code": "CS 241", "name": "Database Systems"},
            "exam_type": "Final",
            "term": "1448",
        },
    )
    assert created.status_code == 201, created.text
    analysis_id = created.json()["id"]
    assert created.json()["capability_version"] == CURRENT_CAPABILITY_VERSION

    for file_type, fixture in (("exam", EXAM), ("tp153", SPECIFICATION)):
        uploaded = client.post(
            f"/api/v1/analyses/{analysis_id}/files",
            headers=auth_header(email),
            data={"file_type": file_type},
            files={
                "file": (
                    fixture.name,
                    io.BytesIO(fixture.read_bytes()),
                    "application/pdf",
                )
            },
        )
        assert uploaded.status_code == 201, uploaded.text

    started = client.post(
        f"/api/v1/analyses/{analysis_id}/run",
        headers=auth_header(email),
    )
    assert started.status_code == 202, started.text
    paused = _wait_for_state(client, analysis_id, email, {"review_ready", "failed"})
    assert paused["state"] == "review_ready", paused

    review_response = client.get(
        f"/api/v1/analyses/{analysis_id}/extraction-review",
        headers=auth_header(email),
    )
    assert review_response.status_code == 200
    review = review_response.json()
    snapshot = review["snapshot"]
    main_questions = [
        item for item in snapshot["questions"] if item["parent_source_record_id"] is None
    ]
    assert len(main_questions) == 7
    assert len(snapshot["supporting_materials"]) == 6
    assert len(snapshot["supporting_annotations"]) == 10
    assert len(snapshot["document_references"]) == 6
    declared = [
        item for item in snapshot["evidence"] if item["evidence_type"] == "declared_total"
    ]
    assert len(declared) == 1
    assert parse_declared_total(declared[0]["extracted_text"]) == 40

    confirmed = client.post(
        f"/api/v1/analyses/{analysis_id}/extraction-review/confirm",
        headers=auth_header(email),
        json={"revision_id": review["revision_id"]},
    )
    assert confirmed.status_code == 202, confirmed.text
    completed = _wait_for_state(client, analysis_id, email, {"completed", "failed"})
    assert completed["state"] == "completed", completed

    findings_response = client.get(
        f"/api/v1/analyses/{analysis_id}/findings",
        headers=auth_header(email),
    )
    assert findings_response.status_code == 200
    findings = {item["rule_id"]: item for item in findings_response.json()}
    assert findings["RULE018"]["status"] == "Satisfied"
    assert findings["RULE014"]["status"] == "Not Verified"
    assert "Figure 2" in findings["RULE014"]["explanation"]
    assert "الشكل 5" in findings["RULE014"]["explanation"]
    assert findings["RULE016"]["status"] == "Not Verified"
    assert findings["RULE022"]["status"] == "Not Verified"

    materials = client.get(
        f"/api/v1/analyses/{analysis_id}/supporting-materials",
        headers=auth_header(email),
    ).json()
    assert len(materials) == 6
    references = client.get(
        f"/api/v1/analyses/{analysis_id}/document-references",
        headers=auth_header(email),
    ).json()
    by_target = {item["normalized_target_label"]: item for item in references}
    assert by_target["figure:1"]["resolution_status"] == "resolved"
    assert len(by_target["figure:1"]["association_candidates"]) == 1
    assert by_target["table:1"]["resolution_status"] == "resolved"
    assert by_target["code_block:1"]["resolution_status"] == "resolved"
    assert by_target["figure:5"]["resolution_status"] == "unresolved"
    assert by_target["figure:5"]["association_candidates"] == []
    assert by_target["figure:2"]["resolution_status"] == "ambiguous"
    assert len(by_target["figure:2"]["association_candidates"]) == 2
    assert by_target["figure:unlabeled"]["resolution_status"] == "unresolved"
    assert len(by_target["figure:unlabeled"]["association_candidates"]) == 1
    assert not by_target["figure:unlabeled"]["association_candidates"][0]["selected"]

    for language in ("en", "ar"):
        generated = client.post(
            f"/api/v1/analyses/{analysis_id}/reports",
            headers=auth_header(email),
            json={"language": language},
        )
        assert generated.status_code == 201, generated.text
        assert generated.json()["language"] == language
        downloaded = client.get(
            f"/api/v1/reports/{generated.json()['id']}/download",
            headers=auth_header(email),
        )
        assert downloaded.status_code == 200
        assert downloaded.content.startswith(b"%PDF")

    denied = client.get(
        f"/api/v1/analyses/{analysis_id}/document-references",
        headers=auth_header("pilot-fixture-intruder@example.test"),
    )
    assert denied.status_code == 404


def test_exact_exam_fixture_extracts_hierarchy_marks_materials_and_references() -> None:
    result = PdfPlumberExamExtractor().extract(EXAM)
    by_label = {question.number_label: question for question in result.questions}

    assert [question.number_label for question in result.questions] == [
        "Q1",
        "Q1(a)",
        "Q1(b)",
        "Q2",
        "Q3",
        "Q4",
        "Q5",
        "Q6",
        "Q7",
    ]
    assert [label for label in by_label if "(" not in label] == [
        "Q1",
        "Q2",
        "Q3",
        "Q4",
        "Q5",
        "Q6",
        "Q7",
    ]
    assert by_label["Q1(a)"].parent_number_label == "Q1"
    assert by_label["Q1(b)"].parent_number_label == "Q1"
    assert [by_label[f"Q{number}"].page_number for number in range(1, 8)] == [
        1,
        2,
        3,
        3,
        4,
        5,
        6,
    ]
    assert [by_label[f"Q{number}"].marks for number in range(1, 8)] == [
        6,
        6,
        6,
        6,
        4,
        6,
        6,
    ]
    assert [by_label[label].marks for label in ("Q1(a)", "Q1(b)")] == [3, 3]
    assert "المفاهيم الأساسية" in by_label["Q1"].text
    assert "Using Table 1" in by_label["Q3"].text
    assert "add_student" in by_label["Q4"].text
    assert "Refer to Figure 2" in by_label["Q6"].text

    material_counts = {
        material_type: sum(
            item.material_type is material_type for item in result.supporting_materials
        )
        for material_type in SupportingMaterialType
    }
    assert material_counts == {
        SupportingMaterialType.FIGURE: 4,
        SupportingMaterialType.TABLE: 1,
        SupportingMaterialType.CODE_BLOCK: 1,
    }
    assert len(result.supporting_materials) == 6

    normalized_references = [
        reference.normalized_target_label for reference in result.document_references
    ]
    assert normalized_references[:5] == [
        "figure:1",
        "table:1",
        "code_block:1",
        "figure:5",
        "figure:2",
    ]
    assert any(
        reference.page_number == 6 and reference.normalized_target_label == "figure:unlabeled"
        for reference in result.document_references
    )

    declared_totals = [
        item for item in result.evidence if item.evidence_type == "declared_total"
    ]
    assert len(declared_totals) == 1
    assert declared_totals[0].page_number == 1
    assert declared_totals[0].geometry is not None
    assert parse_declared_total(declared_totals[0].extracted_text) == 40
    assert "1448" not in declared_totals[0].extracted_text
    assert "241" not in declared_totals[0].extracted_text


def test_exact_exam_fixture_calculates_forty_and_satisfies_correct_total_marks(
    db_engine: Engine,
) -> None:
    extracted = PdfPlumberExamExtractor().extract(EXAM)
    with Session(db_engine) as session:
        analysis = _analysis(session)
        persist_extraction_result(session, analysis.id, extracted)
        questions = list(analysis.questions)
        evidence = list(analysis.evidence)

        result = evaluate_marks_and_total(questions, evidence)

    assert sum(
        question.marks or 0
        for question in questions
        if question.number_label not in {"Q1"}
    ) == 40
    assert result.status.value == "Satisfied"
    assert "Calculated total marks (40" in result.explanation
    assert "declared total marks (40" in result.explanation


def test_exact_exam_fixture_preserves_raw_annotations_and_presents_logical_bidi_text() -> None:
    result = PdfPlumberExamExtractor().extract(EXAM)

    assert any("1 لكشلا" in item.original_text for item in result.supporting_annotations)
    presented = {
        logical_annotation_text(item.original_text, item.normalized_label)
        for item in result.supporting_annotations
    }
    assert {
        "الشكل 1: Relational Database Schema",
        "الجدول 1: Sample Student Scores",
        "الكود 1: Parameterized insert",
        "الشكل 2: Validation Flowchart",
        "الشكل 2: Network Structure",
    } <= presented
    assert (
        logical_annotation_text(
            "ةيقئالع تانايب ةدعاق ططخم:12 لكشلا",
            "figure:12",
        )
        == "الشكل 12: مخطط قاعدة بيانات علائقية"
    )


def test_exact_exam_fixture_review_saves_logical_text_without_mutating_raw_annotations(
    db_engine: Engine,
) -> None:
    extracted = PdfPlumberExamExtractor().extract(EXAM)
    with Session(db_engine) as session:
        analysis = _analysis(session)
        persist_extraction_result(session, analysis.id, extracted)
        initial = materialize_initial_review_revision(session, analysis.id)
        analysis.state = ProcessingStage.REVIEW_READY
        session.flush()

        review = get_extraction_review(session, analysis)
        raw_values = {
            item.original_text for item in review.original_snapshot.supporting_annotations
        }
        editable_values = {item.original_text for item in review.snapshot.supporting_annotations}
        assert any("1 لكشلا" in value for value in raw_values)
        assert "الشكل 1: Relational Database Schema" in editable_values

        saved = append_extraction_review_revision(
            session,
            analysis,
            base_revision_id=initial.id,
            candidate_snapshot=review.snapshot,
        )
        persisted_raw = {
            item.original_text
            for item in session.scalars(
                select(SupportingMaterialAnnotation).where(
                    SupportingMaterialAnnotation.analysis_id == analysis.id
                )
            )
        }

        assert saved.revision_number == 2
        assert "الشكل 1: Relational Database Schema" in {
            item.original_text for item in saved.snapshot.supporting_annotations
        }
        assert any("1 لكشلا" in value for value in persisted_raw)


def test_exact_exam_fixture_associations_follow_approved_policy(db_engine: Engine) -> None:
    extracted = PdfPlumberExamExtractor().extract(EXAM)
    with Session(db_engine) as session:
        analysis = _analysis(session)
        persist_extraction_result(session, analysis.id, extracted)
        references = list(
            session.scalars(
                select(DocumentReference)
                .where(DocumentReference.analysis_id == analysis.id)
                .order_by(DocumentReference.page_number, DocumentReference.normalized_target_label)
            )
        )
        by_target = {reference.normalized_target_label: reference for reference in references}
        assert by_target["figure:1"].machine_resolution_status is ReferenceResolutionStatus.RESOLVED
        assert by_target["table:1"].machine_resolution_status is ReferenceResolutionStatus.RESOLVED
        assert (
            by_target["code_block:1"].machine_resolution_status
            is ReferenceResolutionStatus.RESOLVED
        )
        assert (
            by_target["figure:5"].machine_resolution_status is ReferenceResolutionStatus.UNRESOLVED
        )
        assert (
            by_target["figure:2"].machine_resolution_status is ReferenceResolutionStatus.AMBIGUOUS
        )
        assert (
            by_target["figure:unlabeled"].machine_resolution_status
            is ReferenceResolutionStatus.UNRESOLVED
        )

        figure_two = list(
            session.scalars(
                select(ReferenceAssociation).where(
                    ReferenceAssociation.reference_id == by_target["figure:2"].id
                )
            )
        )
        assert len(figure_two) == 2
        assert all(item.basis is AssociationBasis.EXACT_LABEL for item in figure_two)
        assert not any(item.selected for item in figure_two)
        assert all(item.ambiguity_reason for item in figure_two)

        unlabeled = list(
            session.scalars(
                select(ReferenceAssociation).where(
                    ReferenceAssociation.reference_id == by_target["figure:unlabeled"].id
                )
            )
        )
        assert unlabeled
        assert all(item.basis is AssociationBasis.PROXIMITY_SUPPORT for item in unlabeled)
        assert not any(item.selected for item in unlabeled)


def test_exact_exam_fixture_findings_name_missing_and_ambiguous_references(
    db_engine: Engine,
) -> None:
    extracted = PdfPlumberExamExtractor().extract(EXAM)
    with Session(db_engine) as session:
        analysis = _analysis(session)
        persist_extraction_result(session, analysis.id, extracted)
        revision = materialize_initial_review_revision(session, analysis.id)
        analysis.state = ProcessingStage.REVIEW_READY
        session.flush()
        snapshot = get_extraction_review(session, analysis).snapshot
        confirmed = confirm_extraction_review(
            session,
            analysis,
            revision_id=revision.id,
        )

        availability = evaluate_referenced_material_availability(
            session,
            analysis_id=analysis.id,
            snapshot=snapshot,
            confirmed_revision_id=confirmed.revision_id,
        )
        association = evaluate_supporting_material_association(
            session,
            analysis_id=analysis.id,
            snapshot=snapshot,
            confirmed_revision_id=confirmed.revision_id,
        )
        cross_references = evaluate_resolvable_cross_references(
            session,
            analysis_id=analysis.id,
            snapshot=snapshot,
            confirmed_revision_id=confirmed.revision_id,
        )

    assert availability.status is AcademicStatus.NOT_VERIFIED
    assert "Figure 2" in availability.explanation
    assert "الشكل 5" in availability.explanation
    assert association.status is AcademicStatus.NOT_VERIFIED
    assert "Figure 2" in association.explanation
    assert cross_references.status is AcademicStatus.NOT_VERIFIED
    assert "Figure 2" in cross_references.explanation
    assert "الشكل 5" in cross_references.explanation
    assert "proximity alone" in cross_references.explanation


def test_exact_course_specification_fixture_extracts_only_genuine_records() -> None:
    result = PdfPlumberTp153Extractor().extract(SPECIFICATION)

    assert [item.code for item in result.clos] == ["CLO1", "CLO2", "CLO3", "CLO4"]
    assert len(result.topics) == 7
    assert [item.code for item in result.topics] == [None] * 7
    assert [item.expected_hours for item in result.topics] == [3, 6, 6, 6, 9, 6, 6]
    assert len(result.assessment_records) == 4
    assert [item.percentage for item in result.assessment_records] == [10, 20, 30, 40]
    assert result.missing_sections == []
    assert all(item.geometry is not None for item in result.clos)
    assert all(item.geometry is not None for item in result.topics)
    assert all(item.geometry is not None for item in result.assessment_records)
    assert len({item.geometry.top for item in result.clos if item.geometry is not None}) == 4
    assert len({item.geometry.top for item in result.topics if item.geometry is not None}) == 7
    assert (
        len({item.geometry.top for item in result.assessment_records if item.geometry is not None})
        == 4
    )
    assert all(item.source_text and "\n" in item.source_text for item in result.clos)
    assert all(item.extraction_method == "direct_text" for item in result.clos)


def test_exact_course_specification_fixture_persists_raw_rows_without_missing_markers(
    db_engine: Engine,
) -> None:
    extracted = PdfPlumberTp153Extractor().extract(SPECIFICATION)
    with Session(db_engine) as session:
        analysis = _analysis(session)
        persist_tp153_extraction_result(session, analysis.id, extracted)
        evidence = list(
            session.scalars(select(Evidence).where(Evidence.analysis_id == analysis.id))
        )

    by_type: dict[str, list[Evidence]] = {}
    for item in evidence:
        by_type.setdefault(item.evidence_type, []).append(item)
    assert "missing_section" not in by_type
    assert len(by_type["clo_source_row"]) == 4
    assert len(by_type["topic_source_row"]) == 7
    assert len(by_type["assessment_record_source_row"]) == 4
    assert all(
        item.extracted_text.startswith("Extraction method: direct_text\n")
        and "\n--- cell ---\n" in item.extracted_text
        for evidence_type in (
            "clo_source_row",
            "topic_source_row",
            "assessment_record_source_row",
        )
        for item in by_type[evidence_type]
    )
