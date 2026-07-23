"""Per-stage pipeline handlers.

Milestone 3 wired the stage machine and job runner with no-op placeholders.
Milestone 4 replaced run_extracting_exam with real digital-PDF extraction
and persistence. Milestone 5 replaces run_extracting_tp153 the same way.
Milestone 6 replaces run_applying_rules with the marks/total and numbering
deterministic rules; Milestone 8 extends the same stage with deterministic
CLO/topic alignment and coverage rules, plus three official rules that
always report Not Verified (or, for one, Not Applicable) because they need
semantic judgment or an undefined threshold M8 does not attempt. KB
retrieval, assessment-method consistency, real semantic evaluation,
recommendations, and report generation remain placeholders for later
milestones.
"""

from __future__ import annotations

from collections.abc import Callable

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
from app.services.rules.clo_topic_alignment import (
    evaluate_question_to_clo_mapping,
    evaluate_question_to_topic_alignment,
)
from app.services.rules.clo_topic_coverage import (
    evaluate_applicable_clo_coverage,
    evaluate_applicable_topic_coverage,
)
from app.services.rules.identifiers import (
    APPLICABLE_CLO_COVERAGE,
    APPLICABLE_TOPIC_COVERAGE,
    CLO_COVERAGE_DISTRIBUTION,
    CLO_RELEVANCE,
    MARKS_AND_TOTAL,
    NUMBERING,
    OUT_OF_SCOPE_CONTENT,
    QUESTION_TO_CLO_MAPPING,
    QUESTION_TO_TOPIC_ALIGNMENT,
)
from app.services.rules.marks_total import evaluate_marks_and_total
from app.services.rules.numbering import evaluate_numbering
from app.services.rules.persistence import persist_finding
from app.services.rules.semantic_deferred import (
    evaluate_clo_coverage_distribution,
    evaluate_clo_relevance,
    evaluate_out_of_scope_content,
)
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
    """Runs the M6 deterministic, exam-internal rules (marks/total
    arithmetic and numbering), the M8 deterministic CLO/topic alignment and
    coverage rules, and the three M8 rules that require semantic judgment
    or an undefined threshold (always Not Verified, or Not Applicable for a
    single applicable CLO) - nine findings total. KB retrieval,
    assessment-method consistency, real semantic evaluation,
    recommendations, and report generation remain placeholders for later
    milestones."""
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

    clo_relevance_result = evaluate_clo_relevance(questions, combined_evidence, clos)
    persist_finding(session, analysis.id, CLO_RELEVANCE, clo_relevance_result)

    clo_distribution_result = evaluate_clo_coverage_distribution(questions, combined_evidence, clos)
    persist_finding(session, analysis.id, CLO_COVERAGE_DISTRIBUTION, clo_distribution_result)

    out_of_scope_result = evaluate_out_of_scope_content(questions, combined_evidence, topics)
    persist_finding(session, analysis.id, OUT_OF_SCOPE_CONTENT, out_of_scope_result)


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
