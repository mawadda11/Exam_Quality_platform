"""Per-stage pipeline handlers.

Milestone 3 wired the stage machine and job runner with no-op placeholders.
Milestone 4 replaced run_extracting_exam with real digital-PDF extraction
and persistence. Milestone 5 replaces run_extracting_tp153 the same way.
Every other stage remains a placeholder for a later milestone to replace.
"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.domain import ProcessingStage, UploadedFileType
from app.models.analysis import Analysis
from app.services.extraction.digital_pdf_extractor import PdfPlumberExamExtractor
from app.services.extraction.digital_tp153_extractor import PdfPlumberTp153Extractor
from app.services.extraction.persistence import persist_extraction_result
from app.services.extraction.tp153_persistence import persist_tp153_extraction_result
from app.services.extraction.types import ExtractionError
from app.services.storage.keys import resolve_storage_path


def run_validating(analysis: Analysis, session: Session, settings: Settings) -> None:
    """Placeholder. A future milestone may add deeper content validation here."""


def run_extracting_exam(analysis: Analysis, session: Session, settings: Settings) -> None:
    exam_file = next((f for f in analysis.files if f.file_type == UploadedFileType.EXAM), None)
    if exam_file is None:
        # POST /run already requires ready_for_analysis, so this should not
        # happen in practice - treated as an extraction failure, not a
        # separate special case, so it still yields the same safe message.
        raise ExtractionError("No exam file is associated with this analysis.")

    pdf_path = resolve_storage_path(settings.upload_root, exam_file.storage_key)
    result = PdfPlumberExamExtractor().extract(pdf_path)
    persist_extraction_result(session, analysis.id, result)


def run_extracting_tp153(analysis: Analysis, session: Session, settings: Settings) -> None:
    tp153_file = next((f for f in analysis.files if f.file_type == UploadedFileType.TP153), None)
    if tp153_file is None:
        # Same reasoning as run_extracting_exam: /run already requires
        # ready_for_analysis, so this is an extraction failure, not a
        # separate special case.
        raise ExtractionError("No TP-153 file is associated with this analysis.")

    pdf_path = resolve_storage_path(settings.upload_root, tp153_file.storage_key)
    result = PdfPlumberTp153Extractor().extract(pdf_path)
    persist_tp153_extraction_result(session, analysis.id, result)


def run_building_evidence(analysis: Analysis, session: Session, settings: Settings) -> None:
    """Placeholder. A future milestone persists extracted evidence records here."""


def run_retrieving_knowledge(analysis: Analysis, session: Session, settings: Settings) -> None:
    """Placeholder. A future milestone implements knowledge-base retrieval here."""


def run_applying_rules(analysis: Analysis, session: Session, settings: Settings) -> None:
    """Placeholder. A future milestone implements the rule engine here."""


def run_generating_report(analysis: Analysis, session: Session, settings: Settings) -> None:
    """Placeholder. A future milestone implements report generation here."""


STAGE_HANDLERS: dict[ProcessingStage, Callable[[Analysis, Session, Settings], None]] = {
    ProcessingStage.VALIDATING: run_validating,
    ProcessingStage.EXTRACTING_EXAM: run_extracting_exam,
    ProcessingStage.EXTRACTING_TP153: run_extracting_tp153,
    ProcessingStage.BUILDING_EVIDENCE: run_building_evidence,
    ProcessingStage.RETRIEVING_KNOWLEDGE: run_retrieving_knowledge,
    ProcessingStage.APPLYING_RULES: run_applying_rules,
    ProcessingStage.GENERATING_REPORT: run_generating_report,
}

WORK_STAGES: tuple[ProcessingStage, ...] = (
    ProcessingStage.VALIDATING,
    ProcessingStage.EXTRACTING_EXAM,
    ProcessingStage.EXTRACTING_TP153,
    ProcessingStage.BUILDING_EVIDENCE,
    ProcessingStage.RETRIEVING_KNOWLEDGE,
    ProcessingStage.APPLYING_RULES,
    ProcessingStage.GENERATING_REPORT,
)
