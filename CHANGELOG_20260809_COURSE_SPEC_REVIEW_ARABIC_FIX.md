# Course Specification Arabic Extraction and Faculty Review — 2026-08-09

## Scope

This change improves Course Specification (TP-153 or equivalent) extraction and extends Extraction Review so faculty can verify and correct the Course Specification before analysis continues.

## Extraction

- Uses geometry-aware reading-order text as the canonical text for digitally readable Course Specification PDFs while preserving raw source text for provenance where applicable.
- Supports Arabic, English, and mixed Arabic/English Course Specification headings and records.
- Normalizes Arabic Presentation Forms for reliable matching without changing the displayed academic content.
- Recognizes CLO and topic codes when they appear within mixed rows, not only at the beginning of a line.
- Prevents assessment/footer text from being appended to CLO/topic records.
- Preserves wrapped CLO/topic descriptions conservatively.

Regression verification on the Arabic CPIT405 and CPIT330 Course Specification fixtures returns four CLOs (CLO1–CLO4) and six topics (T1–T6) for each file.

## Faculty Course Specification Review

- CLO and Topic tabs use the uploaded Course Specification PDF as their visual source reference.
- Faculty can use **Show in Course Specification PDF** for extracted CLOs/topics.
- Faculty can add a missing CLO or topic from the Course Specification PDF by selecting its source region and entering the source-faithful text.
- Reviewer-added CLO/topic records require traceable Course Specification PDF evidence before they can be saved.
- Confirmed reviewer additions materialize into the canonical CLO/topic data used by downstream analysis.
- No database migration is required.

## Workflow decision

No additional `Exam reviewed` / `Course Specification reviewed` status badges were added. Course Specification review remains part of the existing unified Extraction Review, and the single **Confirm Extraction and Continue** action confirms the reviewed extraction snapshot.

## Verification

Targeted backend regression suite: 31 passed.
Frontend modified TypeScript/TSX files were syntax-transpiled successfully. A complete frontend build/test run was not available in this environment because the project snapshot does not contain `node_modules`.
