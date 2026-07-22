from __future__ import annotations

import uuid
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
from app.models.course import Course
from app.models.processing_event import ProcessingEvent
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.schemas.analysis import AnalysisCreateRequest, AnalysisResponse
from app.schemas.course import CourseInput
from app.schemas.progress import ProgressResponse
from app.schemas.uploaded_file import UploadedFileResponse
from app.services.processing.runner import run_analysis_pipeline
from app.services.storage.files import UploadTooLargeError, stream_validate_and_store
from app.services.storage.keys import resolve_storage_path
from app.services.storage.validation import UploadValidationError

router = APIRouter(prefix="/analyses", tags=["analyses"])


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
