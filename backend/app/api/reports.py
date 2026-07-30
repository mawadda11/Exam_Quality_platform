from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import String, and_, cast, func, not_, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.api.deps import get_current_user, get_owned_report
from app.core.config import Settings, get_settings
from app.core.domain import ExamType, ProcessingStage, ReportLanguage
from app.db.session import get_db
from app.models.analysis import Analysis
from app.models.course import Course
from app.models.report import Report
from app.models.user import User
from app.schemas.report import (
    ReportLibraryAnalysisResponse,
    ReportLibraryItemResponse,
    ReportLibraryPageResponse,
    ReportLibrarySort,
    ReportLibraryStatus,
    ReportResponse,
)
from app.services.storage.keys import resolve_storage_path

router = APIRouter(prefix="/reports", tags=["reports"])


def _outdated_condition() -> ColumnElement[bool]:
    return and_(
        Report.id.is_not(None),
        Report.capability_version.is_not(None),
        Analysis.capability_version.is_not(None),
        Report.capability_version != Analysis.capability_version,
    )


def _library_status(analysis: Analysis, report: Report | None) -> ReportLibraryStatus:
    if report is None:
        return "not_generated"
    if (
        report.capability_version is not None
        and analysis.capability_version is not None
        and report.capability_version != analysis.capability_version
    ):
        return "outdated"
    if report.score is None:
        return "insufficient_evidence"
    return "available"


@router.get("", response_model=ReportLibraryPageResponse)
def list_report_library(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    query: Annotated[str | None, Query(alias="q", max_length=100)] = None,
    status_filter: Annotated[ReportLibraryStatus | None, Query(alias="status")] = None,
    exam_type: ExamType | None = None,
    language: ReportLanguage | None = None,
    sort: ReportLibrarySort = "newest",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 12,
) -> ReportLibraryPageResponse:
    """Bounded, owner-filtered report-library metadata.

    Successful immutable report snapshots remain separate rows. An owned
    analysis with no report contributes one neutral ``not_generated`` row so
    faculty can generate its first report without an unbounded N+1 client
    request. No storage key, digest, local path, or owner identifier is
    exposed.
    """

    filters: list[ColumnElement[bool]] = [
        Analysis.user_id == current_user.id,
        Analysis.state == ProcessingStage.COMPLETED,
    ]
    outdated = _outdated_condition()

    if query and (normalized_query := query.strip()):
        pattern = f"%{normalized_query.lower()}%"
        search_predicates: list[ColumnElement[bool]] = [
            func.lower(Course.code).like(pattern),
            func.lower(Course.name).like(pattern),
            func.lower(Analysis.term).like(pattern),
            func.lower(cast(Report.id, String)).like(pattern),
        ]
        try:
            search_predicates.append(Report.id == UUID(normalized_query))
        except ValueError:
            pass
        filters.append(or_(*search_predicates))
    if exam_type is not None:
        filters.append(Analysis.exam_type == exam_type)
    if language is not None:
        filters.append(Report.language == language)
    if status_filter == "not_generated":
        filters.append(Report.id.is_(None))
    elif status_filter == "outdated":
        filters.append(outdated)
    elif status_filter == "insufficient_evidence":
        filters.append(and_(Report.score.is_(None), Report.id.is_not(None), not_(outdated)))
    elif status_filter == "available":
        filters.append(and_(Report.score.is_not(None), not_(outdated)))

    joined = (
        select(Analysis, Course, Report)
        .join(Course, Analysis.course_id == Course.id)
        .outerjoin(Report, Report.analysis_id == Analysis.id)
        .where(*filters)
    )
    total_statement = (
        select(func.count())
        .select_from(Analysis)
        .join(Course, Analysis.course_id == Course.id)
        .outerjoin(Report, Report.analysis_id == Analysis.id)
        .where(*filters)
    )

    library_timestamp = func.coalesce(Report.created_at, Analysis.created_at)
    ordering: tuple[Any, ...]
    if sort == "oldest":
        ordering = (library_timestamp.asc(), Analysis.id.asc(), Report.id.asc())
    elif sort == "course":
        ordering = (
            func.lower(Course.name).asc(),
            library_timestamp.desc(),
            Analysis.id.asc(),
        )
    elif sort == "score":
        ordering = (
            Report.score.desc().nulls_last(),
            library_timestamp.desc(),
            Analysis.id.asc(),
        )
    else:
        ordering = (library_timestamp.desc(), Analysis.id.desc(), Report.id.desc())

    total = int(db.execute(total_statement).scalar_one())
    rows = db.execute(
        joined.order_by(*ordering).offset((page - 1) * page_size).limit(page_size)
    ).all()

    items = [
        ReportLibraryItemResponse(
            status=_library_status(analysis, report),
            analysis=ReportLibraryAnalysisResponse(
                id=analysis.id,
                course_code=course.code,
                course_name=course.name,
                exam_type=analysis.exam_type,
                term=analysis.term,
                state=analysis.state,
                capability_version=analysis.capability_version,
                predecessor_analysis_id=analysis.predecessor_analysis_id,
                created_at=analysis.created_at,
                updated_at=analysis.updated_at,
            ),
            report=ReportResponse.model_validate(report) if report is not None else None,
        )
        for analysis, course, report in rows
    ]
    total_pages = (total + page_size - 1) // page_size if total else 0
    return ReportLibraryPageResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(report: Annotated[Report, Depends(get_owned_report)]) -> ReportResponse:
    return ReportResponse.model_validate(report)


@router.get("/{report_id}/download")
def download_report(
    report: Annotated[Report, Depends(get_owned_report)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    path = resolve_storage_path(settings.report_root, report.storage_key)
    return Response(
        content=path.read_bytes(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report-{report.id}.pdf"'},
    )
