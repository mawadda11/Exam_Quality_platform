from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Protocol
from uuid import UUID


class QuestionOrderRecord(Protocol):
    id: UUID
    parent_question_id: UUID | None
    number_label: str
    page_number: int
    sequence: int


def _natural_reference_key(value: str) -> tuple[tuple[int, int | str], ...]:
    normalized = re.sub(
        r"^(?:question|q|السؤال|سؤال|س)\s*",
        "",
        value.strip().casefold(),
        flags=re.IGNORECASE,
    )
    parts = re.findall(r"\d+|[^\W\d_]+", normalized, flags=re.UNICODE)
    return tuple((0, int(part)) if part.isdigit() else (1, part) for part in parts)


def sort_question_records[QuestionRecordT: QuestionOrderRecord](
    questions: Sequence[QuestionRecordT],
) -> list[QuestionRecordT]:
    """Apply the faculty-facing page, root, child, and source order."""

    by_id = {question.id: question for question in questions}
    appearance = {question.id: index for index, question in enumerate(questions)}
    children_by_parent: dict[UUID, list[QuestionRecordT]] = {}
    roots: list[QuestionRecordT] = []
    for question in questions:
        parent_id = question.parent_question_id
        if parent_id is not None and parent_id in by_id:
            children_by_parent.setdefault(parent_id, []).append(question)
        else:
            roots.append(question)

    def key(question: QuestionRecordT) -> tuple[object, ...]:
        has_sequence = question.sequence > 0
        return (
            question.page_number,
            _natural_reference_key(question.number_label),
            0 if has_sequence else 1,
            question.sequence if has_sequence else 0,
            appearance[question.id],
        )

    ordered: list[QuestionRecordT] = []
    visited: set[UUID] = set()

    def append_branch(question: QuestionRecordT) -> None:
        if question.id in visited:
            return
        visited.add(question.id)
        ordered.append(question)
        for child in sorted(children_by_parent.get(question.id, []), key=key):
            append_branch(child)

    for root in sorted(roots, key=key):
        append_branch(root)
    # Keep malformed historical rows visible in deterministic order.
    for question in sorted(questions, key=key):
        append_branch(question)
    return ordered
