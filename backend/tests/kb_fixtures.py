"""Deterministic, synthetic KB workbooks for M7 validator/normalizer tests.

Built programmatically with openpyxl rather than committed as binary files -
same reasoning as pdf_fixtures.py: the repo doesn't want binary fixtures
committed, and generating from readable Python source is easier to review.

VALID_ROWS is one small, fully self-consistent, valid 11-workbook KB (every
FK resolves, every provenance value maps, every enum value is allowed).
Negative-case tests build on top of it via write_kb()'s overrides rather
than each maintaining an independent full copy.
"""

from __future__ import annotations

from pathlib import Path

import openpyxl

from app.services.knowledge_base.schemas import ALL_WORKBOOK_SCHEMAS

VALID_ROWS: dict[str, list[dict[str, object]]] = {
    "01_references.xlsx": [
        {
            "Reference_ID": "REF001",
            "Reference_Code": "DP-100",
            "Reference_Name": "Test Reference",
            "Organization": "Test Org",
            "Version": "1.0",
            "Document_Type": "Test Doc",
            "Role_in_Knowledge_Base": "Primary",
            "Official_Source": "Yes",
            "Scope_Use": "Exam-related requirements only",
            "Notes": "",
        }
    ],
    "02_standards.xlsx": [
        {
            "Standard_ID": "STD001",
            "Reference_ID": "REF001",
            "Official_Code": "1",
            "Standard_Name": "Test Standard",
            "Record_Type": "Official Standard",
            "Scope_Status": "In Scope",
            "Evaluation_Use": "Test use",
            "Inclusion_Reason": "Test reason",
            "Scope_Limit": "",
        }
    ],
    "03_criteria.xlsx": [
        {
            "Criterion_ID": "CRT001",
            "Standard_ID": "STD001",
            "Criterion_Code": "1-1",
            "Criterion_Name": "Test Criterion",
            "Source_Type": "Official Criterion",
            "Officiality": "Official",
            "Scope_Status": "In Scope",
            "Evidence_Source": "",
            "Use_in_System": "Test use",
            "Notes": "",
        }
    ],
    "04_requirements.xlsx": [
        {
            "Requirement_ID": "REQ001",
            "Criterion_ID": "CRT001",
            "Dimension": "Test Dimension",
            "Requirement_Name": "Test Requirement",
            "Requirement_Summary": "Test summary",
            "Source_Type": "Derived Exam Requirement",
            "Officiality": "Derived",
            "Applicability": "Exam evidence only",
            "Verification_Method": "Test method",
            "Not_Verified_Condition": "Test condition",
            "Not_Applicable_Condition": "None",
            "Scope_Limit": "",
        }
    ],
    "05_evidence_types.xlsx": [
        {
            "Evidence_Type_ID": "EV001",
            "Evidence_Name": "Test Evidence",
            "Source_Document": "Exam PDF",
            "Evidence_Category": "Test Category",
            "Extraction_Method": "Test method",
            "Required_Fields": "test field",
            "Used_For": "Test use",
            "Reliability_Notes": "",
        }
    ],
    "06_evidence_mapping.xlsx": [
        {
            "Mapping_ID": "MAP001",
            "Requirement_ID": "REQ001",
            "Evidence_Type_ID": "EV001",
            "Evidence_Role": "Test role",
            "Mandatory": "Yes",
            "Applicability_Condition": "",
            "Missing_Evidence_Result": "Not Verified",
            "Notes": "",
        }
    ],
    "07_evaluation_rules.xlsx": [
        {
            "Rule_ID": "RULE001",
            "Requirement_ID": "REQ001",
            "Rule_Name": "Test Rule",
            "Rule_Type": "Test Type",
            "Satisfied_Condition": "Test satisfied",
            "Partially_Satisfied_Condition": "Test partial",
            "Not_Satisfied_Condition": "Test not satisfied",
            "Not_Verified_Condition": "Test not verified",
            "Not_Applicable_Condition": "None",
            "Output_Statuses": "Satisfied; Not Satisfied; Not Verified",
            "Officiality": "System Rule",
        }
    ],
    "08_recommendations.xlsx": [
        {
            "Recommendation_ID": "REC001",
            "Rule_ID": "RULE001",
            "Recommendation_Title": "Test Title",
            "Recommendation_Text": "Test text",
            "Trigger_Status": "Not Satisfied",
            "Target_User": "Faculty",
            "Recommendation_Type": "Corrective",
            "Notes": "",
        }
    ],
    "09_relationships.xlsx": [
        {
            "Relationship_ID": "REL001",
            "From_Entity_Type": "Reference",
            "From_ID": "REF001",
            "Relationship_Type": "HAS_STANDARD",
            "To_Entity_Type": "Standard",
            "To_ID": "STD001",
            "Status": "Active",
            "Notes": "",
        },
        {
            "Relationship_ID": "REL002",
            "From_Entity_Type": "Standard",
            "From_ID": "STD001",
            "Relationship_Type": "HAS_CRITERION",
            "To_Entity_Type": "Criterion",
            "To_ID": "CRT001",
            "Status": "Active",
            "Notes": "",
        },
        {
            "Relationship_ID": "REL003",
            "From_Entity_Type": "Criterion",
            "From_ID": "CRT001",
            "Relationship_Type": "HAS_REQUIREMENT",
            "To_Entity_Type": "Requirement",
            "To_ID": "REQ001",
            "Status": "Active",
            "Notes": "",
        },
        {
            "Relationship_ID": "REL004",
            "From_Entity_Type": "Requirement",
            "From_ID": "REQ001",
            "Relationship_Type": "EVALUATED_BY",
            "To_Entity_Type": "Rule",
            "To_ID": "RULE001",
            "Status": "Active",
            "Notes": "",
        },
        {
            "Relationship_ID": "REL005",
            "From_Entity_Type": "Requirement",
            "From_ID": "REQ001",
            "Relationship_Type": "REQUIRES_EVIDENCE",
            "To_Entity_Type": "EvidenceType",
            "To_ID": "EV001",
            "Status": "Active",
            "Notes": "",
        },
        {
            "Relationship_ID": "REL006",
            "From_Entity_Type": "Rule",
            "From_ID": "RULE001",
            "Relationship_Type": "TRIGGERS",
            "To_Entity_Type": "Recommendation",
            "To_ID": "REC001",
            "Status": "Active",
            "Notes": "",
        },
    ],
    "10_metadata.xlsx": [
        {
            "Metadata_ID": "META001",
            "Entity_Name": "All Entities",
            "Field_Name": "version",
            "Data_Type": "String",
            "Required": "Yes",
            "Allowed_Values_or_Format": "Semantic version such as 1.0.0",
            "Default_Value": "1.0.0",
            "Description": "Test description",
        }
    ],
    "11_scoring_policy.xlsx": [
        {
            "Policy_ID": "SCORE001",
            "Policy_Category": "Status Model",
            "Policy_Name": "Positive Status",
            "Policy_Value": "Satisfied",
            "Applies_To": "Rules",
            "Mandatory": "Yes",
            "Description": "Test description",
        }
    ],
}


def _write_workbook(path: Path, header: list[str], rows: list[dict[str, object]]) -> None:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(header)
    for row in rows:
        sheet.append([row.get(column, "") for column in header])
    workbook.save(path)


def write_kb(
    dest_dir: Path,
    rows_by_file: dict[str, list[dict[str, object]]] | None = None,
    headers_by_file: dict[str, list[str]] | None = None,
    omit_files: tuple[str, ...] = (),
) -> Path:
    """Writes a synthetic KB into dest_dir.

    rows_by_file overrides VALID_ROWS per-workbook (falls back to the valid
    row set for any workbook not overridden). headers_by_file overrides the
    written column header for a workbook (defaults to the schema's own
    columns) - used to simulate a missing required column. omit_files skips
    writing those workbooks entirely - used to simulate a missing workbook.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    rows = {**VALID_ROWS, **(rows_by_file or {})}
    headers = headers_by_file or {}

    for schema in ALL_WORKBOOK_SCHEMAS:
        if schema.filename in omit_files:
            continue
        header = headers.get(schema.filename, list(schema.column_names))
        _write_workbook(dest_dir / schema.filename, header, rows[schema.filename])
    return dest_dir


def build_valid_kb(dest_dir: Path) -> Path:
    return write_kb(dest_dir)
