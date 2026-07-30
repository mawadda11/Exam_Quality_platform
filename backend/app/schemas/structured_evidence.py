from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.domain import (
    AssociationBasis,
    ReferenceResolutionStatus,
    ReferenceTargetType,
    SupportingAnnotationType,
    SupportingMaterialType,
    UploadedFileType,
)


class SupportingMaterialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    analysis_id: UUID
    question_id: UUID | None
    source_document: UploadedFileType
    material_type: SupportingMaterialType
    page_number: int
    source_text: str
    geometry: dict[str, Any] | None
    confidence: float
    extraction_method: str
    created_at: datetime


class SupportingMaterialAnnotationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    analysis_id: UUID
    material_id: UUID | None
    source_document: UploadedFileType
    annotation_type: SupportingAnnotationType
    original_text: str
    normalized_label: str | None
    page_number: int
    geometry: dict[str, Any] | None
    confidence: float
    extraction_method: str
    created_at: datetime


class ReferenceAssociationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    target_material_id: UUID | None
    target_question_id: UUID | None
    review_revision_id: UUID | None
    basis: AssociationBasis
    confidence: float
    proximity_distance: float | None
    exact_label_match: bool
    selected: bool
    ambiguity_reason: str | None


class DocumentReferenceResponse(BaseModel):
    id: UUID
    analysis_id: UUID
    question_id: UUID | None
    source_document: UploadedFileType
    target_type: ReferenceTargetType
    original_text: str
    target_label: str
    normalized_target_label: str
    page_number: int
    geometry: dict[str, Any] | None
    confidence: float
    extraction_method: str
    resolution_status: ReferenceResolutionStatus
    association_candidates: list[ReferenceAssociationResponse]
    created_at: datetime
