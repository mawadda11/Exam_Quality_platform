# Exam Quality Knowledge Base v1.0

Place the approved source workbooks in `knowledge_base/source/` using these exact names:

1. `01_references.xlsx`
2. `02_standards.xlsx`
3. `03_criteria.xlsx`
4. `04_requirements.xlsx`
5. `05_evidence_types.xlsx`
6. `06_evidence_mapping.xlsx`
7. `07_evaluation_rules.xlsx`
8. `08_recommendations.xlsx`
9. `09_relationships.xlsx`
10. `10_metadata.xlsx`
11. `11_scoring_policy.xlsx`

The source folder is intentionally empty in this package because the approved workbook contents were not attached in the current request. Do not replace them with invented records.

After adding the files, run:
```bash
python scripts/validate_knowledge_base.py
```

The ingestion implementation must preserve provenance and distinguish official wording from derived requirements, system rules, and system policies.
