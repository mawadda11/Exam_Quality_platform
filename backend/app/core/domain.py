from enum import StrEnum


class UserType(StrEnum):
    FACULTY_MEMBER = "Faculty Member"


class ExamType(StrEnum):
    MIDTERM = "Midterm"
    FINAL = "Final"


class UploadedFileType(StrEnum):
    EXAM = "exam"
    TP153 = "tp153"


class AcademicStatus(StrEnum):
    SATISFIED = "Satisfied"
    PARTIALLY_SATISFIED = "Partially Satisfied"
    NOT_SATISFIED = "Not Satisfied"
    NOT_VERIFIED = "Not Verified"
    NOT_APPLICABLE = "Not Applicable"


class ProcessingStage(StrEnum):
    QUEUED = "queued"
    VALIDATING = "validating"
    EXTRACTING_EXAM = "extracting_exam"
    EXTRACTING_TP153 = "extracting_tp153"
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
