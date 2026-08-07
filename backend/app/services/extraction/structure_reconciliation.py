"""Field-level reconciliation of independent local and visual structure candidates."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from difflib import SequenceMatcher

from app.core.domain import ExtractionWarningSeverity, QuestionReviewStatus, QuestionType
from app.services.extraction.types import (
    ExtractedQuestion,
    ExtractedSourceLine,
    ExtractedStructureCandidate,
    ExtractionReconciliationWarning,
    Geometry,
)

_SPACE = re.compile(r"\s+")
_TECHNICAL = re.compile(
    r"(?:\b\d{1,3}(?:\.\d{1,3}){3}(?:/\d{1,2})?\b|"
    r"\b0x[0-9a-f]+\b|[=<>^{}\\/]|\b[A-Z]{2,}\d*\b)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class StructureReconciliationResult:
    questions: tuple[ExtractedQuestion, ...]
    warnings: tuple[ExtractionReconciliationWarning, ...]
    candidates: tuple[ExtractedStructureCandidate, ...]
    recovered_source_lines: tuple[ExtractedSourceLine, ...] = ()


def _normalized(value: str) -> str:
    return _SPACE.sub(" ", value).strip().casefold()


def _similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, _normalized(left), _normalized(right)).ratio()


def _looks_like_textual_extension(local_text: str, visual_text: str) -> bool:
    """Return true only for a source-backed, linguistically plausible continuation.

    This deliberately rejects the broad rule "visual has more text, therefore use it".
    The additional text must follow the local text and look like a wrapped continuation
    rather than an unrelated heading, watermark, note, or nearby block.
    """

    local_compact = _SPACE.sub(" ", local_text).strip()
    visual_compact = _SPACE.sub(" ", visual_text).strip()
    if (
        not local_compact
        or not visual_compact.casefold().startswith(local_compact.casefold())
        or visual_compact.casefold() == local_compact.casefold()
    ):
        return False
    remainder = visual_compact[len(local_compact) :].lstrip()
    if not remainder:
        return False

    local_tail = local_compact[-1]
    if local_tail in ",،;؛:([{/-–—":
        return True
    first = remainder[:1]
    if first.islower() or first.isdigit():
        return True
    continuation_prefix = re.compile(
        r"^(?:and|or|then|also|with|where|when|using|show|explain|calculate|compute|"
        r"identify|determine|state|give|provide|write|draw|compare|perform|report|"
        r"return|find|then|ثم|و|أو|او|اشرح|وضح|احسب|حدد|اذكر|اكتب|ارسم|قارن|بين|بيّن|نفذ)\b",
        re.IGNORECASE,
    )
    return continuation_prefix.match(remainder) is not None


def _overlap(left: ExtractedQuestion, right: ExtractedQuestion) -> int:
    return len(set(left.source_line_ids).intersection(right.source_line_ids))


def _geometry_distance(left: Geometry | None, right: Geometry | None) -> float | None:
    if left is None or right is None:
        return None
    left_center = ((left.x0 + left.x1) / 2, (left.top + left.bottom) / 2)
    right_center = ((right.x0 + right.x1) / 2, (right.top + right.bottom) / 2)
    return float(
        ((left_center[0] - right_center[0]) ** 2 + (left_center[1] - right_center[1]) ** 2) ** 0.5
    )


def _warning(
    code: str,
    question: ExtractedQuestion,
    *,
    source_line_ids: tuple[str, ...] | None = None,
) -> ExtractionReconciliationWarning:
    return ExtractionReconciliationWarning(
        code=code,
        severity=ExtractionWarningSeverity.CRITICAL,
        message="Local and visual extraction candidates disagree and require review.",
        page_number=question.page_number,
        source_line_ids=source_line_ids or question.source_line_ids,
        geometry=question.geometry,
    )


def _best_local(
    visual: ExtractedQuestion,
    available: list[ExtractedQuestion],
) -> ExtractedQuestion | None:
    same_page = [item for item in available if item.page_number == visual.page_number]
    if not same_page:
        return None
    ranked = sorted(
        same_page,
        key=lambda item: (
            _overlap(item, visual),
            item.number_label.casefold() == visual.number_label.casefold(),
            _similarity(item.text, visual.text),
        ),
        reverse=True,
    )
    best = ranked[0]
    if _overlap(best, visual) > 0:
        return best
    if (
        best.number_label.casefold() == visual.number_label.casefold()
        and _similarity(best.text, visual.text) >= 0.45
    ):
        return best
    return None


def reconcile_structure_candidates(
    *,
    local_questions: tuple[ExtractedQuestion, ...],
    visual_questions: tuple[ExtractedQuestion, ...],
    local_candidates: tuple[ExtractedStructureCandidate, ...],
    visual_candidates: tuple[ExtractedStructureCandidate, ...],
    recovered_source_lines: tuple[ExtractedSourceLine, ...] = (),
) -> StructureReconciliationResult:
    remaining = list(local_questions)
    reconciled: list[ExtractedQuestion] = []
    warnings: list[ExtractionReconciliationWarning] = []
    visual_to_canonical_key: dict[str, str] = {}

    for visual in visual_questions:
        local = _best_local(visual, remaining)
        if local is None:
            reconciled.append(replace(visual, review_status=QuestionReviewStatus.NEEDS_REVIEW))
            if visual.local_key:
                visual_to_canonical_key[visual.local_key] = visual.local_key
            warnings.append(_warning("QUESTION_MISSING", visual))
            continue
        remaining.remove(local)
        canonical_key = local.local_key or visual.local_key or f"local-{local.sequence}"
        if visual.local_key:
            visual_to_canonical_key[visual.local_key] = canonical_key
        translated_visual_parent = visual_to_canonical_key.get(
            visual.parent_local_key or "",
            visual.parent_local_key,
        )
        proposed = local
        local_source_ids = set(local.source_line_ids)
        visual_source_ids = set(visual.source_line_ids)
        combined_ids = tuple(dict.fromkeys((*local.source_line_ids, *visual.source_line_ids)))
        if local_source_ids != visual_source_ids:
            warnings.append(
                _warning("QUESTION_BOUNDARY_MISMATCH", local, source_line_ids=combined_ids)
            )

        # The visual materializer reconstructs question text from validated source
        # lines, not from free-form model transcription. If it proves that the
        # local parser stopped early and contributes a strict source-line superset,
        # keep the canonical local identity but promote the more complete
        # source-backed stem. This is deliberately one-way: partial/disjoint visual
        # boundaries never replace local text merely because Gemini preferred them.
        visual_is_source_backed_extension = (
            bool(local_source_ids)
            and local_source_ids < visual_source_ids
            and _looks_like_textual_extension(local.text, visual.text)
        )
        if visual_is_source_backed_extension:
            proposed = replace(
                proposed,
                text=visual.text,
                source_line_ids=visual.source_line_ids,
                geometry=visual.geometry or local.geometry,
                confidence=min(local.confidence, visual.confidence, 0.95),
                extraction_method=visual.extraction_method,
                review_status=QuestionReviewStatus.NEEDS_REVIEW,
            )
        similarity = _similarity(local.text, visual.text)
        if similarity < 0.92:
            warnings.append(
                _warning(
                    "TECHNICAL_TEXT_MISMATCH"
                    if _TECHNICAL.search(local.text + visual.text)
                    else "CRITICAL_TEXT_MISMATCH",
                    local,
                    source_line_ids=combined_ids,
                )
            )
        if local.number_label.casefold() != visual.number_label.casefold():
            warnings.append(
                _warning("QUESTION_NUMBER_MISMATCH", local, source_line_ids=combined_ids)
            )
        if local.question_type != visual.question_type:
            warnings.append(_warning("QUESTION_TYPE_MISMATCH", local, source_line_ids=combined_ids))
            if local.question_type is QuestionType.UNKNOWN:
                proposed = replace(proposed, question_type=visual.question_type)
        if local.parent_local_key != translated_visual_parent:
            warnings.append(
                _warning("QUESTION_HIERARCHY_MISMATCH", local, source_line_ids=combined_ids)
            )
            if local.parent_local_key is None and translated_visual_parent is not None:
                proposed = replace(
                    proposed,
                    parent_local_key=translated_visual_parent,
                    parent_number_label=visual.parent_number_label,
                )
        if local.marks != visual.marks:
            warnings.append(_warning("MARKS_MISMATCH", local, source_line_ids=combined_ids))
            if local.marks is None and visual.marks is not None:
                proposed = replace(proposed, marks=visual.marks)
        local_options = {item.option_label.casefold(): item for item in local.options}
        visual_options = {item.option_label.casefold(): item for item in visual.options}
        if local_options.keys() != visual_options.keys():
            warnings.append(_warning("OPTION_MISSING", local, source_line_ids=combined_ids))
            if not local.options and visual.options:
                proposed = replace(
                    proposed,
                    options=tuple(
                        replace(option, question_local_key=canonical_key)
                        for option in visual.options
                    ),
                )
        for label in local_options.keys() & visual_options.keys():
            if (
                _similarity(local_options[label].option_text, visual_options[label].option_text)
                < 0.92
            ):
                warnings.append(
                    _warning("OPTION_TEXT_MISMATCH", local, source_line_ids=combined_ids)
                )
                break
        if len(local.blanks) != len(visual.blanks):
            warnings.append(_warning("BLANK_MISSING", local, source_line_ids=combined_ids))
            if not local.blanks and visual.blanks:
                proposed = replace(
                    proposed,
                    blanks=tuple(
                        replace(blank, question_local_key=canonical_key) for blank in visual.blanks
                    ),
                )
        if local.instructions != visual.instructions:
            warnings.append(
                _warning("SHARED_INSTRUCTIONS_MISMATCH", local, source_line_ids=combined_ids)
            )
            if local.instructions is None and visual.instructions:
                proposed = replace(proposed, instructions=visual.instructions)
        if set(local.supporting_material_local_ids) != set(visual.supporting_material_local_ids):
            warnings.append(
                _warning("FIGURE_ASSOCIATION_UNCERTAIN", local, source_line_ids=combined_ids)
            )
            if not local.supporting_material_local_ids:
                proposed = replace(
                    proposed,
                    supporting_material_local_ids=visual.supporting_material_local_ids,
                )
        distance = _geometry_distance(local.geometry, visual.geometry)
        if distance is not None and distance > 72:
            warnings.append(
                _warning("QUESTION_GEOMETRY_MISMATCH", local, source_line_ids=combined_ids)
            )
        if proposed != local:
            proposed = replace(proposed, review_status=QuestionReviewStatus.NEEDS_REVIEW)
        reconciled.append(proposed)

    for local in remaining:
        reconciled.append(local)
        warnings.append(_warning("QUESTION_MISSING", local))

    reconciled.sort(key=lambda item: item.sequence)
    reconciled = [replace(item, sequence=index) for index, item in enumerate(reconciled, start=1)]
    canonical_visual_candidates = tuple(
        replace(
            candidate,
            question_local_key=visual_to_canonical_key.get(
                candidate.question_local_key or "",
                candidate.question_local_key,
            ),
        )
        for candidate in visual_candidates
    )
    return StructureReconciliationResult(
        questions=tuple(reconciled),
        warnings=tuple(warnings),
        candidates=(*local_candidates, *canonical_visual_candidates),
        recovered_source_lines=recovered_source_lines,
    )
