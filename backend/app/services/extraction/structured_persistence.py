from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.domain import ReferenceResolutionStatus, UploadedFileType
from app.models.document_reference import DocumentReference
from app.models.evidence import Evidence
from app.models.question import Question
from app.models.supporting_material import SupportingMaterial
from app.models.supporting_material_annotation import SupportingMaterialAnnotation
from app.services.extraction.associations import materialize_reference_associations
from app.services.extraction.types import ExtractionResult


def persist_structured_evidence(
    session: Session,
    analysis_id: UUID,
    result: ExtractionResult,
    questions_by_label: dict[str, Question],
    questions_by_key: dict[str, Question] | None = None,
) -> None:
    questions_by_key = questions_by_key or {}
    materials_by_key: dict[str, SupportingMaterial] = {}
    for extracted_material in result.supporting_materials:
        material_row = SupportingMaterial(
            analysis_id=analysis_id,
            question_id=(
                question.id
                if (
                    question := questions_by_key.get(extracted_material.question_local_key or "")
                    or questions_by_label.get(extracted_material.question_number_label or "")
                )
                is not None
                else None
            ),
            source_document=UploadedFileType.EXAM,
            material_type=extracted_material.material_type,
            page_number=extracted_material.page_number,
            source_text=extracted_material.source_text,
            geometry=(
                extracted_material.geometry.to_dict() if extracted_material.geometry else None
            ),
            confidence=extracted_material.confidence,
            extraction_method=extracted_material.extraction_method,
        )
        session.add(material_row)
        materials_by_key[extracted_material.local_key] = material_row
    session.flush()

    for extracted_annotation in result.supporting_annotations:
        material = materials_by_key.get(extracted_annotation.material_local_key or "")
        annotation_row = SupportingMaterialAnnotation(
            analysis_id=analysis_id,
            material_id=material.id if material is not None else None,
            source_document=UploadedFileType.EXAM,
            annotation_type=extracted_annotation.annotation_type,
            original_text=extracted_annotation.original_text,
            normalized_label=extracted_annotation.normalized_label,
            page_number=extracted_annotation.page_number,
            geometry=(
                extracted_annotation.geometry.to_dict() if extracted_annotation.geometry else None
            ),
            confidence=extracted_annotation.confidence,
            extraction_method=extracted_annotation.extraction_method,
        )
        session.add(annotation_row)
        session.add(
            Evidence(
                analysis_id=analysis_id,
                source_document=UploadedFileType.EXAM,
                evidence_type=extracted_annotation.annotation_type.value,
                page_number=extracted_annotation.page_number,
                item_reference=(
                    extracted_annotation.normalized_label or extracted_annotation.local_key
                ),
                extracted_text=extracted_annotation.original_text,
                geometry=(
                    extracted_annotation.geometry.to_dict()
                    if extracted_annotation.geometry
                    else None
                ),
                confidence=extracted_annotation.confidence,
            )
        )

    reference_rows: list[DocumentReference] = []
    for extracted_reference in result.document_references:
        question = questions_by_key.get(
            extracted_reference.question_local_key or ""
        ) or questions_by_label.get(extracted_reference.question_number_label or "")
        reference_row = DocumentReference(
            analysis_id=analysis_id,
            question_id=question.id if question is not None else None,
            source_document=UploadedFileType.EXAM,
            target_type=extracted_reference.target_type,
            original_text=extracted_reference.original_text,
            target_label=extracted_reference.target_label,
            normalized_target_label=extracted_reference.normalized_target_label,
            page_number=extracted_reference.page_number,
            geometry=(
                extracted_reference.geometry.to_dict() if extracted_reference.geometry else None
            ),
            confidence=extracted_reference.confidence,
            extraction_method=extracted_reference.extraction_method,
            machine_resolution_status=ReferenceResolutionStatus.UNRESOLVED,
        )
        session.add(reference_row)
        reference_rows.append(reference_row)
    session.flush()

    for persisted_reference in reference_rows:
        session.add(
            Evidence(
                analysis_id=analysis_id,
                question_id=persisted_reference.question_id,
                source_document=UploadedFileType.EXAM,
                evidence_type="explicit_reference",
                page_number=persisted_reference.page_number,
                item_reference=str(persisted_reference.id),
                extracted_text=persisted_reference.original_text,
                geometry=persisted_reference.geometry,
                confidence=persisted_reference.confidence,
            )
        )

    for material in materials_by_key.values():
        if not material.source_text:
            continue
        session.add(
            Evidence(
                analysis_id=analysis_id,
                question_id=material.question_id,
                source_document=UploadedFileType.EXAM,
                evidence_type=material.material_type.value,
                page_number=material.page_number,
                item_reference=str(material.id),
                extracted_text=material.source_text,
                geometry=material.geometry,
                confidence=material.confidence,
            )
        )
    session.flush()
    materialize_reference_associations(
        session,
        analysis_id=analysis_id,
        references=reference_rows,
    )
