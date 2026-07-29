from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, cast

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, get_owned_analysis
from app.core.config import Settings, get_settings
from app.core.domain import (
    ProcessingStage,
    ReferenceResolutionStatus,
    ReportFormat,
    UploadedFileType,
)
from app.db.session import get_db
from app.models.analysis import Analysis
from app.models.assessment_record import AssessmentRecord
from app.models.clo import Clo
from app.models.course import Course
from app.models.document_reference import DocumentReference
from app.models.finding import Finding, FindingEvidence
from app.models.processing_event import ProcessingEvent
from app.models.question import Question
from app.models.report import Report
from app.models.supporting_material import SupportingMaterial
from app.models.supporting_material_annotation import SupportingMaterialAnnotation
from app.models.topic import Topic
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.schemas.analysis import AnalysisCreateRequest, AnalysisResponse, ReanalysisCreateRequest
from app.schemas.assessment_record import AssessmentRecordResponse
from app.schemas.clo import CloResponse
from app.schemas.course import CourseInput
from app.schemas.extraction_review import (
    ExtractionReviewConfirmRequest,
    ExtractionReviewConfirmResponse,
    ExtractionReviewResponse,
    ExtractionReviewUpdateRequest,
)
from app.schemas.finding import FindingResponse
from app.schemas.progress import ProgressResponse
from app.schemas.question import QuestionResponse
from app.schemas.recommendation import RecommendationResponse
from app.schemas.report import ReportCreateRequest, ReportResponse
from app.schemas.rule_coverage import RuleCoverageAuditResponse
from app.schemas.score import AnalysisScoreResponse
from app.schemas.structured_evidence import (
    DocumentReferenceResponse,
    ReferenceAssociationResponse,
    SupportingMaterialAnnotationResponse,
    SupportingMaterialResponse,
)
from app.schemas.topic import TopicResponse
from app.schemas.uploaded_file import UploadedFileResponse
from app.services.extraction.review_workflow import (
    ExtractionReviewClosedError,
    ExtractionReviewNotReadyError,
    ExtractionReviewRevisionNotFoundError,
    ExtractionReviewSourceFaithfulnessError,
    ExtractionReviewStaleRevisionError,
    append_extraction_review_revision,
    confirm_extraction_review,
    confirmed_supporting_annotation_texts,
    get_extraction_review,
)
from app.services.extraction.structured_evidence import logical_annotation_text
from app.services.knowledge_base.reference_data import (
    get_controlled_recommendations,
    get_requirement_display,
)
from app.services.processing.runner import (
    run_analysis_pipeline,
    run_post_confirmation_pipeline,
    run_retry_pipeline,
)
from app.services.processing.stages import POST_CONFIRMATION_STAGES
from app.services.reporting.content import assemble_report_content
from app.services.reporting.pdf import render_report_pdf
from app.services.reporting.storage import store_report_pdf
from app.services.rules.coverage_audit import build_rule_coverage_audit
from app.services.rules.versioning import CURRENT_CAPABILITY_VERSION, effective_capability_version
from app.services.storage.files import UploadTooLargeError, stream_validate_and_store
from app.services.storage.keys import generate_storage_key, resolve_storage_path
from app.services.storage.validation import UploadValidationError

router = APIRouter(prefix="/analyses", tags=["analyses"])


def _kb_source_dir(settings: Settings) -> Path:
    return Path(settings.kb_source_dir).resolve()


def _get_or_create_course(db: Session, course_input: CourseInput) -> Course:
    existing = db.execute(
        select(Course).where(Course.code == course_input.code)
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    course = Course(
        code=course_input.code,
        name=course_input.name,
        department=course_input.department,
        program=course_input.program,
    )
    db.add(course)
    db.flush()
    return course


def _load_with_relations(db: Session, analysis_id: uuid.UUID) -> Analysis:
    statement = (
        select(Analysis)
        .where(Analysis.id == analysis_id)
        .options(selectinload(Analysis.files), selectinload(Analysis.course))
    )
    return db.execute(statement).scalar_one()


@router.post("", response_model=AnalysisResponse, status_code=status.HTTP_201_CREATED)
def create_analysis(
    payload: AnalysisCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AnalysisResponse:
    course = _get_or_create_course(db, payload.course)
    analysis = Analysis(
        user_id=current_user.id,
        course_id=course.id,
        exam_type=payload.exam_type,
        term=payload.term,
        capability_version=CURRENT_CAPABILITY_VERSION,
    )
    db.add(analysis)
    db.flush()
    return AnalysisResponse.from_model(_load_with_relations(db, analysis.id))


@router.get("", response_model=list[AnalysisResponse])
def list_analyses(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[AnalysisResponse]:
    statement = (
        select(Analysis)
        .where(Analysis.user_id == current_user.id)
        .options(selectinload(Analysis.files), selectinload(Analysis.course))
        .order_by(Analysis.created_at.desc())
    )
    analyses = db.execute(statement).scalars().all()
    return [AnalysisResponse.from_model(analysis) for analysis in analyses]


@router.get("/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(
    analysis: Annotated[Analysis, Depends(get_owned_analysis)],
    db: Annotated[Session, Depends(get_db)],
) -> AnalysisResponse:
    return AnalysisResponse.from_model(_load_with_relations(db, analysis.id))


@router.post(
    "/{analysis_id}/files",
    response_model=UploadedFileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_analysis_file(
    analysis: Annotated[Analysis, Depends(get_owned_analysis)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    file_type: Annotated[UploadedFileType, Form()],
    file: UploadFile,
) -> UploadedFileResponse:
    already_uploaded = db.execute(
        select(UploadedFile).where(
            UploadedFile.analysis_id == analysis.id, UploadedFile.file_type == file_type
        )
    ).scalar_one_or_none()
    if already_uploaded is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A {file_type.value} file has already been uploaded for this analysis.",
        )

    try:
        stored = await stream_validate_and_store(
            upload=file,
            analysis_id=analysis.id,
            file_type=file_type,
            upload_root=settings.upload_root,
            max_size_bytes=settings.max_upload_mb * 1024 * 1024,
        )
    except UploadTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(exc)) from exc
    except UploadValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

    uploaded_file = UploadedFile(
        analysis_id=analysis.id,
        file_type=file_type,
        original_filename=file.filename or "upload.pdf",
        storage_key=stored.storage_key,
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=stored.size_bytes,
        sha256_hash=stored.sha256_hash,
    )
    try:
        db.add(uploaded_file)
        db.flush()
    except IntegrityError as exc:
        # Race between two concurrent uploads for the same slot slipping past the
        # pre-check above; the unique constraint is the real guarantee, this is cleanup.
        db.rollback()
        resolve_storage_path(settings.upload_root, stored.storage_key).unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A {file_type.value} file has already been uploaded for this analysis.",
        ) from exc

    return UploadedFileResponse.model_validate(uploaded_file)


@router.post(
    "/{analysis_id}/run", response_model=AnalysisResponse, status_code=status.HTTP_202_ACCEPTED
)
def run_analysis(
    analysis: Annotated[Analysis, Depends(get_owned_analysis)],
    db: Annotated[Session, Depends(get_db)],
    background_tasks: BackgroundTasks,
) -> AnalysisResponse:
    if analysis.state != ProcessingStage.QUEUED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This analysis has already been started.",
        )
    if not analysis.ready_for_analysis:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Both the examination PDF and the populated TP-153 must be uploaded "
                "before analysis can start."
            ),
        )

    claim = cast(
        CursorResult[Any],
        db.execute(
            update(Analysis)
            .where(
                Analysis.id == analysis.id,
                Analysis.state == ProcessingStage.QUEUED,
            )
            .values(state=ProcessingStage.VALIDATING)
            .execution_options(synchronize_session=False)
        ),
    )
    if claim.rowcount != 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This analysis has already been started.",
        )
    # The background task opens a separate session and must see the atomic
    # claim before it starts. A second commit by get_db's normal lifecycle is
    # harmless; this explicit one closes the scheduling race.
    db.commit()
    db.expire_all()
    background_tasks.add_task(run_analysis_pipeline, analysis.id)
    return AnalysisResponse.from_model(_load_with_relations(db, analysis.id))


@router.post(
    "/{analysis_id}/retry", response_model=AnalysisResponse, status_code=status.HTTP_202_ACCEPTED
)
def retry_analysis(
    analysis: Annotated[Analysis, Depends(get_owned_analysis)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    background_tasks: BackgroundTasks,
) -> AnalysisResponse:
    if analysis.state != ProcessingStage.FAILED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a failed analysis can be retried.",
        )

    latest_failure = db.execute(
        select(ProcessingEvent)
        .where(
            ProcessingEvent.analysis_id == analysis.id,
            ProcessingEvent.stage == ProcessingStage.FAILED,
        )
        .order_by(ProcessingEvent.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if (
        latest_failure is None
        or latest_failure.failed_stage is None
        or not latest_failure.retryable
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This failure does not have a safe retry boundary.",
        )
    if not analysis.ready_for_analysis:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The original examination and TP-153 files are required before retrying.",
        )
    unavailable_files = [
        uploaded.original_filename
        for uploaded in analysis.files
        if not resolve_storage_path(settings.upload_root, uploaded.storage_key).is_file()
    ]
    if unavailable_files:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The original uploaded files are unavailable. Upload them in a new analysis.",
        )
    if (
        latest_failure.failed_stage in POST_CONFIRMATION_STAGES
        and analysis.confirmed_review_id is None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The confirmed extraction revision required for retry is unavailable.",
        )

    retry_stage = latest_failure.failed_stage
    confirmed_review_id = analysis.confirmed_review_id
    claim = cast(
        CursorResult[Any],
        db.execute(
            update(Analysis)
            .where(
                Analysis.id == analysis.id,
                Analysis.state == ProcessingStage.FAILED,
            )
            .values(state=retry_stage)
            .execution_options(synchronize_session=False)
        ),
    )
    if claim.rowcount != 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A retry or another processing action has already started.",
        )
    db.add(
        ProcessingEvent(
            analysis_id=analysis.id,
            stage=retry_stage,
            message="Retry accepted. Processing will resume from the failed stage.",
        )
    )
    db.commit()
    db.expire_all()
    background_tasks.add_task(run_retry_pipeline, analysis.id, retry_stage, confirmed_review_id)
    return AnalysisResponse.from_model(_load_with_relations(db, analysis.id))


def _review_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ExtractionReviewRevisionNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, ExtractionReviewSourceFaithfulnessError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    if isinstance(
        exc,
        (
            ExtractionReviewClosedError,
            ExtractionReviewNotReadyError,
            ExtractionReviewStaleRevisionError,
        ),
    ):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    raise exc


@router.get(
    "/{analysis_id}/extraction-review",
    response_model=ExtractionReviewResponse,
)
def read_extraction_review(
    analysis: Annotated[Analysis, Depends(get_owned_analysis)],
    db: Annotated[Session, Depends(get_db)],
) -> ExtractionReviewResponse:
    try:
        return get_extraction_review(db, analysis)
    except Exception as exc:
        raise _review_http_error(exc) from exc


@router.put(
    "/{analysis_id}/extraction-review",
    response_model=ExtractionReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def save_extraction_review(
    payload: ExtractionReviewUpdateRequest,
    analysis: Annotated[Analysis, Depends(get_owned_analysis)],
    db: Annotated[Session, Depends(get_db)],
) -> ExtractionReviewResponse:
    try:
        return append_extraction_review_revision(
            db,
            analysis,
            base_revision_id=payload.base_revision_id,
            candidate_snapshot=payload.snapshot,
        )
    except Exception as exc:
        raise _review_http_error(exc) from exc


@router.post(
    "/{analysis_id}/extraction-review/confirm",
    response_model=ExtractionReviewConfirmResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def confirm_extraction_review_endpoint(
    payload: ExtractionReviewConfirmRequest,
    analysis: Annotated[Analysis, Depends(get_owned_analysis)],
    db: Annotated[Session, Depends(get_db)],
    background_tasks: BackgroundTasks,
) -> ExtractionReviewConfirmResponse:
    try:
        confirmed = confirm_extraction_review(
            db,
            analysis,
            revision_id=payload.revision_id,
        )
    except Exception as exc:
        raise _review_http_error(exc) from exc

    # The worker opens a separate session and must observe the exact confirmation claim.
    db.commit()
    background_tasks.add_task(
        run_post_confirmation_pipeline,
        analysis.id,
        confirmed.revision_id,
    )
    return ExtractionReviewConfirmResponse(
        analysis_id=analysis.id,
        confirmed_revision_id=confirmed.revision_id,
        confirmed_revision_number=confirmed.revision_number,
        state=ProcessingStage.BUILDING_EVIDENCE,
    )


@router.post(
    "/{analysis_id}/reanalysis",
    response_model=AnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_reanalysis(
    predecessor: Annotated[Analysis, Depends(get_owned_analysis)],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    payload: ReanalysisCreateRequest | None = None,
) -> AnalysisResponse:
    payload = payload or ReanalysisCreateRequest()
    # PRD: "Create a linked reanalysis for a revised examination when needed"
    # - reads as a post-review action on results already seen, not a retry
    # mechanism for a run that never finished.
    if predecessor.state != ProcessingStage.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a completed analysis can be reanalyzed.",
        )

    reanalysis = Analysis(
        user_id=current_user.id,
        course_id=predecessor.course_id,
        exam_type=predecessor.exam_type,
        term=predecessor.term,
        predecessor_analysis_id=predecessor.id,
        capability_version=CURRENT_CAPABILITY_VERSION,
    )
    db.add(reanalysis)
    db.flush()

    if payload.reuse_tp153:
        predecessor_tp153 = next(
            (f for f in predecessor.files if f.file_type == UploadedFileType.TP153), None
        )
        if predecessor_tp153 is not None:
            # Copy the bytes to a storage key of the *new* analysis's own -
            # storage_key is unique per row, and every other stage (extraction,
            # evidence persistence) already assumes "this analysis's own file
            # reference", so the new row must look exactly like a fresh
            # upload rather than aliasing the predecessor's row/key.
            source_path = resolve_storage_path(settings.upload_root, predecessor_tp153.storage_key)
            new_storage_key = generate_storage_key(reanalysis.id, UploadedFileType.TP153)
            destination_path = resolve_storage_path(settings.upload_root, new_storage_key)
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            destination_path.write_bytes(source_path.read_bytes())

            db.add(
                UploadedFile(
                    analysis_id=reanalysis.id,
                    file_type=UploadedFileType.TP153,
                    original_filename=predecessor_tp153.original_filename,
                    storage_key=new_storage_key,
                    mime_type=predecessor_tp153.mime_type,
                    size_bytes=predecessor_tp153.size_bytes,
                    sha256_hash=predecessor_tp153.sha256_hash,
                )
            )
            db.flush()

    return AnalysisResponse.from_model(_load_with_relations(db, reanalysis.id))


@router.get("/{analysis_id}/progress", response_model=ProgressResponse)
def get_analysis_progress(
    analysis: Annotated[Analysis, Depends(get_owned_analysis)],
    db: Annotated[Session, Depends(get_db)],
) -> ProgressResponse:
    latest_event = db.execute(
        select(ProcessingEvent)
        .where(ProcessingEvent.analysis_id == analysis.id)
        .order_by(ProcessingEvent.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    return ProgressResponse(
        analysis_id=analysis.id,
        state=analysis.state,
        message=latest_event.message if latest_event else None,
        failed_stage=latest_event.failed_stage if latest_event else None,
        error_code=latest_event.error_code if latest_event else None,
        can_retry=bool(
            analysis.state == ProcessingStage.FAILED
            and latest_event is not None
            and latest_event.retryable
        ),
        updated_at=analysis.updated_at,
    )


@router.get("/{analysis_id}/questions", response_model=list[QuestionResponse])
def list_analysis_questions(
    analysis: Annotated[Analysis, Depends(get_owned_analysis)],
    db: Annotated[Session, Depends(get_db)],
) -> list[QuestionResponse]:
    questions = db.execute(
        select(Question).where(Question.analysis_id == analysis.id).order_by(Question.sequence)
    ).scalars()
    return [QuestionResponse.model_validate(question) for question in questions]


@router.get("/{analysis_id}/clos", response_model=list[CloResponse])
def list_analysis_clos(
    analysis: Annotated[Analysis, Depends(get_owned_analysis)],
    db: Annotated[Session, Depends(get_db)],
) -> list[CloResponse]:
    # Raw extracted TP-153 source data only - no alignment, coverage, or
    # academic status. That comparison against the exam is rule-engine work
    # for a later milestone.
    clos = db.execute(
        select(Clo).where(Clo.analysis_id == analysis.id).order_by(Clo.page_number, Clo.created_at)
    ).scalars()
    return [CloResponse.model_validate(clo) for clo in clos]


@router.get("/{analysis_id}/topics", response_model=list[TopicResponse])
def list_analysis_topics(
    analysis: Annotated[Analysis, Depends(get_owned_analysis)],
    db: Annotated[Session, Depends(get_db)],
) -> list[TopicResponse]:
    # Raw extracted TP-153 source data only - see list_analysis_clos.
    topics = db.execute(
        select(Topic)
        .where(Topic.analysis_id == analysis.id)
        .order_by(Topic.page_number, Topic.created_at)
    ).scalars()
    return [TopicResponse.model_validate(topic) for topic in topics]


@router.get("/{analysis_id}/assessment-records", response_model=list[AssessmentRecordResponse])
def list_analysis_assessment_records(
    analysis: Annotated[Analysis, Depends(get_owned_analysis)],
    db: Annotated[Session, Depends(get_db)],
) -> list[AssessmentRecordResponse]:
    # Raw extracted TP-153 source data only - see list_analysis_clos.
    records = db.execute(
        select(AssessmentRecord)
        .where(AssessmentRecord.analysis_id == analysis.id)
        .order_by(AssessmentRecord.page_number, AssessmentRecord.created_at)
    ).scalars()
    return [AssessmentRecordResponse.model_validate(record) for record in records]


@router.get(
    "/{analysis_id}/supporting-materials",
    response_model=list[SupportingMaterialResponse],
)
def list_analysis_supporting_materials(
    analysis: Annotated[Analysis, Depends(get_owned_analysis)],
    db: Annotated[Session, Depends(get_db)],
) -> list[SupportingMaterialResponse]:
    rows = db.execute(
        select(SupportingMaterial)
        .where(SupportingMaterial.analysis_id == analysis.id)
        .order_by(SupportingMaterial.page_number, SupportingMaterial.created_at)
    ).scalars()
    return [SupportingMaterialResponse.model_validate(row) for row in rows]


@router.get(
    "/{analysis_id}/supporting-material-annotations",
    response_model=list[SupportingMaterialAnnotationResponse],
)
def list_analysis_supporting_material_annotations(
    analysis: Annotated[Analysis, Depends(get_owned_analysis)],
    db: Annotated[Session, Depends(get_db)],
) -> list[SupportingMaterialAnnotationResponse]:
    rows = list(
        db.execute(
            select(SupportingMaterialAnnotation)
            .where(SupportingMaterialAnnotation.analysis_id == analysis.id)
            .order_by(
                SupportingMaterialAnnotation.page_number,
                SupportingMaterialAnnotation.created_at,
            )
        ).scalars()
    )
    reviewed_texts = confirmed_supporting_annotation_texts(db, analysis)
    if reviewed_texts is not None:
        rows = [row for row in rows if row.id in reviewed_texts]
    return [
        SupportingMaterialAnnotationResponse.model_validate(row).model_copy(
            update={
                "original_text": (
                    reviewed_texts[row.id]
                    if reviewed_texts is not None
                    else logical_annotation_text(row.original_text, row.normalized_label)
                )
            }
        )
        for row in rows
    ]


@router.get(
    "/{analysis_id}/document-references",
    response_model=list[DocumentReferenceResponse],
)
def list_analysis_document_references(
    analysis: Annotated[Analysis, Depends(get_owned_analysis)],
    db: Annotated[Session, Depends(get_db)],
) -> list[DocumentReferenceResponse]:
    rows = (
        db.execute(
            select(DocumentReference)
            .where(DocumentReference.analysis_id == analysis.id)
            .options(selectinload(DocumentReference.association_candidates))
            .order_by(DocumentReference.page_number, DocumentReference.created_at)
        )
        .scalars()
        .all()
    )
    responses: list[DocumentReferenceResponse] = []
    for row in rows:
        active_candidates = [
            item
            for item in row.association_candidates
            if item.review_revision_id == analysis.confirmed_review_id
        ]
        exact_candidates = [item for item in active_candidates if item.exact_label_match]
        selected_candidates = [item for item in exact_candidates if item.selected]
        resolution_status = (
            ReferenceResolutionStatus.RESOLVED
            if len(selected_candidates) == 1
            else (
                ReferenceResolutionStatus.AMBIGUOUS
                if len(exact_candidates) > 1
                else ReferenceResolutionStatus.UNRESOLVED
            )
        )
        responses.append(
            DocumentReferenceResponse(
                id=row.id,
                analysis_id=row.analysis_id,
                question_id=row.question_id,
                source_document=row.source_document,
                target_type=row.target_type,
                original_text=row.original_text,
                target_label=row.target_label,
                normalized_target_label=row.normalized_target_label,
                page_number=row.page_number,
                geometry=row.geometry,
                confidence=row.confidence,
                extraction_method=row.extraction_method,
                resolution_status=resolution_status,
                association_candidates=[
                    ReferenceAssociationResponse.model_validate(item) for item in active_candidates
                ],
                created_at=row.created_at,
            )
        )
    return responses


def _load_findings(db: Session, analysis_id: uuid.UUID) -> list[Finding]:
    return list(
        db.execute(
            select(Finding)
            .where(Finding.analysis_id == analysis_id)
            .order_by(Finding.created_at, Finding.rule_id)
            .options(selectinload(Finding.evidence_links).selectinload(FindingEvidence.evidence))
        )
        .scalars()
        .all()
    )


@router.get("/{analysis_id}/findings", response_model=list[FindingResponse])
def list_analysis_findings(
    analysis: Annotated[Analysis, Depends(get_owned_analysis)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[FindingResponse]:
    # Deterministic rule outcomes, enriched (M9) with each Finding's official
    # requirement display metadata (name/dimension/officiality) resolved
    # from 04_requirements.xlsx - no aggregate analysis score here, that's
    # GET /score below, still computed read-time rather than persisted
    # (Milestone 10 owns persistence/report rendering).
    findings = _load_findings(db, analysis.id)
    source_dir = _kb_source_dir(settings)
    return [
        FindingResponse.from_model(
            finding, get_requirement_display(source_dir, finding.requirement_id)
        )
        for finding in findings
    ]


@router.get("/{analysis_id}/rule-coverage", response_model=RuleCoverageAuditResponse)
def get_analysis_rule_coverage(
    analysis: Annotated[Analysis, Depends(get_owned_analysis)],
    db: Annotated[Session, Depends(get_db)],
) -> RuleCoverageAuditResponse:
    """Return implementation coverage for every governed exam-facing rule.

    This endpoint deliberately separates operational capability gaps from the
    five academic statuses used by Findings.
    """

    return build_rule_coverage_audit(
        analysis.id,
        _load_findings(db, analysis.id),
        capability_version=effective_capability_version(analysis),
    )


@router.get("/{analysis_id}/score", response_model=AnalysisScoreResponse)
def get_analysis_score(
    analysis: Annotated[Analysis, Depends(get_owned_analysis)],
    db: Annotated[Session, Depends(get_db)],
) -> AnalysisScoreResponse:
    # Read-time aggregation over whatever Findings currently exist (none yet
    # -> Insufficient Evidence) - reuses the M6 scoring function unchanged.
    # No `analyses.score` column: see docs/DATABASE_SCHEMA.md's M9 note.
    findings = _load_findings(db, analysis.id)
    return AnalysisScoreResponse.from_findings(analysis.id, findings)


@router.get("/{analysis_id}/recommendations", response_model=list[RecommendationResponse])
def list_analysis_recommendations(
    analysis: Annotated[Analysis, Depends(get_owned_analysis)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[RecommendationResponse]:
    # Resolved read-time from each Finding's (rule_id, status) against
    # 08_recommendations.xlsx - never persisted. Satisfied/Not Applicable
    # findings naturally produce zero matches (see reference_data.py).
    findings = _load_findings(db, analysis.id)
    source_dir = _kb_source_dir(settings)
    return [
        RecommendationResponse.from_finding(finding, display)
        for finding in findings
        for display in get_controlled_recommendations(
            source_dir,
            finding.rule_id,
            finding.status,
            finding.recommendation_id,
        )
    ]


@router.post(
    "/{analysis_id}/reports", response_model=ReportResponse, status_code=status.HTTP_201_CREATED
)
def create_report(
    analysis: Annotated[Analysis, Depends(get_owned_analysis)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    payload: ReportCreateRequest | None = None,
) -> ReportResponse:
    payload = payload or ReportCreateRequest()
    # M10 decision: on-demand only, triggered by this explicit action - never
    # generated automatically by the processing pipeline. Regenerating
    # creates a new Report row rather than replacing an existing one (see
    # app.models.report.Report's docstring).
    if analysis.state != ProcessingStage.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A report can only be generated for a completed analysis.",
        )

    findings = _load_findings(db, analysis.id)
    source_dir = _kb_source_dir(settings)
    assessment_records = list(
        db.execute(
            select(AssessmentRecord)
            .where(AssessmentRecord.analysis_id == analysis.id)
            .order_by(AssessmentRecord.page_number, AssessmentRecord.created_at)
        ).scalars()
    )
    supporting_materials = list(
        db.execute(
            select(SupportingMaterial)
            .where(SupportingMaterial.analysis_id == analysis.id)
            .order_by(SupportingMaterial.page_number, SupportingMaterial.created_at)
        ).scalars()
    )
    supporting_annotations = list(
        db.execute(
            select(SupportingMaterialAnnotation)
            .where(SupportingMaterialAnnotation.analysis_id == analysis.id)
            .order_by(
                SupportingMaterialAnnotation.page_number,
                SupportingMaterialAnnotation.created_at,
            )
        ).scalars()
    )
    reviewed_annotation_texts = confirmed_supporting_annotation_texts(db, analysis)
    if reviewed_annotation_texts is not None:
        supporting_annotations = [
            item for item in supporting_annotations if item.id in reviewed_annotation_texts
        ]
    else:
        reviewed_annotation_texts = {
            item.id: logical_annotation_text(item.original_text, item.normalized_label)
            for item in supporting_annotations
        }
    document_references = list(
        db.execute(
            select(DocumentReference)
            .where(DocumentReference.analysis_id == analysis.id)
            .options(selectinload(DocumentReference.association_candidates))
            .order_by(DocumentReference.page_number, DocumentReference.created_at)
        ).scalars()
    )
    coverage = build_rule_coverage_audit(
        analysis.id,
        findings,
        capability_version=effective_capability_version(analysis),
    )
    content = assemble_report_content(
        analysis,
        findings,
        source_dir,
        datetime.now(UTC),
        assessment_records=assessment_records,
        rule_coverage=coverage,
        supporting_materials=supporting_materials,
        supporting_annotations=supporting_annotations,
        supporting_annotation_texts=reviewed_annotation_texts,
        document_references=document_references,
    )
    pdf_bytes = render_report_pdf(content, language=payload.language)

    report_id = uuid.uuid4()
    stored = store_report_pdf(
        content=pdf_bytes,
        analysis_id=analysis.id,
        report_id=report_id,
        report_root=settings.report_root,
    )

    report = Report(
        id=report_id,
        analysis_id=analysis.id,
        format=ReportFormat.PDF,
        language=payload.language,
        storage_key=stored.storage_key,
        size_bytes=stored.size_bytes,
        sha256_hash=stored.sha256_hash,
        kb_version=content.kb_version,
        capability_version=effective_capability_version(analysis),
        score=content.score,
        score_label=content.score_label,
        denominator=content.denominator,
        satisfied_count=content.satisfied_count,
        partially_satisfied_count=content.partially_satisfied_count,
        not_satisfied_count=content.not_satisfied_count,
        not_verified_count=content.not_verified_count,
        not_applicable_count=content.not_applicable_count,
    )
    db.add(report)
    db.flush()
    return ReportResponse.model_validate(report)


@router.get("/{analysis_id}/reports", response_model=list[ReportResponse])
def list_analysis_reports(
    analysis: Annotated[Analysis, Depends(get_owned_analysis)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ReportResponse]:
    # Full history, most recent first - every generation is preserved (M10
    # decision: never replace an existing Report record).
    reports = (
        db.execute(
            select(Report)
            .where(Report.analysis_id == analysis.id)
            .order_by(Report.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [ReportResponse.model_validate(report) for report in reports]
