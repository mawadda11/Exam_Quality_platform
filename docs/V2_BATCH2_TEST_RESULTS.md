# Version 2 Batch 2 Test Results

## Verification completed in the build workspace

- Python syntax/compile check: Passed.
- Existing and new backend tests: **554 collected and passed in three deterministic test-file batches**.
- Focused M2/M3 regression suite: Passed.
- Migration `0010`: Passed on SQLite upgrade-to-head.
- Existing digital extraction, OCR, TP-153/Course Specification, marks, pipeline, authentication, ownership, and migration tests remained passing.

## New automated coverage

- Arabic and mixed language detection.
- Arabic digit and punctuation normalization.
- Arabic question hierarchy, marks, instructions, and total marks.
- Arabic OCR source text, geometry, confidence, and diagnostics.
- Tesseract Arabic+English language-pack selection and fallback.
- Direct-text quality routing.
- Three Course Specification layout families.
- Reordered Arabic table layout.
- Compact source-faithful layout with missing-section behavior.
- Low-confidence review behavior.
- Course Specification metadata evidence persistence.
- Uploaded-file extraction metadata persistence.
- Migration `0010` columns.

## Required local CI-equivalent gates

The final branch must still run the repository's exact Docker-based Ruff, Mypy, Pytest, frontend, and GitHub Actions gates after the patch is applied. The batch does not modify frontend source code, but the full frontend regression gates remain mandatory before commit.
