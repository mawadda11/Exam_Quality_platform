# Exam Quality Analyzer — General Extraction + CLO/Topic Review Fix

Date: 2026-08-09

## Scope
This patch is intentionally source-generic. It contains no course-code, page-number, question-number, language-specific fixture, or coordinate hard-coding. The supplied PDFs are regression fixtures only.

## Exam extraction reliability
- Preserve exact source-line ownership while a question stem is assembled instead of reconstructing provenance later from punctuation-sensitive text matching.
- Prevent administrative dotted fields above a question (for example student name / university ID) from being attached as answer blanks to the first question.
- Recognize nested method calls such as `self.connection.execute(query, (student_id, name))` as code so code bodies remain supporting context instead of leaking into canonical question text.
- Let explicit Figure/Table/Code references disambiguate the visual/supporting question family, while preserving strong task types such as MCQ, True/False, calculation, and essay.
- Preserve missing/ambiguous references as missing/ambiguous references without collapsing the semantic question type.

## Course Specification extraction
- Deduplicate coded and uncoded parser/recovery views of the same topic using source/text identity rather than `code OR text` keys.
- Preserve records with conflicting explicit topic codes instead of silently merging them.
- Prefer the most source-faithful CLO candidate when layout and structured-table parsers see the same row, preserving complete raw source provenance and avoiding wrapped-line contamination.

## CLO / Topic review UX
- Course Specification PDF remains the source document for CLO and Topic tabs.
- PDF pane is forced to the physical LEFT on desktop in both English and Arabic/RTL layouts; record fields retain the correct locale direction.
- `Copy text` opens the selectable original Course Specification PDF.
- Missing CLO and Topic records can be added without replacing extracted records.
- Added records can be linked to an exact source area in the Course Specification PDF.
- Added a visible instruction banner explaining the copy/add/source-area workflow.
- Added source-specific accessible labels for the selectable Course Specification PDF.

## Regression results in the patch workspace
Backend passes:
- `tests/test_document_ocr_and_structure.py` — 41 passed
- `tests/test_digital_pdf_extractor.py` — 17 passed
- `tests/test_digital_tp153_extractor.py` — 15 passed
- `tests/test_v2_arabic_extraction.py` — 7 passed
- `tests/test_arabic_mixed_structure_regression.py` + `tests/test_structure_reconciliation_question_completeness.py` — 9 passed
- `tests/test_v2_adaptive_course_specification.py` + `tests/test_tp153_extraction_persistence.py` — 10 passed
- `tests/test_extraction_review_snapshot.py` + `tests/test_extraction_review_v2.py` — 11 passed
- Targeted Batch4/CS241 extraction regressions pass, including source-boundary, supporting-context, explicit-reference, nested-code, and course-specification tests.

Known-good manual regression checks after the patch:
- CPIT405 Arabic/mixed: 22 records = 18 assessed + 4 structural containers; Course Spec = 4 CLOs + 6 Topics.
- ITCY312 English: 22 records = 18 assessed + 4 structural containers; Course Spec = 4 CLOs + 6 Topics.
- CPIT405 Q4(b) improves from `code_question` to `figure_based` because the prompt explicitly references Figure 1.

Batch4/CS241 deterministic result after the patch:
- Q1 clean, no Student ID/Name contamination, no false blanks.
- Q2 figure_based with full Figure 1 prompt.
- Q3 table_based with full Table 1 prompt.
- Q4 code_question with clean prompt; code body remains separate.
- Q5 figure_based with unresolved Figure 5 preserved.
- Q6 figure_based with ambiguous Figure 2 preserved.
- Q7 figure_based with unlabeled diagram reference preserved.
- Course Spec = 4 CLOs + 7 unique Topics.

## Frontend verification note
The changed TypeScript/TSX files were syntax-checked with TypeScript `transpileModule`. Full Vitest execution could not be installed in the isolated build environment because its internal npm mirror returned a 404 for `zod-validation-error@4.0.2`. The patch includes regression tests; run them in the user's existing frontend environment after applying.
