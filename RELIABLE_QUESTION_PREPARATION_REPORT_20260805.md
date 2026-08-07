# Exam Quality Analyzer — Reliable Question Preparation Implementation Report

Date: 2026-08-05  
Release basis: existing `2.0.0-rc1` repository, with no database migration.

## Implemented product decision

The application no longer treats universal automatic PDF understanding as a requirement for a valid analysis. Question preparation is now an explicit, governed choice made before processing:

1. **Assisted extraction from PDF (`assisted_pdf`)**
   - The deterministic PDF parser proposes question records.
   - Wrapped question text continues until the next explicit question marker instead of stopping at the first line.
   - Figure labels and page-wide decorative/vector regions are filtered conservatively.
   - The Faculty Member must review and confirm the exact revision before academic analysis.

2. **Structured question template (`structured_template`) — recommended**
   - The exam PDF remains the immutable visual reference.
   - The platform does not create automatic questions.
   - Extraction Review provides a downloadable Excel-compatible CSV template and imports a completed CSV.
   - One source-faithful row represents one question. Multiple-choice options, parent question, page number, type, and visible marks can be supplied.
   - Empty marks remain unknown; the system never invents marks.

3. **Manual visual review from PDF (`manual_pdf`)**
   - The platform does not create automatic questions.
   - The Faculty Member selects each question region from the PDF and enters the complete source-faithful wording.
   - Questions remain editable and traceable to the selected source region.

The uploaded examination PDF and populated Course Specification remain required in every mode.

## Academic and AI boundary

- Academic results are generated only after the exact Extraction Review revision is confirmed.
- Gemini is not required for question preparation.
- Existing post-confirmation semantic AI can use Gemini only when explicitly configured through the existing `AI_PROVIDER=gemini` settings.
- Extraction Gemini remains a separate optional feature and is disabled by default.
- No real Gemini request was made during this implementation or its automated tests.
- Missing marks remain empty. No model or deterministic rule invents a mark.

## Reliability changes

- Added provider-neutral `QuestionPreparationMode` values and API validation.
- Persisted the selected preparation mode without adding a database column or migration.
- Retries preserve the selected mode, including failures occurring before exam extraction.
- Manual and structured modes retain PDF evidence and TP-153 extraction while intentionally producing zero automatic questions.
- Structured import validates required columns, supported question types, unique labels, parent references, pages, marks, and MCQ options.
- Structured questions can be confirmed with a source page and no fabricated PDF geometry.
- Manual questions require a real selected PDF region.
- Imported/manual questions and options materialize to canonical records only after review confirmation.
- Assisted extraction now preserves multiline questions across line wrapping, vertical spacing, and an interposed diagram until the next question marker.
- Visual question crops are constrained by the current question stem and the next question boundary, reducing neighboring-question bleed.
- Section headings and shared instructions are not presented as missing questions requiring resolution.

## Frontend workflow

- Added a three-mode choice to **Review and Start**.
- Added mode-specific guidance in Extraction Review.
- Added a structured CSV download/import panel.
- Added Arabic translations for the new workflow and validation messages.
- Kept advanced extraction diagnostics collapsed.
- Preserved the original PDF as the visual source reference in every mode.

## Files added

- `backend/app/services/extraction/preparation_mode.py`
- `frontend/src/features/extraction-review/structuredQuestionTemplate.ts`
- `frontend/src/features/extraction-review/structuredQuestionTemplate.test.ts`
- `frontend/src/features/extraction-review/questionVisualGeometry.ts`
- `frontend/src/features/extraction-review/questionVisualGeometry.test.ts`
- `docs/QUESTION_PREPARATION_AND_REVIEW_PLAN.md`
- `docs/STRUCTURED_QUESTION_TEMPLATE.md`
- `sample_data/Exam_Quality_Question_Template.csv`

## Main files modified

- `backend/app/core/domain.py`
- `backend/app/schemas/analysis.py`
- `backend/app/schemas/extraction_review.py`
- `backend/app/api/analyses.py`
- `backend/app/services/processing/runner.py`
- `backend/app/services/processing/stages.py`
- `backend/app/services/extraction/digital_pdf_extractor.py`
- `backend/app/services/extraction/review_snapshot.py`
- `backend/app/services/extraction/review_workflow.py`
- `frontend/src/api/analyses.ts`
- `frontend/src/types/api.ts`
- `frontend/src/routes/AnalysisWorkflowRoute.tsx`
- `frontend/src/features/analysis-upload/ReviewStartSummary.tsx`
- `frontend/src/features/analysis-upload/ProcessingStatus.tsx`
- `frontend/src/features/extraction-review/ExtractionReviewWorkspace.tsx`
- `frontend/src/i18n/additionalArabicMessages.ts`
- `frontend/src/styles/analysis-workflow.css`
- `frontend/src/styles/extraction-review.css`
- `README.md`
- `.env.example`
- `docs/EXTRACTION_ARCHITECTURE.md`
- `docs/HUMAN_ASSISTED_EXTRACTION_REVIEW.md`
- `docs/KNOWN_LIMITATIONS.md`
- `FILE_INVENTORY.md`

## Verification completed

### Backend

- All **806 collected backend tests** passed when executed in non-overlapping groups covering all 78 test files.
- Targeted tests cover all three modes, retry persistence, zero-question review behavior, structured import persistence, multiline questions, diagram interruption, and review confirmation.
- Python compile validation passed for application and test modules.
- Knowledge-base validation passed: **441 normalized records across 11 workbooks**.

### Frontend

- All **175 TypeScript/TSX source files** passed TypeScript parser validation.
- The pure TypeScript modules for the structured importer, question geometry, and API types passed direct `tsc --noEmit` checking using the installed TypeScript compiler.
- New deterministic unit tests were added for the CSV importer and question visual geometry.
- The full npm/Vitest/lint/build gate could not be executed in this environment because the internal npm registry returned HTTP 404 for required packages. This is an environment dependency-fetch failure, not a claimed passing gate.

## Scope and honest limitations

- The structured CSV is Excel-compatible, but direct `.xlsx` and Word template import are not implemented in this release.
- Assisted PDF extraction is still a proposal and is not guaranteed to understand every examination layout.
- Irregular, scanned, handwritten, multi-column, cross-page, or diagram-heavy exams should use manual visual review or the structured template.
- Tables and diagrams remain part of the visual source; the platform does not promise cell-by-cell or arrow-by-arrow interpretation.
- Semantic relationships to CLOs/topics require confirmed question text. When AI is unavailable or evidence is insufficient, the governed status must remain `Not Verified` rather than inventing a relationship.

## Recommended demonstration path

For the most dependable pilot/demo:

1. Upload the exam PDF and matching TP-153.
2. Select **Structured question template**.
3. Download the CSV, complete one row per question, and import it.
4. Compare each question against the PDF and correct any wording/type/visible mark.
5. Confirm the exact review revision.
6. Run the governed academic analysis.

This preserves the project's academic value while removing universal PDF parsing as a single point of failure.
