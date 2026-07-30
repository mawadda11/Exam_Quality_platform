from __future__ import annotations

import uuid

from app.models.question import Question
from app.services.ai.local_provider import _best_targets, _has_action, _item_for_rule, _tokens
from app.services.rules.question_hierarchy import scorable_leaves


def _target(reference: str, text: str) -> dict[str, object]:
    return {
        "id": str(uuid.uuid4()),
        "item_reference": reference,
        "text": text,
        "evidence_type": "clo",
    }


def test_arabic_action_verbs_and_concept_tokens_are_recognized() -> None:
    assert _has_action("عرّف قاعدة البيانات العلائقية واشرح فائدتين لها") == (True, False)
    assert _has_action("حوّل التصميم إلى الصورة الطبيعية الثالثة 3NF") == (True, False)
    assert _has_action("اكتب استعلام SQL يعرض أسماء الطلاب") == (True, False)

    tokens = _tokens("قواعد البيانات العلائقية واستعلامات SQL")
    assert {"بيان", "علائقية", "استعلام", "sql"} <= tokens


def test_arabic_question_maps_to_governed_clo_and_topic_concepts() -> None:
    clo = _target("CLO1", "شرح مفاهيم قواعد البيانات العلائقية")
    status, target_ids, _ = _best_targets(
        "عرّف قاعدة البيانات العلائقية واشرح فائدتين لها",
        [clo],
    )
    assert status == "Satisfied"
    assert target_ids == [clo["id"]]

    topic = _target("T2", "الاعتماديات الوظيفية والتطبيع")
    status, target_ids, _ = _best_targets(
        "حدد الاعتماديات الوظيفية في المثال المعطى",
        [topic],
    )
    assert status == "Satisfied"
    assert target_ids == [topic["id"]]


def test_arabic_midterm_assessment_method_is_compared_bilingually() -> None:
    source = {
        "id": str(uuid.uuid4()),
        "text": "Exam type: Midterm | اختبار نصفي",
    }
    target = {
        "id": str(uuid.uuid4()),
        "text": "الطريقة: اختبار نصفي | النشاط: اختبار تحريري",
    }

    item = _item_for_rule("RULE003", source, [target], [])

    assert item["status"] == "Satisfied"
    assert item["target_evidence_ids"] == [target["id"]]


def test_structural_parent_question_is_visible_but_not_a_scorable_leaf() -> None:
    analysis_id = uuid.uuid4()
    parent_id = uuid.uuid4()
    parent = Question(
        id=parent_id,
        analysis_id=analysis_id,
        number_label="Q2",
        question_text="س٢. أجب عما يلي:",
        page_number=1,
        marks=None,
        sequence=1,
        confidence=1.0,
    )
    child_a = Question(
        id=uuid.uuid4(),
        analysis_id=analysis_id,
        parent_question_id=parent_id,
        number_label="Q2(a)",
        question_text="حدد الاعتماديات الوظيفية",
        page_number=1,
        marks=4,
        sequence=2,
        confidence=1.0,
    )
    child_b = Question(
        id=uuid.uuid4(),
        analysis_id=analysis_id,
        parent_question_id=parent_id,
        number_label="Q2(b)",
        question_text="حوّل التصميم إلى 2NF",
        page_number=1,
        marks=3,
        sequence=3,
        confidence=1.0,
    )

    assert [item.number_label for item in scorable_leaves([parent, child_a, child_b])] == [
        "Q2(a)",
        "Q2(b)",
    ]


def test_arabic_pilot_questions_match_expected_controlled_targets() -> None:
    clos = [
        _target("CLO1", "شرح مفاهيم قواعد البيانات العلائقية"),
        _target("CLO2", "تطبيق تقنيات التطبيع حتى الصورة الطبيعية الثالثة"),
        _target("CLO3", "كتابة استعلامات SQL لتحليل البيانات"),
    ]
    topics = [
        _target("T1", "أساسيات قواعد البيانات"),
        _target("T2", "الاعتماديات الوظيفية والتطبيع"),
        _target("T3", "SQL والاستعلامات المتقدمة"),
    ]

    clo_cases = {
        "عرّف قاعدة البيانات العلائقية واشرح فائدتين لها": "CLO1",
        "حوّل التصميم إلى الصورة الطبيعية الثانية 2NF": "CLO2",
        "حوّل التصميم إلى الصورة الطبيعية الثالثة 3NF": "CLO2",
        "اكتب استعلام SQL يعرض أسماء الطلاب": "CLO3",
    }
    for question, expected_reference in clo_cases.items():
        status, target_ids, _ = _best_targets(question, clos)
        expected = next(item for item in clos if item["item_reference"] == expected_reference)
        assert status == "Satisfied"
        assert expected["id"] in target_ids

    status, target_ids, _ = _best_targets(
        "حدد الاعتماديات الوظيفية في المثال المعطى",
        topics,
    )
    expected_topic = next(item for item in topics if item["item_reference"] == "T2")
    assert status == "Satisfied"
    assert target_ids == [expected_topic["id"]]
