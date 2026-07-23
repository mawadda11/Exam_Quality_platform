from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, get_owned_analysis
from app.core.config import Settings, get_settings
from app.core.domain import ProcessingStage, UploadedFileType
from app.db.session import get_db
from app.models.analysis import Analysis
from app.models.assessment_record import AssessmentRecord
from app.models.clo import Clo
from app.models.course import Course
from app.models.finding import Finding, FindingEvidence
from app.models.processing_event import ProcessingEvent
from app.models.question import Question
from app.models.topic import Topic
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.schemas.analysis import AnalysisCreateRequest, AnalysisResponse
from app.schemas.assessment_record import AssessmentRecordResponse
from app.schemas.clo import CloResponse
from app.schemas.course import CourseInput
from app.schemas.finding import FindingResponse
from app.schemas.progress import ProgressResponse
from app.schemas.question import QuestionResponse
from app.schemas.recommendation import RecommendationResponse
from app.schemas.score import AnalysisScoreResponse
from app.schemas.topic import TopicResponse
from app.schemas.uploaded_file import UploadedFileResponse
from app.services.knowledge_base.reference_data import (
    get_recommendations_for,
    get_requirement_display,
)
from app.services.processing.runner import run_analysis_pipeline
from app.services.storage.files import UploadTooLargeError, stream_validate_and_store
from app.services.storage.keys import resolve_storage_path
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

    background_tasks.add_task(run_analysis_pipeline, analysis.id)
    return AnalysisResponse.from_model(_load_with_relations(db, analysis.id))


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
        for display in get_recommendations_for(source_dir, finding.rule_id, finding.status)
    ]
