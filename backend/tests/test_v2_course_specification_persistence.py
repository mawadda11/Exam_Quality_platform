from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evidence import Evidence
from app.services.extraction.tp153_persistence import persist_tp153_extraction_result
from app.services.extraction.types import ExtractedCourseField, Tp153ExtractionResult


def test_course_specification_fields_are_persisted_as_reviewable_evidence(
    db_engine,
) -> None:
    analysis_id = uuid.uuid4()
    result = Tp153ExtractionResult(
        clos=[],
        topics=[],
        assessment_records=[],
        missing_sections=[],
        course_fields=[
            ExtractedCourseField(
                field_name="course_code",
                value="CPIT-450",
                page_number=1,
                confidence=0.82,
                geometry=None,
            )
        ],
    )

    with Session(db_engine) as session:
        # SQLite test fixtures do not enforce foreign keys, allowing this
        # focused persistence test to validate the emitted evidence row.
        persist_tp153_extraction_result(session, analysis_id, result)
        rows = (
            session.execute(select(Evidence).where(Evidence.analysis_id == analysis_id))
            .scalars()
            .all()
        )

    assert len(rows) == 1
    assert rows[0].evidence_type == "course_specification_field"
    assert rows[0].item_reference == "course_code"
    assert rows[0].extracted_text == "CPIT-450"
