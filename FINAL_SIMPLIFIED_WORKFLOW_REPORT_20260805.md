# Exam Quality Analyzer — Final Simplified Workflow Update

Date: 2026-08-05

## Product decisions implemented

- Assisted PDF extraction is now the recommended starting workflow.
- The Faculty Member corrects only questions that need attention instead of completing a large form.
- The former structured-template workflow is now presented as **Paste or import question list**.
- Questions can be pasted directly from Word or PDF.
- The new CSV requires only `question_number`, `question_text`, and the `marks` column. Marks cells may remain empty. `question_type` and `options` are optional.
- Older detailed CSV files remain accepted for backward compatibility.
- The separate automatically cropped **Original question from PDF** panel was removed. The full PDF page on the left is the source reference.
- `Show in PDF` remains available for page navigation and highlighting.
- Marks can be corrected or cleared for parent/container questions.
- Technical parenthesized numbers such as `GF (19)` are no longer interpreted as marks.
- Explicit marks such as `[5 marks]`, `(5 marks)`, `[5]`, and the approved `Q1 (10):` form remain supported.
- Digital and OCR fallback extraction now preserve wrapped question text until the next explicit question marker.
- No Gemini request was made and no Google Document AI code was added.
- No database migration was added.

## Paste format

```text
Q1. Which pattern constructs a complex object step by step? [1 mark]
A. Singleton
B. Builder
C. Prototype
D. Adapter

Q2. Explain why hash collisions are undesirable
in cryptographic hash functions. [2 marks]
```

The paste parser joins wrapped lines and keeps answer options attached to the current question.

## Validation

- Backend application import: passed.
- Backend test collection: 808 tests.
- All 808 backend tests passed in four isolated groups.
- Knowledge-base validation: passed; 441 normalized records across 11 workbooks.
- TypeScript/TSX syntax validation: passed for 172 files.
- Manual runtime checks for the paste parser and simple CSV parser: passed.
- Full frontend dependency installation could not run because the configured npm mirror returned HTTP 404 for `zod-validation-error@4.0.2`; therefore the complete Vitest/build suite was not claimed as passed in this environment.

## Important behavior

- Existing saved extraction revisions retain their previously extracted text and marks. Create a new analysis to test extraction-rule changes.
- Existing open revisions can use the now-editable Marks field and can remove an incorrect value manually.
- Academic analysis still starts only after the exact Extraction Review revision is saved and confirmed.
