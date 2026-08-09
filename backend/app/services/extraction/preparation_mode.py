from __future__ import annotations

from app.core.domain import QuestionPreparationMode, UploadedFileType
from app.models.analysis import Analysis

_PREFIX = "question_preparation:"


def encode_question_preparation_mode(mode: QuestionPreparationMode) -> str:
    return f"{_PREFIX}{mode.value}"


def decode_question_preparation_mode(value: str | None) -> QuestionPreparationMode:
    if value and value.startswith(_PREFIX):
        candidate = value[len(_PREFIX) :]
        try:
            return QuestionPreparationMode(candidate)
        except ValueError:
            pass
    return QuestionPreparationMode.ASSISTED_PDF


def question_preparation_mode_for_analysis(analysis: Analysis) -> QuestionPreparationMode:
    exam_file = next(
        (item for item in analysis.files if item.file_type == UploadedFileType.EXAM),
        None,
    )
    return decode_question_preparation_mode(exam_file.parser_layout if exam_file else None)
