from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.deps import get_owned_report
from app.core.config import Settings, get_settings
from app.models.report import Report
from app.schemas.report import ReportResponse
from app.services.storage.keys import resolve_storage_path

router = APIRouter(prefix="/reports", tags=["reports"])


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
