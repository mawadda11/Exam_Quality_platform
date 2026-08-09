from __future__ import annotations
import re
from collections.abc import Iterable, Sequence
from app.core.domain import ExamType
from app.models.assessment_record import AssessmentRecord

_FINAL = re.compile(r"\b(final|final examination|final exam)\b|اختبار\s*نهائي|الاختبار\s*النهائي", re.I)
_MID = re.compile(r"\b(midterm|mid-term|mid term)\b|اختبار\s*نصفي|الاختبار\s*النصفي", re.I)

def _matches(method: str, exam_type: ExamType) -> bool:
    return bool((_FINAL if exam_type is ExamType.FINAL else _MID).search(method))

def resolve_applicable_clo_codes(exam_type: ExamType, records: Sequence[AssessmentRecord], available_codes: Iterable[str]) -> frozenset[str] | None:
    available={x.strip().upper().replace(" ","") for x in available_codes if x.strip()}
    mapped=set()
    for record in records:
        if not _matches(record.method, exam_type):
            continue
        for raw in record.related_clo_codes or []:
            code=raw.strip().upper().replace(" ","")
            if code in available:
                mapped.add(code)
    # IMPORTANT: None means preserve the legacy behavior: all CLOs remain applicable.
    return frozenset(mapped) if mapped else None
