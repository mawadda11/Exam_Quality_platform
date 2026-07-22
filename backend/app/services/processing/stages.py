"""Per-stage pipeline handlers.

Milestone 3 wires the stage machine and job runner only - every handler below
is a placeholder. Later milestones replace each one with real work; the
function names and signatures are the seam they plug into.
"""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from app.core.domain import ProcessingStage
from app.models.analysis import Analysis


def run_validating(analysis: Analysis, session: Session) -> None:
    """Placeholder. A future milestone may add deeper content validation here."""


def run_extracting_exam(analysis: Analysis, session: Session) -> None:
    """Placeholder. Milestone 4 implements digital-PDF/OCR extraction here."""


def run_extracting_tp153(analysis: Analysis, session: Session) -> None:
    """Placeholder. A future milestone implements TP-153 parsing here."""


def run_building_evidence(analysis: Analysis, session: Session) -> None:
    """Placeholder. A future milestone persists extracted evidence records here."""


def run_retrieving_knowledge(analysis: Analysis, session: Session) -> None:
    """Placeholder. A future milestone implements knowledge-base retrieval here."""


def run_applying_rules(analysis: Analysis, session: Session) -> None:
    """Placeholder. A future milestone implements the rule engine here."""


def run_generating_report(analysis: Analysis, session: Session) -> None:
    """Placeholder. A future milestone implements report generation here."""


STAGE_HANDLERS: dict[ProcessingStage, Callable[[Analysis, Session], None]] = {
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
