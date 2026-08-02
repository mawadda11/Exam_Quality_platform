from __future__ import annotations

import json
import uuid
from pathlib import Path

from fpdf import FPDF
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.domain import (
    AcademicStatus,
    AssociationBasis,
    ExamType,
    ReferenceResolutionStatus,
    ReferenceTargetType,
    SupportingAnnotationType,
    SupportingMaterialType,
)
from app.models.analysis import Analysis
from app.models.course import Course
from app.models.document_reference import DocumentReference
from app.models.reference_association import ReferenceAssociation
from app.models.supporting_material import SupportingMaterial
from app.models.supporting_material_annotation import SupportingMaterialAnnotation
from app.models.user import User
from app.schemas.extraction_review import ExtractionReviewSnapshot
from app.services.extraction.associations import (
    materialize_confirmed_reference_associations,
)
from app.services.extraction.digital_pdf_extractor import PdfPlumberExamExtractor
from app.services.extraction.persistence import persist_extraction_result
from app.services.extraction.review_snapshot import materialize_initial_review_revision
from app.services.extraction.structured_evidence import (
    extract_question_references,
    normalize_annotation_label,
)
from app.services.extraction.types import (
    ExtractedDocumentReference,
    ExtractedQuestion,
    ExtractedSupportingAnnotation,
    ExtractedSupportingMaterial,
    ExtractionResult,
    Geometry,
)
from app.services.rules.structured_evidence import (
    evaluate_referenced_material_availability,
    evaluate_resolvable_cross_references,
    evaluate_supporting_material_association,
)


def _analysis(session: Session) -> Analysis:
    suffix = uuid.uuid4().hex
    user = User(email=f"batch4-{suffix}@example.test", display_name="Batch 4")
    course = Course(code=f"B4-{suffix[:8]}", name="Structured Evidence")
    session.add_all([user, course])
    session.flush()
    analysis = Analysis(
        user_id=user.id,
        course_id=course.id,
        exam_type=ExamType.MIDTERM,
        term="Batch 4",
        capability_version="v2-b4-structured-evidence",
    )
    session.add(analysis)
    session.flush()
    return analysis


def _question() -> ExtractedQuestion:
    return ExtractedQuestion(
        number_label="Q1",
        text="Q1. Refer to Figure 1.",
        page_number=1,
        parent_number_label=None,
        marks=5,
        sequence=1,
        confidence=0.98,
        geometry=Geometry(10, 10, 200, 30),
    )


def _result(
    *,
    material_count: int = 1,
    include_label: bool = True,
    include_reference: bool = True,
    material_type: SupportingMaterialType = SupportingMaterialType.FIGURE,
    source_text: str = "",
) -> ExtractionResult:
    materials = [
        ExtractedSupportingMaterial(
            local_key=f"figure-{index}",
            material_type=material_type,
            page_number=1,
            source_text=source_text,
            confidence=0.96,
            geometry=Geometry(20 + index * 5, 80, 180 + index * 5, 160),
            extraction_method="direct_text",
            question_number_label="Q1",
        )
        for index in range(material_count)
    ]
    annotations = (
        [
            ExtractedSupportingAnnotation(
                local_key=f"label-{index}",
                material_local_key=material.local_key,
                annotation_type=SupportingAnnotationType.LABEL,
                original_text=(
                    "Figure 1"
                    if material_type is SupportingMaterialType.FIGURE
                    else ("Table 1" if material_type is SupportingMaterialType.TABLE else "Code 1")
                ),
                normalized_label=f"{material_type.value}:1",
                page_number=1,
                confidence=0.95,
                geometry=Geometry(20, 165, 180, 180),
                extraction_method="direct_text",
            )
            for index, material in enumerate(materials)
        ]
        if include_label
        else []
    )
    references = (
        [
            ExtractedDocumentReference(
                local_key="reference-1",
                target_type=ReferenceTargetType(material_type.value),
                original_text=(
                    "Figure 1"
                    if material_type is SupportingMaterialType.FIGURE
                    else ("Table 1" if material_type is SupportingMaterialType.TABLE else "Code 1")
                ),
                target_label=f"{material_type.value.title()} 1",
                normalized_target_label=f"{material_type.value}:1",
                page_number=1,
                confidence=0.98,
                geometry=Geometry(10, 10, 200, 30),
                extraction_method="direct_text",
                question_number_label="Q1",
            )
        ]
        if include_reference
        else []
    )
    return ExtractionResult(
        questions=[_question()],
        evidence=[],
        supporting_materials=materials,
        supporting_annotations=annotations,
        document_references=references,
    )


def _persist_and_confirm_candidates(
    session: Session,
    result: ExtractionResult,
) -> tuple[Analysis, ExtractionReviewSnapshot, uuid.UUID]:
    analysis = _analysis(session)
    persist_extraction_result(session, analysis.id, result)
    initial = materialize_initial_review_revision(session, analysis.id)
    snapshot = ExtractionReviewSnapshot.model_validate_json(json.dumps(initial.snapshot))
    materialize_confirmed_reference_associations(
        session,
        analysis_id=analysis.id,
        snapshot=snapshot,
        review_revision_id=initial.id,
    )
    session.flush()
    return analysis, snapshot, initial.id


def test_bilingual_reference_normalization_preserves_original_wording() -> None:
    assert normalize_annotation_label("Figure 12: Architecture") == "figure:12"
    assert normalize_annotation_label("الجدول ٣: النتائج") == "table:3"

    references = extract_question_references(
        text="راجع الشكل ٢ ثم انظر إلى السؤال ٣",
        question_number_label="Q1",
        page_number=4,
        geometry=None,
        confidence=0.82,
        extraction_method="ocr",
    )

    assert [item.normalized_target_label for item in references] == [
        "figure:2",
        "question:3",
    ]
    assert [item.original_text for item in references] == [
        "الشكل ٢",
        "انظر إلى السؤال ٣",
    ]
    assert all(item.page_number == 4 for item in references)
    assert all(item.confidence == 0.82 for item in references)


def test_exact_unique_label_is_selected_and_proximity_is_only_supporting(
    db_engine: Engine,
) -> None:
    with Session(db_engine) as session:
        analysis, _, _ = _persist_and_confirm_candidates(session, _result())
        reference = session.scalars(
            select(DocumentReference).where(DocumentReference.analysis_id == analysis.id)
        ).one()
        machine = session.scalars(
            select(ReferenceAssociation).where(
                ReferenceAssociation.reference_id == reference.id,
                ReferenceAssociation.review_revision_id.is_(None),
            )
        ).all()

        assert reference.machine_resolution_status is ReferenceResolutionStatus.RESOLVED
        assert len(machine) == 1
        assert machine[0].basis is AssociationBasis.EXACT_LABEL
        assert machine[0].selected is True
        assert machine[0].exact_label_match is True


def test_duplicate_exact_labels_preserve_all_candidates_as_ambiguous(
    db_engine: Engine,
) -> None:
    with Session(db_engine) as session:
        analysis, _, _ = _persist_and_confirm_candidates(
            session,
            _result(material_count=2),
        )
        reference = session.scalars(
            select(DocumentReference).where(DocumentReference.analysis_id == analysis.id)
        ).one()
        candidates = session.scalars(
            select(ReferenceAssociation).where(
                ReferenceAssociation.reference_id == reference.id,
                ReferenceAssociation.review_revision_id.is_(None),
            )
        ).all()

        assert reference.machine_resolution_status is ReferenceResolutionStatus.AMBIGUOUS
        assert len(candidates) == 2
        assert all(candidate.exact_label_match for candidate in candidates)
        assert not any(candidate.selected for candidate in candidates)
        assert all(candidate.ambiguity_reason for candidate in candidates)


def test_proximity_without_exact_label_is_never_selected(
    db_engine: Engine,
) -> None:
    with Session(db_engine) as session:
        analysis, _, _ = _persist_and_confirm_candidates(
            session,
            _result(include_label=False),
        )
        reference = session.scalars(
            select(DocumentReference).where(DocumentReference.analysis_id == analysis.id)
        ).one()
        candidates = session.scalars(
            select(ReferenceAssociation).where(
                ReferenceAssociation.reference_id == reference.id,
                ReferenceAssociation.review_revision_id.is_(None),
            )
        ).all()

        assert reference.machine_resolution_status is ReferenceResolutionStatus.UNRESOLVED
        assert len(candidates) == 1
        assert candidates[0].basis is AssociationBasis.PROXIMITY_SUPPORT
        assert candidates[0].selected is False
        assert candidates[0].exact_label_match is False
        assert candidates[0].proximity_distance is not None


def test_structured_source_rows_remain_immutable_when_review_snapshot_is_corrected(
    db_engine: Engine,
) -> None:
    with Session(db_engine) as session:
        analysis = _analysis(session)
        persist_extraction_result(session, analysis.id, _result())
        initial = materialize_initial_review_revision(session, analysis.id)
        snapshot = ExtractionReviewSnapshot.model_validate_json(json.dumps(initial.snapshot))
        original_annotation = session.scalars(
            select(SupportingMaterialAnnotation).where(
                SupportingMaterialAnnotation.analysis_id == analysis.id
            )
        ).one()
        original_reference = session.scalars(
            select(DocumentReference).where(DocumentReference.analysis_id == analysis.id)
        ).one()

        corrected = snapshot.model_copy(deep=True)
        corrected.supporting_annotations[0].original_text = "Figure 1: Reviewed caption"
        corrected.document_references[0].target_label = "Figure 1 (reviewed)"
        materialize_confirmed_reference_associations(
            session,
            analysis_id=analysis.id,
            snapshot=corrected,
            review_revision_id=initial.id,
        )
        session.flush()

        assert original_annotation.original_text == "Figure 1"
        assert original_reference.target_label == "Figure 1"
        assert (
            corrected.supporting_annotations[0].original_text != original_annotation.original_text
        )
        assert corrected.document_references[0].target_label != original_reference.target_label


def test_historical_analysis_has_empty_structured_review_collections(
    db_engine: Engine,
) -> None:
    with Session(db_engine) as session:
        analysis = _analysis(session)
        analysis.capability_version = None
        session.flush()
        revision = materialize_initial_review_revision(session, analysis.id)
        snapshot = ExtractionReviewSnapshot.model_validate_json(json.dumps(revision.snapshot))

        assert snapshot.supporting_materials == []
        assert snapshot.supporting_annotations == []
        assert snapshot.document_references == []
        assert snapshot.reference_associations == []


def test_governed_rules_exact_unique_and_not_applicable_branches(
    db_engine: Engine,
) -> None:
    with Session(db_engine) as session:
        analysis, snapshot, revision_id = _persist_and_confirm_candidates(session, _result())
        assert (
            evaluate_referenced_material_availability(
                session,
                analysis_id=analysis.id,
                snapshot=snapshot,
                confirmed_revision_id=revision_id,
            ).status
            is AcademicStatus.SATISFIED
        )
        assert (
            evaluate_supporting_material_association(
                session,
                analysis_id=analysis.id,
                snapshot=snapshot,
                confirmed_revision_id=revision_id,
            ).status
            is AcademicStatus.SATISFIED
        )
        assert (
            evaluate_resolvable_cross_references(
                session,
                analysis_id=analysis.id,
                snapshot=snapshot,
                confirmed_revision_id=revision_id,
            ).status
            is AcademicStatus.SATISFIED
        )

        no_reference_analysis, no_reference_snapshot, no_reference_revision = (
            _persist_and_confirm_candidates(
                session,
                _result(material_count=0, include_label=False, include_reference=False),
            )
        )
        assert (
            evaluate_referenced_material_availability(
                session,
                analysis_id=no_reference_analysis.id,
                snapshot=no_reference_snapshot,
                confirmed_revision_id=no_reference_revision,
            ).status
            is AcademicStatus.NOT_APPLICABLE
        )
        assert (
            evaluate_supporting_material_association(
                session,
                analysis_id=no_reference_analysis.id,
                snapshot=no_reference_snapshot,
                confirmed_revision_id=no_reference_revision,
            ).status
            is AcademicStatus.NOT_APPLICABLE
        )
        assert (
            evaluate_resolvable_cross_references(
                session,
                analysis_id=no_reference_analysis.id,
                snapshot=no_reference_snapshot,
                confirmed_revision_id=no_reference_revision,
            ).status
            is AcademicStatus.NOT_APPLICABLE
        )


def test_governed_rules_ambiguous_and_proximity_only_are_not_verified(
    db_engine: Engine,
) -> None:
    with Session(db_engine) as session:
        ambiguous, ambiguous_snapshot, ambiguous_revision = _persist_and_confirm_candidates(
            session,
            _result(material_count=2),
        )
        for evaluator in (
            evaluate_referenced_material_availability,
            evaluate_supporting_material_association,
            evaluate_resolvable_cross_references,
        ):
            assert (
                evaluator(
                    session,
                    analysis_id=ambiguous.id,
                    snapshot=ambiguous_snapshot,
                    confirmed_revision_id=ambiguous_revision,
                ).status
                is AcademicStatus.NOT_VERIFIED
            )

        proximity, proximity_snapshot, proximity_revision = _persist_and_confirm_candidates(
            session,
            _result(include_label=False),
        )
        assert (
            evaluate_resolvable_cross_references(
                session,
                analysis_id=proximity.id,
                snapshot=proximity_snapshot,
                confirmed_revision_id=proximity_revision,
            ).status
            is AcademicStatus.NOT_VERIFIED
        )
        assert (
            evaluate_referenced_material_availability(
                session,
                analysis_id=proximity.id,
                snapshot=proximity_snapshot,
                confirmed_revision_id=proximity_revision,
            ).status
            is AcademicStatus.NOT_SATISFIED
        )


def test_rule014_incomplete_table_is_partially_satisfied(
    db_engine: Engine,
) -> None:
    with Session(db_engine) as session:
        analysis, snapshot, revision_id = _persist_and_confirm_candidates(
            session,
            _result(material_type=SupportingMaterialType.TABLE, source_text=""),
        )
        result = evaluate_referenced_material_availability(
            session,
            analysis_id=analysis.id,
            snapshot=snapshot,
            confirmed_revision_id=revision_id,
        )

        assert result.status is AcademicStatus.PARTIALLY_SATISFIED
        assert result.evidence_ids


def test_persistence_keeps_page_geometry_confidence_and_extraction_method(
    db_engine: Engine,
) -> None:
    with Session(db_engine) as session:
        analysis = _analysis(session)
        persist_extraction_result(session, analysis.id, _result())
        material = session.scalars(
            select(SupportingMaterial).where(SupportingMaterial.analysis_id == analysis.id)
        ).one()

        assert material.page_number == 1
        assert material.geometry == {
            "x0": 20,
            "top": 80,
            "x1": 180,
            "bottom": 160,
        }
        assert material.confidence == 0.96
        assert material.extraction_method == "direct_text"


def test_plain_exam_questions_do_not_create_code_block(
    tmp_path: Path,
) -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)

    lines = (
        "CS101 Midterm Examination (Sample)",
        "Course: Introduction to Programming",
        "Total Marks: 30",
        "Q1 (10): Define an algorithm and explain two characteristics.",
        "Q2 (10): Write a Python function to calculate the factorial of n.",
        "Q3 (10): Compare lists and tuples with two examples.",
    )

    for line in lines:
        pdf.cell(text=line)
        pdf.ln(8)

    pdf_path = tmp_path / "plain-question-exam.pdf"
    pdf.output(pdf_path)

    extracted = PdfPlumberExamExtractor().extract(pdf_path)

    assert not any(
        item.material_type is SupportingMaterialType.CODE_BLOCK
        for item in extracted.supporting_materials
    )
    assert extracted.supporting_materials == []


def test_real_pdf_pipeline_extracts_persists_and_verifies_unique_table(
    db_engine: Engine,
    tmp_path: Path,
) -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(text="Q1. Refer to Table 1 and explain the result. [5 marks]")
    pdf.ln(12)
    pdf.cell(text="Table 1: Results")
    pdf.ln(7)
    for left, right in (("Student", "Mark"), ("A", "5"), ("B", "4")):
        pdf.cell(45, 8, left, border=1)
        pdf.cell(45, 8, right, border=1)
        pdf.ln(8)
    pdf_path = tmp_path / "structured-table.pdf"
    pdf.output(pdf_path)

    extracted = PdfPlumberExamExtractor().extract(pdf_path)
    assert any(
        item.material_type is SupportingMaterialType.TABLE
        for item in extracted.supporting_materials
    )
    assert any(item.normalized_label == "table:1" for item in extracted.supporting_annotations)
    assert any(item.normalized_target_label == "table:1" for item in extracted.document_references)

    with Session(db_engine) as session:
        analysis, snapshot, revision_id = _persist_and_confirm_candidates(
            session,
            extracted,
        )
        assert (
            evaluate_referenced_material_availability(
                session,
                analysis_id=analysis.id,
                snapshot=snapshot,
                confirmed_revision_id=revision_id,
            ).status
            is AcademicStatus.SATISFIED
        )
        assert (
            evaluate_supporting_material_association(
                session,
                analysis_id=analysis.id,
                snapshot=snapshot,
                confirmed_revision_id=revision_id,
            ).status
            is AcademicStatus.SATISFIED
        )
        assert (
            evaluate_resolvable_cross_references(
                session,
                analysis_id=analysis.id,
                snapshot=snapshot,
                confirmed_revision_id=revision_id,
            ).status
            is AcademicStatus.SATISFIED
        )
