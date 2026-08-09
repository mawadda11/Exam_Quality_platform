# Automatic Draft + Copy/Paste Review Refinement — 2026-08-07

This build is based on `Exam_Quality_FINAL_LATEST_UI_ROOTFIX_CONTINUE_FIXED_20260807`.

## Workflow changes

- New analyses always begin with assisted PDF extraction; the pre-start choice between automatic extraction and manual/template entry is removed.
- Extraction Review remains the human-control point: reviewers can keep the automatic draft, edit only missing/wrong content, add a missing question from the PDF, or start over with pasted/imported questions.
- `Start over / paste questions` is now a fallback inside Extraction Review instead of a primary workflow choice.
- Replacing the visible draft preserves the original machine records as excluded audit records rather than deleting them.

## Copy/paste support

- The PDF pane now includes `Copy text` and `Region view` modes.
- `Copy text` embeds the original PDF so text in digital PDFs can be selected and copied with the browser/OS clipboard, then pasted into the exact editable field chosen by the reviewer.
- `Region view` retains the existing highlighted source-region workflow and manual area adjustment.
- `Show in PDF` returns to Region view so source highlighting remains available.

## Source-faithfulness changes

- Pasted replacement questions use `pasted_review` extraction provenance.
- Pasted questions do not invent PDF geometry.
- Backend review validation permits source-faithful pasted questions and MCQ options inside an assisted-PDF analysis while preserving immutable machine source records.

## Verification performed in this build environment

- Backend focused tests: 21 passed (`test_extraction_review_models.py`, `test_extraction_review_schemas.py`, `test_extraction_review_api.py`, `test_pasted_review_questions.py`).
- Python syntax compilation passed for modified backend code/tests.
- TypeScript syntax transpilation passed for all modified TS/TSX files.
- Full frontend npm test/typecheck could not be executed because the configured package registry returned HTTP 404 for an existing dependency tarball (`zod-validation-error@4.0.2`); no frontend dependency was added or changed by this patch.
