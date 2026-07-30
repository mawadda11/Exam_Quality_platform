"""Local evidence-grounded semantic baseline for offline development.

This adapter is deliberately conservative and transparent. It is not a
replacement for an approved external language model and is blocked in
production. It exists so the training-project demo can execute the governed
M6-M9 contracts without sending exam text to a third party.
"""

from __future__ import annotations

import json
import re
from typing import Any, cast

from app.services.ai.provider import AiProviderError
from app.services.extraction.text_normalization import normalize_arabic_for_matching

_TOKEN = re.compile(r"[a-z0-9\u0600-\u06ff]+", re.IGNORECASE)
_ACTION_VERBS = {
    "analyze",
    "calculate",
    "compare",
    "complete",
    "create",
    "define",
    "describe",
    "design",
    "determine",
    "differentiate",
    "discuss",
    "evaluate",
    "explain",
    "identify",
    "implement",
    "justify",
    "list",
    "prove",
    "select",
    "solve",
    "state",
    "trace",
    "write",
    # Arabic command/action forms used in computing assessments. Diacritics
    # and a leading conjunction are normalized before lookup.
    "اشرح",
    "عرف",
    "حدد",
    "حول",
    "اكتب",
    "احسب",
    "حل",
    "حلل",
    "قارن",
    "ناقش",
    "طبق",
    "صمم",
    "استخرج",
    "اذكر",
    "بين",
    "وضح",
    "برهن",
    "اختر",
    "قيم",
    "فسر",
}
_WEAK_ACTIONS = {"comment", "mention", "talk", "علق", "اذكر باختصار"}
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "using",
    "with",
    "question",
    "q",
    "marks",
    "mark",
    "student",
    "students",
    "في",
    "من",
    "على",
    "الى",
    "إلى",
    "عن",
    "ما",
    "يلي",
    "جميع",
    "هذا",
    "هذه",
    "ذلك",
    "تلك",
    "مع",
    "او",
    "أو",
    "ثم",
    "كل",
    "السؤال",
    "سؤال",
    "درجات",
    "درجة",
}
_AMBIGUOUS_MARKERS = {
    "and/or",
    "etc",
    "appropriate",
    "somehow",
    "something",
    "things",
    "various",
    "whatever",
    "مناسب",
    "بعض",
    "أشياء",
    "اشياء",
}
_REFERENCE_MARKERS = {
    "above",
    "below",
    "following",
    "provided",
    "attached",
    "figure",
    "table",
    "diagram",
    "code shown",
    "المعطى",
    "الموضح",
    "التالي",
    "المرفق",
    "الشكل",
    "الجدول",
    "الرسم",
    "الكود",
}


def _is_arabic_token(token: str) -> bool:
    return any("\u0600" <= char <= "\u06ff" for char in token)


def _normalize_arabic_token(token: str) -> str:
    normalized = normalize_arabic_for_matching(token).casefold()
    # Remove a common attached conjunction before the definite article or an
    # imperative verb (e.g. واشرح -> اشرح, والبيانات -> البيانات).
    if normalized.startswith(("وال", "فال")) and len(normalized) > 5:
        normalized = normalized[1:]
    elif normalized.startswith(("و", "ف")) and (
        normalized[1:] in _ACTION_VERBS
        or (normalized.startswith("و") and normalized[1:].startswith(("ا", "إ", "آ")))
    ):
        normalized = normalized[1:]
    if normalized.startswith("ال") and len(normalized) > 4:
        normalized = normalized[2:]
    # Conservative regular plural handling helps exact concept matching such
    # as استعلام / استعلامات without pretending to be a full Arabic stemmer.
    if normalized.endswith("ات") and len(normalized) > 5:
        normalized = normalized[:-2]
    if normalized == "قواعد":
        return "قاعدة"
    return normalized


def _stem(token: str) -> str:
    if _is_arabic_token(token):
        return _normalize_arabic_token(token)
    token = token.casefold()
    for suffix in ("ations", "ation", "ments", "ment", "ing", "ed", "es", "s"):
        if token.endswith(suffix) and len(token) > len(suffix) + 3:
            return token[: -len(suffix)]
    return token


def _tokens(text: str) -> set[str]:
    normalized_text = normalize_arabic_for_matching(text).casefold()
    normalized_stopwords = {_stem(word) for word in _STOPWORDS}
    tokens = {
        normalized
        for token in _TOKEN.findall(normalized_text)
        if len(token) > 1
        for normalized in (_stem(token),)
        if normalized and normalized not in normalized_stopwords
    }
    # In database courses, the standard 2NF/3NF labels and the Arabic phrase
    # "الصورة الطبيعية" are explicit, auditable names for normalization.
    if "2nf" in tokens or "3nf" in tokens or "الصورة الطبيعية" in normalized_text:
        tokens.add("تطبيع")
    return tokens


def _concept_overlap(left: str, right: str) -> int:
    """Return an auditable shared-concept count for the local demo adapter.

    The production semantic contract never uses this helper.  The offline
    adapter intentionally avoids opaque numeric similarity/confidence
    thresholds: an exact controlled identifier is strongest evidence, two or
    more shared normalized concepts is full local support, one is limited
    support, and zero is unsupported.
    """

    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0
    return len(left_tokens & right_tokens)


def _has_explicit_reference(source_text: str, reference: str) -> bool:
    """Recognize controlled IDs with harmless punctuation variants.

    Examples: ``CLO1``, ``CLO-1``, ``[CLO 1]`` and ``T_2``.  The
    normalization is identifier-only and does not infer academic meaning.
    """

    characters = [re.escape(char) for char in reference.casefold() if char.isalnum()]
    if not characters:
        return False
    pattern = r"(?<![a-z0-9])" + r"[\W_]*".join(characters) + r"(?![a-z0-9])"
    return re.search(pattern, source_text.casefold()) is not None


def _aggregate(statuses: list[str]) -> str:
    if not statuses:
        return "Not Verified"
    if all(status == "Not Applicable" for status in statuses):
        return "Not Applicable"
    substantive = [status for status in statuses if status != "Not Applicable"]
    if not substantive:
        return "Not Applicable"
    if all(status == substantive[0] for status in substantive):
        return substantive[0]
    if all(status == "Not Verified" for status in substantive):
        return "Not Verified"
    return "Partially Satisfied"


def _best_targets(source_text: str, targets: list[dict[str, object]]) -> tuple[str, list[str], str]:
    ranked: list[tuple[bool, int, dict[str, object]]] = []
    for target in targets:
        overlap = _concept_overlap(source_text, str(target.get("text", "")))
        reference = str(target.get("item_reference", "")).strip()
        explicit_reference = bool(reference and _has_explicit_reference(source_text, reference))
        ranked.append((explicit_reference, overlap, target))

    ranked.sort(
        key=lambda item: (
            -int(item[0]),
            -item[1],
            str(item[2].get("id", "")),
        )
    )
    if not ranked:
        return "Not Verified", [], "No controlled target evidence was available."

    best_explicit, best_overlap, best = ranked[0]
    if best_explicit:
        selected = [str(target[2]["id"]) for target in ranked if target[0]][:3]
        return (
            "Satisfied",
            selected or [str(best["id"])],
            "The question explicitly cites one or more controlled target identifiers.",
        )

    if best_overlap >= 2:
        selected = [str(target[2]["id"]) for target in ranked if target[1] >= 2][:3]
        return (
            "Satisfied",
            selected or [str(best["id"])],
            "The question and controlled target share at least two normalized assessed concepts.",
        )

    if best_overlap == 1:
        selected = [str(target[2]["id"]) for target in ranked if target[1] == 1][:3]
        return (
            "Partially Satisfied",
            selected or [str(best["id"])],
            "One normalized assessed concept is shared; the local evidence is limited.",
        )

    return (
        "Not Satisfied",
        [],
        "No shared normalized assessed concept or explicit controlled identifier was found.",
    )


def _has_action(text: str) -> tuple[bool, bool]:
    tokens = _tokens(text)
    return bool(tokens & _ACTION_VERBS), bool(tokens & _WEAK_ACTIONS)


def _item_for_rule(
    rule_id: str,
    source: dict[str, object],
    targets: list[dict[str, object]],
    context: list[dict[str, object]],
) -> dict[str, object]:
    source_text = str(source.get("text", ""))
    source_id = str(source["id"])

    if rule_id in {"RULE001", "RULE002", "RULE007", "RULE008"}:
        status, target_ids, reasoning = _best_targets(source_text, targets)
        if rule_id == "RULE008":
            if status == "Not Satisfied":
                reasoning = (
                    "The assessed content could not be supported by any supplied documented topic."
                )
            elif status == "Partially Satisfied":
                reasoning = (
                    "Only a limited part of the assessed content is supported by documented topics."
                )
            else:
                reasoning = "The assessed content is supported by documented course topics."
        return {
            "source_evidence_id": source_id,
            "target_evidence_ids": target_ids,
            "status": status,
            "reasoning": reasoning,
        }

    if rule_id == "RULE004":
        relation_status, target_ids, _ = _best_targets(source_text, targets)
        clear_action, weak_action = _has_action(source_text)
        if relation_status == "Not Satisfied":
            status = "Not Satisfied"
            reasoning = "The format cannot be tied to an intended CLO using supplied evidence."
        elif clear_action:
            status = "Satisfied"
            reasoning = "The question states an observable response task suitable for the target."
        elif weak_action:
            status = "Partially Satisfied"
            reasoning = "The response task is understandable but not fully precise."
        else:
            status = "Not Satisfied"
            reasoning = "No recognizable response action is stated."
        return {
            "source_evidence_id": source_id,
            "target_evidence_ids": target_ids,
            "status": status,
            "reasoning": reasoning,
        }

    if rule_id == "RULE003":
        exam_text = normalize_arabic_for_matching(source_text).casefold()
        combined = normalize_arabic_for_matching(
            " ".join(str(item.get("text", "")) for item in targets)
        ).casefold()
        midterm_markers = ("midterm", "نصفي", "منتصف")
        final_markers = ("final", "نهائي")
        expected = (
            "midterm"
            if any(marker in exam_text for marker in midterm_markers)
            else "final"
            if any(marker in exam_text for marker in final_markers)
            else ""
        )
        expected_markers = midterm_markers if expected == "midterm" else final_markers
        opposite_markers = final_markers if expected == "midterm" else midterm_markers
        if expected and any(marker in combined for marker in expected_markers):
            status = "Satisfied"
            reasoning = f"The documented assessment evidence explicitly includes the {expected}."
        elif any(marker in combined for marker in ("exam", "written", "اختبار", "تحريري")):
            status = "Partially Satisfied"
            reasoning = (
                "A general exam method is documented, but the exact exam type is incomplete."
            )
        elif expected and any(marker in combined for marker in opposite_markers):
            status = "Not Satisfied"
            reasoning = "The documented assessment evidence identifies the other exam type."
        else:
            status = "Not Verified"
            reasoning = "The assessment evidence does not identify a comparable exam method."
        return {
            "source_evidence_id": source_id,
            "target_evidence_ids": [str(item["id"]) for item in targets],
            "status": status,
            "reasoning": reasoning,
        }

    if rule_id == "RULE011":
        clear_action, weak_action = _has_action(source_text)
        if clear_action:
            status = "Satisfied"
            reasoning = "A recognizable action and expected response are stated."
        elif weak_action or len(_tokens(source_text)) >= 4:
            status = "Partially Satisfied"
            reasoning = "The task is understandable but the expected response is not fully precise."
        else:
            status = "Not Satisfied"
            reasoning = "The required action or expected response cannot be identified."
        return {
            "source_evidence_id": source_id,
            "target_evidence_ids": [],
            "status": status,
            "reasoning": reasoning,
        }

    if rule_id == "RULE012":
        lowered = normalize_arabic_for_matching(source_text).casefold()
        markers = sorted(marker for marker in _AMBIGUOUS_MARKERS if marker in lowered)
        if not source_text.strip():
            status = "Not Verified"
            reasoning = "Question text is unavailable."
        elif len(markers) >= 2:
            status = "Not Satisfied"
            reasoning = "Multiple material ambiguity markers affect consistent interpretation."
        elif markers:
            status = "Partially Satisfied"
            reasoning = f"Potentially ambiguous wording was detected: {', '.join(markers)}."
        else:
            status = "Satisfied"
            reasoning = "No material ambiguity or contradiction is evident in the supplied wording."
        return {
            "source_evidence_id": source_id,
            "target_evidence_ids": [],
            "status": status,
            "reasoning": reasoning,
        }

    if rule_id == "RULE013":
        lowered = normalize_arabic_for_matching(source_text).casefold()
        references = sorted(marker for marker in _REFERENCE_MARKERS if marker in lowered)
        instruction_ids = [
            str(item["id"]) for item in context if item.get("evidence_type") == "instructions"
        ]
        if len(_tokens(source_text)) < 3:
            status = "Not Satisfied"
            reasoning = "The question lacks enough task or context information to be answerable."
        elif references and not instruction_ids:
            status = "Partially Satisfied"
            reasoning = (
                "The question refers to context or material that is not separately available."
            )
        else:
            status = "Satisfied"
            reasoning = "The supplied question contains the information needed for its stated task."
        return {
            "source_evidence_id": source_id,
            "target_evidence_ids": instruction_ids,
            "status": status,
            "reasoning": reasoning,
        }

    if rule_id == "RULE021":
        instruction_ids = [
            str(item["id"]) for item in context if item.get("evidence_type") == "instructions"
        ]
        lowered = normalize_arabic_for_matching(source_text).casefold()
        unresolved = any(marker in lowered for marker in _REFERENCE_MARKERS)
        if instruction_ids:
            status = "Satisfied"
            reasoning = "General instruction evidence is present and the question states its task."
        elif unresolved:
            status = "Not Satisfied"
            reasoning = (
                "The question depends on referenced material or directions that are unavailable."
            )
        else:
            status = "Not Applicable"
            reasoning = "The question is self-contained and no special instruction is required."
        return {
            "source_evidence_id": source_id,
            "target_evidence_ids": instruction_ids,
            "status": status,
            "reasoning": reasoning,
        }

    raise AiProviderError(f"Local provider does not support {rule_id}.")


class LocalSemanticProvider:
    """Offline, evidence-grounded baseline blocked outside development/test."""

    def __init__(self, *, model: str = "local-governed-baseline-v1") -> None:
        self._model = model
        self.calls: list[dict[str, object]] = []

    @property
    def provider_name(self) -> str:
        return "local"

    @property
    def model_name(self) -> str:
        return self._model

    def generate_structured(self, *, system: str, prompt: str, schema: dict[str, Any]) -> str:
        self.calls.append({"system": system, "prompt": prompt, "schema": schema})
        try:
            envelope = json.loads(prompt)
            evidence = {str(item["id"]): item for item in envelope["evidence"]}
            source_ids = [str(value) for value in envelope["required_source_evidence_ids"]]
            target_ids = [str(value) for value in envelope["allowed_target_evidence_ids"]]
            sources = [evidence[value] for value in source_ids]
            targets = [evidence[value] for value in target_ids]
            context = [item for item in evidence.values() if item.get("role") == "context"]
            rule_id = str(envelope["rule_id"])
            items = [
                _item_for_rule(rule_id, source, targets, [*targets, *context]) for source in sources
            ]
            status = _aggregate([str(item["status"]) for item in items])
            evidence_ids = sorted(
                {str(item["source_evidence_id"]) for item in items}
                | {
                    str(target_id)
                    for item in items
                    for target_id in cast(list[object], item["target_evidence_ids"])
                }
            )
            recommendations = envelope.get("controlled_recommendations", {}).get(status, [])
            recommendation_id = (
                recommendations[0]["recommendation_id"]
                if recommendations and status != "Satisfied"
                else None
            )
            return json.dumps(
                {
                    "rule_id": rule_id,
                    "requirement_id": envelope["requirement_id"],
                    "status": status,
                    "evidence_ids": evidence_ids,
                    "explanation": (
                        f"{len(items)} confirmed source item(s) were evaluated against the "
                        "controlled rule conditions and supplied knowledge-base context."
                    ),
                    "recommendation_id": recommendation_id,
                    "items": items,
                    "provider": self.provider_name,
                    "model": self.model_name,
                    "prompt_template_version": envelope["prompt_template_version"],
                    "kb_version": envelope["kb_version"],
                }
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise AiProviderError("Local provider received an invalid prompt envelope.") from exc
