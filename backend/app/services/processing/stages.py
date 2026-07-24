"""Per-stage pipeline handlers.

Milestone 3 wired the stage machine and job runner with no-op placeholders.
Milestone 4 replaced run_extracting_exam with real digital-PDF extraction
and persistence. Milestone 5 replaces run_extracting_tp153 the same way.
Milestone 6 replaced run_applying_rules with marks/total and numbering
rules; Milestone 8 added deterministic CLO/topic alignment and coverage.
The semantic/RAG continuation completes versioned KB indexing and adds the
approved RULE002/RULE004/RULE008 semantic evaluators to that same stage.

The M8 correction remains intact for deterministic evaluation:
REQ006/RULE006 (CLO Coverage Distribution) is genuinely
deterministic only for 0 or 1 applicable CLOs; evaluate_clo_coverage_distribution
returns None for 2+, and this stage skips persistence in that case rather
than inventing a judgment. The approved semantic continuation is limited to
RULE002, RULE004, and RULE008; it does not release a RULE006 evaluator.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.domain import ProcessingStage, UploadedFileType
from app.models.analysis import Analysis
from app.models.clo import Clo
from app.models.evidence import Evidence
from app.models.question import Question
from app.models.topic import Topic
from app.services.extraction.digital_pdf_extractor import PdfPlumberExamExtractor
from app.services.extraction.digital_tp153_extractor import PdfPlumberTp153Extractor
from app.services.extraction.persistence import persist_extraction_result
from app.services.extraction.tp153_persistence import persist_tp153_extraction_result
from app.services.extraction.types import ExtractionError
from app.services.knowledge_base.runtime import get_semantic_runtime
from app.services.rules.clo_topic_alignment import (
    evaluate_question_to_clo_mapping,
    evaluate_question_to_topic_alignment,
)
from app.services.rules.clo_topic_coverage import (
    evaluate_applicable_clo_coverage,
    evaluate_applicable_topic_coverage,
    evaluate_clo_coverage_distribution,
)
from app.services.rules.identifiers import (
    APPLICABLE_CLO_COVERAGE,
    APPLICABLE_TOPIC_COVERAGE,
    CLO_COVERAGE_DISTRIBUTION,
    CLO_RELEVANCE,
    MARKS_AND_TOTAL,
    NUMBERING,
    OUT_OF_SCOPE_CONTENT,
    QUESTION_FORMAT_SUITABILITY,
    QUESTION_TO_CLO_MAPPING,
    QUESTION_TO_TOPIC_ALIGNMENT,
    RuleIdentifier,
)
from app.services.rules.marks_total import evaluate_marks_and_total
from app.services.rules.numbering import evaluate_numbering
from app.services.rules.persistence import persist_finding, persist_semantic_finding
from app.services.rules.semantic_evaluators import evaluate_approved_semantic_rules
from app.services.storage.keys import resolve_storage_path

# The RuleIdentifiers run_applying_rules actually evaluates at runtime.
# Read by tests to confirm the capability manifest's SUPPORTED/
# PARTIALLY_SUPPORTED entries correspond to real pipeline capabilities,
# without needing fragile source-text inspection of this module.
RUNTIME_RULE_IDENTIFIERS: tuple[RuleIdentifier, ...] = (
    MARKS_AND_TOTAL,
    NUMBERING,
    QUESTION_TO_CLO_MAPPING,
    APPLICABLE_CLO_COVERAGE,
    CLO_COVERAGE_DISTRIBUTION,
    QUESTION_TO_TOPIC_ALIGNMENT,
    APPLICABLE_TOPIC_COVERAGE,
    CLO_RELEVANCE,
    QUESTION_FORMAT_SUITABILITY,
    OUT_OF_SCOPE_CONTENT,
)


def run_validating(analysis: Analysis, session: Session, settings: Settings) -> None:
    """Confirms both already-upload-validated source artifacts still exist."""
    for file_type in (UploadedFileType.EXAM, UploadedFileType.TP153):
        uploaded = next((item for item in analysis.files if item.file_type == file_type), None)
        if uploaded is None:
            raise ExtractionError(f"No {file_type.value} file is associated with this analysis.")
        if not resolve_storage_path(settings.upload_root, uploaded.storage_key).is_file():
            raise ExtractionError(f"The stored {file_type.value} file is unavailable.")


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
    """Adds a traceable absence record when no exam question text was extracted."""
    existing = session.execute(
        select(Evidence)
        .where(
            Evidence.analysis_id == analysis.id,
            Evidence.evidence_type == "question_text",
        )
        .limit(1)
    ).scalar_one_or_none()
    if existing is not None:
        return
    missing = session.execute(
        select(Evidence).where(
            Evidence.analysis_id == analysis.id,
            Evidence.evidence_type == "missing_semantic_input",
            Evidence.item_reference == "questions",
        )
    ).scalar_one_or_none()
    if missing is None:
        session.add(
            Evidence(
                analysis_id=analysis.id,
                source_document=UploadedFileType.EXAM,
                evidence_type="missing_semantic_input",
                page_number=1,
                item_reference="questions",
                extracted_text="No readable question text was extracted from the exam.",
                geometry=None,
                confidence=0.0,
            )
        )
        session.flush()


def run_retrieving_knowledge(analysis: Analysis, session: Session, settings: Settings) -> None:
    """Validates, normalizes, and version-safely indexes the controlled KB."""
    get_semantic_runtime(settings).ensure_index()


def run_applying_rules(analysis: Analysis, session: Session, settings: Settings) -> None:
    """Runs the M6 deterministic, exam-internal rules (marks/total
    arithmetic and numbering) and the M8 deterministic CLO/topic alignment
    and coverage rules, followed by the three approved semantic evaluators.
    It persists one Finding per rule that genuinely produces one - RULE006
    persists no Finding at all when 2+ CLOs are applicable (see module
    docstring). Report generation remains outside this rule stage."""
    questions = (
        session.execute(select(Question).where(Question.analysis_id == analysis.id)).scalars().all()
    )
    exam_evidence = (
        session.execute(
            select(Evidence).where(
                Evidence.analysis_id == analysis.id,
                Evidence.source_document == UploadedFileType.EXAM,
            )
        )
        .scalars()
        .all()
    )

    marks_result = evaluate_marks_and_total(questions, exam_evidence)
    persist_finding(session, analysis.id, MARKS_AND_TOTAL, marks_result)

    numbering_result = evaluate_numbering(questions, exam_evidence)
    persist_finding(session, analysis.id, NUMBERING, numbering_result)

    tp153_evidence = (
        session.execute(
            select(Evidence).where(
                Evidence.analysis_id == analysis.id,
                Evidence.source_document == UploadedFileType.TP153,
            )
        )
        .scalars()
        .all()
    )
    clos = session.execute(select(Clo).where(Clo.analysis_id == analysis.id)).scalars().all()
    topics = session.execute(select(Topic).where(Topic.analysis_id == analysis.id)).scalars().all()

    # Question text (exam evidence) and CLO/topic evidence (TP-153 evidence)
    # are both needed - question_text rows only exist under EXAM.
    combined_evidence = [*exam_evidence, *tp153_evidence]

    clo_mapping_result = evaluate_question_to_clo_mapping(questions, combined_evidence, clos)
    persist_finding(session, analysis.id, QUESTION_TO_CLO_MAPPING, clo_mapping_result)

    clo_coverage_result = evaluate_applicable_clo_coverage(questions, combined_evidence, clos)
    persist_finding(session, analysis.id, APPLICABLE_CLO_COVERAGE, clo_coverage_result)

    topic_alignment_result = evaluate_question_to_topic_alignment(
        questions, combined_evidence, topics
    )
    persist_finding(session, analysis.id, QUESTION_TO_TOPIC_ALIGNMENT, topic_alignment_result)

    topic_coverage_result = evaluate_applicable_topic_coverage(questions, combined_evidence, topics)
    persist_finding(session, analysis.id, APPLICABLE_TOPIC_COVERAGE, topic_coverage_result)

    # None (2+ applicable CLOs) means no genuine judgment is possible - skip
    # persistence rather than record an unconditional Not Verified Finding.
    clo_distribution_result = evaluate_clo_coverage_distribution(combined_evidence, clos)
    if clo_distribution_result is not None:
        persist_finding(session, analysis.id, CLO_COVERAGE_DISTRIBUTION, clo_distribution_result)

    runtime = get_semantic_runtime(settings)
    runtime.ensure_index()
    semantic_results = evaluate_approved_semantic_rules(
        analysis,
        session,
        runtime,
        Path(settings.kb_source_dir).resolve(),
        validation_retries=settings.ai_validation_retries,
    )
    for result in semantic_results:
        persist_semantic_finding(session, analysis.id, result)


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
