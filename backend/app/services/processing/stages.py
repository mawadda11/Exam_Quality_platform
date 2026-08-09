"""Per-stage pipeline handlers for the reviewed hybrid workflow.

M3-M5 split processing at the source-faithful review boundary. M6-M9 build
confirmed evidence, retrieve governed KB context, execute ten constrained
semantic evaluators, and deterministically aggregate CLO/topic coverage.
RULE006 remains conservative: zero and one applicable CLO have governed
outcomes; two or more applicable CLOs produce no Finding because the KB does
not define a concentration threshold.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.domain import AcademicStatus, ProcessingStage, QuestionPreparationMode, UploadedFileType
from app.models.analysis import Analysis
from app.models.clo import Clo
from app.models.evidence import Evidence
from app.models.question import Question
from app.models.uploaded_file import UploadedFile
from app.schemas.extraction_review import ExtractionReviewSnapshot
from app.services.ai.analysis_routing import (
    analysis_ai_route,
    build_analysis_semantic_provider,
    record_analysis_ai_route,
)
from app.services.extraction.digital_pdf_extractor import PdfPlumberExamExtractor
from app.services.extraction.digital_tp153_extractor import PdfPlumberTp153Extractor
from app.services.extraction.document_ocr import create_document_ocr_provider
from app.services.extraction.exam_structure import (
    apply_exam_structure_parser,
    create_exam_structure_parser,
)
from app.services.extraction.persistence import persist_extraction_result
from app.services.extraction.preparation_mode import encode_question_preparation_mode
from app.services.extraction.reference_adjudication import adjudicate_nonexplicit_references
from app.services.extraction.review_snapshot import materialize_initial_review_revision
from app.services.extraction.tp153_persistence import persist_tp153_extraction_result
from app.services.extraction.types import ExtractionError, PageExtractionDiagnostic
from app.services.knowledge_base.runtime import get_semantic_runtime
from app.services.rules.clo_topic_coverage import (
    evaluate_applicable_clo_coverage_from_relationships,
    evaluate_applicable_topic_coverage_from_relationships,
    evaluate_clo_coverage_distribution,
)
from app.services.rules.identifiers import (
    APPLICABLE_CLO_COVERAGE,
    APPLICABLE_TOPIC_COVERAGE,
    ASSESSMENT_METHOD_CONSISTENCY,
    CLEAR_TASK_STATEMENT,
    CLO_COVERAGE_DISTRIBUTION,
    CLO_RELEVANCE,
    COMPLETE_INSTRUCTIONS,
    COMPLETE_QUESTION_INFORMATION,
    MARKS_AND_TOTAL,
    NUMBERING,
    OUT_OF_SCOPE_CONTENT,
    QUESTION_FORMAT_SUITABILITY,
    QUESTION_TO_CLO_MAPPING,
    QUESTION_TO_TOPIC_ALIGNMENT,
    REFERENCED_MATERIAL_AVAILABILITY,
    RESOLVABLE_CROSS_REFERENCES,
    SUPPORTING_MATERIAL_ASSOCIATION,
    UNAMBIGUOUS_WORDING,
    RuleIdentifier,
)
from app.services.rules.marks_total import evaluate_marks_and_total
from app.services.rules.numbering import evaluate_numbering
from app.services.rules.persistence import persist_finding, persist_semantic_finding
from app.services.rules.semantic_evaluators import (
    evaluate_semantic_judgment_rules,
    evaluate_semantic_relationship_rules,
)
from app.services.rules.structured_evidence import (
    evaluate_referenced_material_availability,
    evaluate_resolvable_cross_references,
    evaluate_supporting_material_association,
)
from app.services.rules.versioning import batch4_structured_rules_enabled
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
    ASSESSMENT_METHOD_CONSISTENCY,
    QUESTION_FORMAT_SUITABILITY,
    OUT_OF_SCOPE_CONTENT,
    CLEAR_TASK_STATEMENT,
    UNAMBIGUOUS_WORDING,
    COMPLETE_QUESTION_INFORMATION,
    COMPLETE_INSTRUCTIONS,
    REFERENCED_MATERIAL_AVAILABILITY,
    SUPPORTING_MATERIAL_ASSOCIATION,
    RESOLVABLE_CROSS_REFERENCES,
)


def _record_extraction_metadata(
    uploaded_file: UploadedFile,
    *,
    document_language: str,
    diagnostics: list[PageExtractionDiagnostic],
    parser_layout: str | None = None,
) -> None:
    methods = {item.extraction_method for item in diagnostics}
    if len(methods) == 1:
        extraction_method = next(iter(methods))
    elif methods:
        extraction_method = "mixed"
    else:
        extraction_method = None

    average_confidence = (
        sum(item.text_quality_confidence for item in diagnostics) / len(diagnostics)
        if diagnostics
        else None
    )
    uploaded_file.detected_language = document_language
    uploaded_file.extraction_method = extraction_method
    uploaded_file.extraction_confidence = (
        round(average_confidence, 4) if average_confidence is not None else None
    )
    uploaded_file.review_recommended = any(item.review_recommended for item in diagnostics)
    uploaded_file.parser_layout = parser_layout


class ReviewConfirmationRequiredError(RuntimeError):
    """Raised when a post-confirmation stage is invoked before confirmation."""


def require_confirmed_review(analysis: Analysis) -> None:
    """Central governance guard for every post-confirmation pipeline stage."""
    if analysis.confirmed_review_id is None:
        raise ReviewConfirmationRequiredError(
            "A confirmed extraction review is required before downstream processing."
        )


def run_validating(analysis: Analysis, session: Session, settings: Settings) -> None:
    """Confirms both already-upload-validated source artifacts still exist."""
    for file_type in (UploadedFileType.EXAM, UploadedFileType.TP153):
        uploaded = next((item for item in analysis.files if item.file_type == file_type), None)
        if uploaded is None:
            raise ExtractionError(f"No {file_type.value} file is associated with this analysis.")
        if not resolve_storage_path(settings.upload_root, uploaded.storage_key).is_file():
            raise ExtractionError(f"The stored {file_type.value} file is unavailable.")


def run_extracting_exam(
    analysis: Analysis,
    session: Session,
    settings: Settings,
    *,
    preparation_mode: QuestionPreparationMode = QuestionPreparationMode.ASSISTED_PDF,
) -> None:
    exam_file = next((f for f in analysis.files if f.file_type == UploadedFileType.EXAM), None)
    if exam_file is None:
        # POST /run already requires ready_for_analysis, so this should not
        # happen in practice - treated as an extraction failure, not a
        # separate special case, so it still yields the same safe message.
        raise ExtractionError("No exam file is associated with this analysis.")

    pdf_path = resolve_storage_path(settings.upload_root, exam_file.storage_key)
    ocr_provider = create_document_ocr_provider(settings)
    result = PdfPlumberExamExtractor(document_ocr_provider=ocr_provider).extract(pdf_path)
    if preparation_mode is QuestionPreparationMode.ASSISTED_PDF:
        result = apply_exam_structure_parser(
            result,
            create_exam_structure_parser(
                settings,
                initial_tier=analysis_ai_route(session, analysis.id),
                on_route_changed=lambda tier: record_analysis_ai_route(
                    session,
                    analysis_id=analysis.id,
                    stage=ProcessingStage.EXTRACTING_EXAM,
                    tier=tier,
                ),
            ),
            pdf_path=pdf_path,
        )
    else:
        # Manual and structured-template modes keep the immutable PDF, page
        # diagnostics, and visible materials but deliberately create no
        # automatic question facts. Questions are added in Extraction Review.
        result = replace(
            result,
            questions=[],
            evidence=[
                item
                for item in result.evidence
                if item.question_number_label is None
                and item.evidence_type not in {
                    "question_text",
                    "question_source_spans",
                    "marks",
                }
            ],
            supporting_materials=[
                replace(item, question_number_label=None, question_local_key=None)
                for item in result.supporting_materials
            ],
            document_references=[],
            reconciliation_warnings=[],
            structure_candidates=[],
        )
    persist_extraction_result(session, analysis.id, result)
    adjudicate_nonexplicit_references(session, analysis.id, settings)
    _record_extraction_metadata(
        exam_file,
        document_language=result.document_language.value,
        diagnostics=result.page_diagnostics,
        parser_layout=encode_question_preparation_mode(preparation_mode),
    )


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
    _record_extraction_metadata(
        tp153_file,
        document_language=result.document_language.value,
        diagnostics=result.page_diagnostics,
        parser_layout=result.layout_family,
    )


def run_building_evidence(analysis: Analysis, session: Session, settings: Settings) -> None:
    """Build deterministic post-confirmation evidence required by M6-M9."""

    require_confirmed_review(analysis)

    exam_type_evidence = session.execute(
        select(Evidence).where(
            Evidence.analysis_id == analysis.id,
            Evidence.evidence_type == "exam_metadata",
            Evidence.item_reference == "exam_type",
        )
    ).scalar_one_or_none()
    if exam_type_evidence is None:
        session.add(
            Evidence(
                analysis_id=analysis.id,
                source_document=UploadedFileType.EXAM,
                evidence_type="exam_metadata",
                page_number=1,
                item_reference="exam_type",
                extracted_text=f"Exam type: {analysis.exam_type.value}",
                geometry=None,
                confidence=1.0,
            )
        )

    existing_question = session.execute(
        select(Evidence)
        .where(
            Evidence.analysis_id == analysis.id,
            Evidence.evidence_type == "question_text",
        )
        .limit(1)
    ).scalar_one_or_none()
    if existing_question is None:
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
    require_confirmed_review(analysis)
    get_semantic_runtime(settings).ensure_index()


def run_applying_rules(analysis: Analysis, session: Session, settings: Settings) -> None:
    """Run the governed M6-M9 hybrid evaluation in approved order."""

    require_confirmed_review(analysis)
    questions = (
        session.execute(select(Question).where(Question.analysis_id == analysis.id)).scalars().all()
    )
    evidence = (
        session.execute(select(Evidence).where(Evidence.analysis_id == analysis.id)).scalars().all()
    )

    persist_finding(
        session,
        analysis.id,
        MARKS_AND_TOTAL,
        evaluate_marks_and_total(questions, evidence),
    )
    persist_finding(
        session,
        analysis.id,
        NUMBERING,
        evaluate_numbering(questions, evidence),
    )
    if batch4_structured_rules_enabled(analysis):
        assert analysis.confirmed_review is not None
        confirmed_snapshot = ExtractionReviewSnapshot.model_validate_json(
            json.dumps(analysis.confirmed_review.snapshot)
        )
        confirmed_revision_id = analysis.confirmed_review_id
        assert confirmed_revision_id is not None
        structured_results = (
            (
                REFERENCED_MATERIAL_AVAILABILITY,
                evaluate_referenced_material_availability(
                    session,
                    analysis_id=analysis.id,
                    snapshot=confirmed_snapshot,
                    confirmed_revision_id=confirmed_revision_id,
                ),
            ),
            (
                SUPPORTING_MATERIAL_ASSOCIATION,
                evaluate_supporting_material_association(
                    session,
                    analysis_id=analysis.id,
                    snapshot=confirmed_snapshot,
                    confirmed_revision_id=confirmed_revision_id,
                ),
            ),
            (
                RESOLVABLE_CROSS_REFERENCES,
                evaluate_resolvable_cross_references(
                    session,
                    analysis_id=analysis.id,
                    snapshot=confirmed_snapshot,
                    confirmed_revision_id=confirmed_revision_id,
                ),
            ),
        )
        for identifier, structured_result in structured_results:
            persist_finding(session, analysis.id, identifier, structured_result)

    runtime = get_semantic_runtime(settings)
    routed_provider = build_analysis_semantic_provider(
        settings,
        session,
        analysis_id=analysis.id,
        stage=ProcessingStage.APPLYING_RULES,
    )
    if routed_provider is not None:
        runtime = runtime.with_provider(routed_provider)
    runtime.ensure_index()
    kb_source_dir = Path(settings.kb_source_dir).resolve()

    clo_mapping, topic_mapping = evaluate_semantic_relationship_rules(
        analysis,
        session,
        runtime,
        kb_source_dir,
        validation_retries=settings.ai_validation_retries,
    )
    # Final pilot philosophy: material-reference quality is reported in its own
    # governed dimension. It must not automatically downgrade or suppress a
    # semantic CLO/topic judgment when the readable question text itself can
    # still be evaluated. The semantic evaluator keeps responsibility for its
    # own confidence/status; reference defects remain visible separately.
    persist_semantic_finding(session, analysis.id, clo_mapping)
    persist_semantic_finding(session, analysis.id, topic_mapping)

    persist_finding(
        session,
        analysis.id,
        APPLICABLE_CLO_COVERAGE,
        evaluate_applicable_clo_coverage_from_relationships(evidence, clo_mapping),
    )
    persist_finding(
        session,
        analysis.id,
        APPLICABLE_TOPIC_COVERAGE,
        evaluate_applicable_topic_coverage_from_relationships(evidence, topic_mapping),
    )

    clos = session.execute(select(Clo).where(Clo.analysis_id == analysis.id)).scalars().all()
    clo_distribution_result = evaluate_clo_coverage_distribution(evidence, clos)
    if clo_distribution_result is not None:
        persist_finding(session, analysis.id, CLO_COVERAGE_DISTRIBUTION, clo_distribution_result)

    semantic_results = evaluate_semantic_judgment_rules(
        analysis,
        session,
        runtime,
        kb_source_dir,
        validation_retries=settings.ai_validation_retries,
    )
    for semantic_result in semantic_results:
        if semantic_result.identifier == OUT_OF_SCOPE_CONTENT:
            # Pilot scope decision: "no supported topic relationship" does not
            # prove that content is outside the course. Keep the question-to-
            # topic suggestions for faculty review, but exclude an automated
            # out-of-scope judgment from scoring unless a future governed
            # positive-evidence method is added.
            semantic_result = replace(
                semantic_result,
                status=AcademicStatus.NOT_APPLICABLE,
                explanation=(
                    "Automated out-of-scope scoring is outside the current pilot scope. "
                    "Review the question-to-topic suggestions in Alignment & Coverage."
                ),
                recommendation_id=None,
            )
        # Complete Information is judged from the question itself. Missing or
        # duplicate supporting material is scored once by RULE014 rather than
        # being propagated into a second penalty here.
        persist_semantic_finding(session, analysis.id, semantic_result)


def run_generating_report(analysis: Analysis, session: Session, settings: Settings) -> None:
    """Placeholder. A future milestone implements report generation here."""
    require_confirmed_review(analysis)


def run_materializing_review(analysis: Analysis, session: Session, _settings: Settings) -> None:
    """Create the immutable source-faithful initial review revision."""
    materialize_initial_review_revision(session, analysis.id)


STAGE_HANDLERS: dict[ProcessingStage, Callable[[Analysis, Session, Settings], None]] = {
    ProcessingStage.VALIDATING: run_validating,
    ProcessingStage.EXTRACTING_EXAM: run_extracting_exam,
    ProcessingStage.EXTRACTING_TP153: run_extracting_tp153,
    ProcessingStage.BUILDING_EVIDENCE: run_building_evidence,
    ProcessingStage.RETRIEVING_KNOWLEDGE: run_retrieving_knowledge,
    ProcessingStage.APPLYING_RULES: run_applying_rules,
    ProcessingStage.GENERATING_REPORT: run_generating_report,
}

PRE_REVIEW_STAGES: tuple[ProcessingStage, ...] = (
    ProcessingStage.VALIDATING,
    ProcessingStage.EXTRACTING_EXAM,
    ProcessingStage.EXTRACTING_TP153,
)

POST_CONFIRMATION_STAGES: tuple[ProcessingStage, ...] = (
    ProcessingStage.BUILDING_EVIDENCE,
    ProcessingStage.RETRIEVING_KNOWLEDGE,
    ProcessingStage.APPLYING_RULES,
    ProcessingStage.GENERATING_REPORT,
)
