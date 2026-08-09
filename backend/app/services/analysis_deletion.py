"""Owned-analysis deletion with guarded state and best-effort artifact cleanup."""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.core.domain import ProcessingStage
from app.models.analysis import Analysis
from app.models.extraction_review_revision import ExtractionReviewRevision
from app.services.storage.keys import resolve_storage_path

logger = logging.getLogger(__name__)

DELETABLE_STATES = {
    ProcessingStage.QUEUED,
    ProcessingStage.REVIEW_READY,
    ProcessingStage.COMPLETED,
    ProcessingStage.FAILED,
}


class AnalysisDeletionConflictError(RuntimeError):
    """Safe deletion conflict suitable for a 409 response."""


def _remove_artifact(path: Path, *, analysis_id: object) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.warning("Could not remove one analysis artifact for analysis %s.", analysis_id)
        return

    parent = path.parent
    try:
        parent.rmdir()
    except OSError:
        pass


def delete_analysis(session: Session, analysis: Analysis, settings: Settings) -> None:
    """Delete one analysis and only its server-resolved owned artifacts.

    Physical cleanup is intentionally best effort: a missing or locked file
    never restores database rows or exposes a private server path.
    """

    if analysis.state not in DELETABLE_STATES:
        raise AnalysisDeletionConflictError(
            "This analysis cannot be deleted while processing is active."
        )

    successor_exists = session.execute(
        select(Analysis.id).where(Analysis.predecessor_analysis_id == analysis.id).limit(1)
    ).scalar_one_or_none()
    if successor_exists is not None:
        raise AnalysisDeletionConflictError(
            "This historical analysis is retained because a reanalysis references it."
        )

    persisted = session.execute(
        select(Analysis)
        .where(Analysis.id == analysis.id)
        .options(selectinload(Analysis.files), selectinload(Analysis.reports))
    ).scalar_one()
    upload_paths = [
        resolve_storage_path(settings.upload_root, item.storage_key) for item in persisted.files
    ]
    extraction_cache_paths = [
        path.with_name(f".{path.name}.gemini-structure-cache.json") for path in upload_paths
    ]
    report_paths = [
        resolve_storage_path(settings.report_root, item.storage_key) for item in persisted.reports
    ]

    # Break the intentional circular link before deleting immutable revisions.
    persisted.confirmed_review_id = None
    session.flush()
    session.query(ExtractionReviewRevision).filter(
        ExtractionReviewRevision.analysis_id == persisted.id
    ).delete(synchronize_session=False)
    session.delete(persisted)
    session.flush()

    for path in (*upload_paths, *extraction_cache_paths, *report_paths):
        _remove_artifact(path, analysis_id=persisted.id)
    logger.info("Deleted analysis %s and completed best-effort artifact cleanup.", persisted.id)
