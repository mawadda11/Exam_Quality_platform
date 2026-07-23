"""Shared question-hierarchy logic for rule modules.

A question counts as a scorable "leaf" only if it has no children (a
standalone top-level question, or any sub-question) - a top-level question
that has sub-questions is excluded. Originally introduced in marks_total.py
(M6) to avoid double-counting a parent's marks on top of its children's;
M8's CLO/Topic alignment and coverage rules also operate over the same
scorable-item set, so it now lives here for both to share.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.models.question import Question


def scorable_leaves(questions: Sequence[Question]) -> list[Question]:
    parent_ids_with_children = {
        q.parent_question_id for q in questions if q.parent_question_id is not None
    }
    return [
        q
        for q in questions
        if q.parent_question_id is not None or q.id not in parent_ids_with_children
    ]
