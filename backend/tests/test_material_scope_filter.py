from __future__ import annotations

from app.core.domain import (
    ReferenceTargetType,
    SupportingAnnotationType,
    SupportingMaterialType,
)
from app.services.extraction.structured_evidence import retain_question_linked_materials
from app.services.extraction.types import (
    ExtractedDocumentReference,
    ExtractedQuestion,
    ExtractedSupportingAnnotation,
    ExtractedSupportingMaterial,
    Geometry,
)


def _question(
    number_label: str,
    text: str,
    page_number: int,
    *,
    local_key: str,
) -> ExtractedQuestion:
    return ExtractedQuestion(
        number_label=number_label,
        text=text,
        page_number=page_number,
        parent_number_label=None,
        marks=None,
        sequence=1,
        confidence=1.0,
        geometry=Geometry(40, 80, 520, 120),
        local_key=local_key,
    )


def _material(
    key: str,
    material_type: SupportingMaterialType,
    page_number: int,
    text: str,
    geometry: Geometry,
) -> ExtractedSupportingMaterial:
    return ExtractedSupportingMaterial(
        local_key=key,
        material_type=material_type,
        page_number=page_number,
        source_text=text,
        confidence=0.95,
        geometry=geometry,
        extraction_method="direct_text",
    )


def test_keeps_only_question_linked_schema_context() -> None:
    questions = [
        _question("Q1", "Question 1 - Multiple Choice", 1, local_key="q1"),
        _question("Q2", "Question 2 - True or False", 2, local_key="q2"),
        _question(
            "Q4",
            "Question 4 - SQL Application. Use the following schema:",
            4,
            local_key="q4",
        ),
    ]
    materials = [
        _material(
            "cover-table",
            SupportingMaterialType.TABLE,
            1,
            "Course Code | ITDB 211 | Total Marks | 30",
            Geometry(40, 150, 550, 300),
        ),
        _material(
            "tf-grid",
            SupportingMaterialType.TABLE,
            3,
            "No. | Statement | T / F",
            Geometry(40, 50, 550, 200),
        ),
        _material(
            "schema",
            SupportingMaterialType.CODE_BLOCK,
            4,
            "STUDENT(StudentID, StudentName, Major)",
            Geometry(50, 130, 320, 175),
        ),
    ]

    retained, annotations = retain_question_linked_materials(
        questions=questions,
        materials=materials,
        annotations=[],
        references=[],
    )

    assert annotations == []
    assert [item.local_key for item in retained] == ["schema"]
    assert retained[0].question_number_label == "Q4"
    assert retained[0].question_local_key == "q4"


def test_keeps_exactly_referenced_labeled_table() -> None:
    question = _question(
        "Q3",
        "Refer to Table 1 and explain the result.",
        1,
        local_key="q3",
    )
    table = _material(
        "table-1",
        SupportingMaterialType.TABLE,
        1,
        "Student | Mark",
        Geometry(40, 150, 320, 240),
    )
    annotation = ExtractedSupportingAnnotation(
        local_key="label-1",
        material_local_key="table-1",
        annotation_type=SupportingAnnotationType.LABEL,
        original_text="Table 1",
        normalized_label="table:1",
        page_number=1,
        confidence=1.0,
        geometry=Geometry(40, 130, 100, 145),
        extraction_method="direct_text",
    )
    reference = ExtractedDocumentReference(
        local_key="q3-table-1",
        target_type=ReferenceTargetType.TABLE,
        original_text="Table 1",
        target_label="Table 1",
        normalized_target_label="table:1",
        page_number=1,
        confidence=1.0,
        geometry=question.geometry,
        extraction_method="direct_text",
        question_number_label="Q3",
        question_local_key="q3",
    )

    retained, retained_annotations = retain_question_linked_materials(
        questions=[question],
        materials=[table],
        annotations=[annotation],
        references=[reference],
    )

    assert [item.local_key for item in retained] == ["table-1"]
    assert retained[0].question_number_label == "Q3"
    assert retained[0].question_local_key == "q3"
    assert retained_annotations == [annotation]


def test_drops_unreferenced_layout_table() -> None:
    question = _question("Q1", "Define database normalization.", 1, local_key="q1")
    table = _material(
        "metadata",
        SupportingMaterialType.TABLE,
        1,
        "Course | Database Systems",
        Geometry(40, 150, 550, 300),
    )

    retained, retained_annotations = retain_question_linked_materials(
        questions=[question],
        materials=[table],
        annotations=[],
        references=[],
    )

    assert retained == []
    assert retained_annotations == []
