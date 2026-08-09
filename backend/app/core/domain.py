from enum import StrEnum


class UserType(StrEnum):
    FACULTY_MEMBER = "Faculty Member"


class ExamType(StrEnum):
    MIDTERM = "Midterm"
    FINAL = "Final"


class QuestionPreparationMode(StrEnum):
    ASSISTED_PDF = "assisted_pdf"
    MANUAL_PDF = "manual_pdf"
    STRUCTURED_TEMPLATE = "structured_template"


class UploadedFileType(StrEnum):
    EXAM = "exam"
    TP153 = "tp153"


class ReportFormat(StrEnum):
    PDF = "pdf"


class LanguageCode(StrEnum):
    ARABIC = "ar"
    ENGLISH = "en"


class ReportLanguage(StrEnum):
    ARABIC = "ar"
    ENGLISH = "en"


class SupportingMaterialType(StrEnum):
    FIGURE = "figure"
    TABLE = "table"
    CODE_BLOCK = "code_block"


class SupportingAnnotationType(StrEnum):
    CAPTION = "caption"
    LABEL = "label"


class ReferenceTargetType(StrEnum):
    FIGURE = "figure"
    TABLE = "table"
    CODE_BLOCK = "code_block"
    QUESTION = "question"


class ReferenceResolutionStatus(StrEnum):
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


class QuestionType(StrEnum):
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    FILL_IN_BLANK = "fill_in_blank"
    MATCHING = "matching"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"
    CALCULATION = "calculation"
    CODE_QUESTION = "code_question"
    TABLE_BASED = "table_based"
    FIGURE_BASED = "figure_based"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class QuestionReviewStatus(StrEnum):
    MACHINE_EXTRACTED = "machine_extracted"
    NEEDS_REVIEW = "needs_review"
    REVIEWED = "reviewed"


class ExtractionWarningSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AssociationBasis(StrEnum):
    EXACT_LABEL = "exact_label"
    PROXIMITY_SUPPORT = "proximity_support"
    DEICTIC_GEOMETRY = "deictic_geometry"
    AI_ADJUDICATION = "ai_adjudication"


class AcademicStatus(StrEnum):
    SATISFIED = "Satisfied"
    PARTIALLY_SATISFIED = "Partially Satisfied"
    NOT_SATISFIED = "Not Satisfied"
    NOT_VERIFIED = "Not Verified"
    NOT_APPLICABLE = "Not Applicable"


class SemanticConfidenceLevel(StrEnum):
    """The single authoritative categorical-confidence vocabulary.

    Semantic confidence is deliberately separate from numeric OCR and
    extraction confidence. ORM, Pydantic, API, and AI contracts must import
    this enum rather than defining local alternatives.
    """

    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class ProcessingStage(StrEnum):
    QUEUED = "queued"
    VALIDATING = "validating"
    EXTRACTING_EXAM = "extracting_exam"
    EXTRACTING_TP153 = "extracting_tp153"
    REVIEW_READY = "review_ready"
    BUILDING_EVIDENCE = "building_evidence"
    RETRIEVING_KNOWLEDGE = "retrieving_knowledge"
    APPLYING_RULES = "applying_rules"
    GENERATING_REPORT = "generating_report"
    COMPLETED = "completed"
    FAILED = "failed"


def enum_values(enum_cls: type[StrEnum]) -> list[str]:
    """SQLAlchemy's Enum(values_callable=...) hook: without it, SQLAlchemy stores the
    member *name* (e.g. "MIDTERM") instead of its API-facing `.value` ("Midterm")."""
    return [member.value for member in enum_cls]
