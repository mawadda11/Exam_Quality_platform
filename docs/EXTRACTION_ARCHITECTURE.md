# Exam extraction architecture

## Runtime flow

The owner chooses a question-preparation mode before processing:

### `assisted_pdf`

1. Validate the owner-scoped stored exam PDF.
2. Extract native text and layout with `pdfplumber`; use bounded local Tesseract only when required.
3. Reconcile provider evidence and parse a deterministic question proposal.
4. Preserve wrapped text until the next explicit question marker. Vector-diagram labels, table-cell
   text, captions, and page decoration are not silently appended to the canonical stem.
5. Persist questions, hierarchy, visible marks, options, simple blanks, source spans, supporting
   visuals, references, and warnings.

### `manual_pdf`

1. Validate and retain the original PDF and page diagnostics.
2. Deliberately persist no automatic question facts.
3. In Extraction Review, the Faculty Member adds each question with a required PDF region and
   source-faithful transcription.

### `structured_template`

1. Validate and retain the original PDF and page diagnostics.
2. Deliberately persist no automatic question facts.
3. In Extraction Review, import a controlled CSV containing complete question text, supported type,
   source page, optional visible marks, hierarchy, and MCQ options. Imported facts are reviewed
   against the original PDF. No geometry is invented.

All modes then:

1. Extract the populated TP-153 independently.
2. Create immutable Extraction Review snapshot schema version 2 and pause in `review_ready`.
3. Require at least one included, source-faithful question and exact-revision confirmation.
4. Continue to evidence, deterministic checks, constrained semantic relationships, findings, score,
   and report only after confirmation.

Historical schema-version-1 review snapshots remain readable. They receive empty defaults for
version-2 collections and are never rewritten.

## Replaceable OCR boundary

`DocumentOcrProvider` accepts a PDF path and returns only provider-neutral
`NormalizedOcrDocument`, `NormalizedOcrPage`, `NormalizedOcrLine`, and
`NormalizedOcrToken` values. Provider SDK objects may not cross this boundary.
Question parsing, persistence, review, rules, APIs, frontend, and reporting
depend only on normalized models.

Tesseract is the sole supported OCR adapter in this release. It runs locally,
renders every page at the governed resolution, and preserves recognized text
without spelling correction. Native pdfplumber extraction remains a separate
evidence path. To add another engine later, implement the interface, map the
engine response into the normalized models, extend the factory configuration,
and add adapter contract tests; downstream modules do not change.

Configuration:

- `EXAM_OCR_PROVIDER=tesseract`
- `EXAM_OCR_FALLBACK_ENABLED=true` (reserved for a future alternate-primary
  adapter; local Tesseract remains the fallback contract)

No OCR credentials, runtime downloads, or cloud OCR dependencies are used.

## Reconciliation and blockers

Reconciliation compares wording, question numbers, marks, options, reading
order, unassigned content, duplicates, and technical strings. Warnings include
stable source-line IDs and geometry. Critical warnings such as
`CRITICAL_TEXT_MISMATCH`, `QUESTION_NUMBER_MISMATCH`, `MARKS_MISMATCH`,
`OPTION_MISSING`, `OPTION_TEXT_MISMATCH`, `ORPHAN_OPTION`, and
`SOURCE_LINE_NOT_FOUND` block confirmation until the reviewer explicitly marks
them resolved in a newly saved immutable revision.

Numeric OCR confidence is extraction metadata and is not the governed semantic
confidence category used by academic evaluators.

## Exam structure parsing

`ExamStructureParser` is separate from academic `AIProvider` implementations.
The deterministic parser is always available and independently produces local
question, hierarchy, type, option, blank, marks, shared-instruction, table,
figure, geometry, source-span, confidence, and warning candidates. It uses
stable local identities; repeated visible question numbers are not identifiers.

If `EXTRACTION_AI_ENABLED=true`, `GeminiExamStructureParser` receives each
selected complete page image together with normalized lines and tokens, stable
source-line IDs, PDF-coordinate geometry, local candidates, supporting
materials, and extraction warnings. It independently proposes question
boundaries, hierarchy, options versus lettered subquestions, T/F statements,
blanks, matching layouts, marks, tables, figures, UML/code relationships, and
repeated decoration in strict Pydantic-validated JSON.

Source-line text remains canonical. Candidate transcription for content that
is visible but absent locally is accepted only after a Tesseract crop of the
reported geometry supplies source lines. A disagreement or failed recovery
creates a critical review blocker; Gemini text never silently replaces native
or OCR evidence. Reconciliation retains both pipeline candidates and compares
boundaries, text, labels, types, hierarchy, marks, options, blanks,
instructions, material associations, geometry, and provenance field by field.

Outputs are rejected when they reference missing lines, invent unsupported
text, create invalid hierarchy, assign a stem line incompatibly, omit required
options without an uncertainty warning, or fail schema validation. With
`AI_FAILOVER_ENABLED=true`, an availability failure on the primary Gemini model
retries the same extraction on `GEMINI_FALLBACK_MODEL`; if that model is also
unavailable, deterministic extraction is retained. The downgrade is sticky for
the remainder of that analysis, including post-review semantic evaluation, while
every new analysis starts from the primary model again. Non-availability parser
failures preserve the established conservative deterministic fallback without
changing the analysis's model route. Extraction assistance cannot produce
academic findings, mappings, scores, recommendations, statuses, or accreditation
conclusions.

Configuration:

- `EXTRACTION_AI_ENABLED=false`
- `EXTRACTION_AI_PROVIDER=gemini`
- `EXTRACTION_AI_MODEL=gemini-3.6-flash`
- `EXTRACTION_AI_VALIDATION_RETRIES=1`
- `EXTRACTION_AI_PAGE_DPI=144`
- `EXTRACTION_AI_MAX_PAGES_PER_DOCUMENT=25`
- `EXTRACTION_AI_CACHE_ENABLED=true`
- `EXTRACTION_AI_TARGETED_OCR_ENABLED=true`
- `EXTRACTION_AI_CANDIDATE_MIN_CONFIDENCE=0.55`
- `AI_FAILOVER_ENABLED=true`
- `GEMINI_FALLBACK_MODEL=gemini-3.5-flash-lite`
- `AI_LOCAL_FALLBACK_MODEL=local-governed-baseline-v1`
- `GEMINI_API_KEY` is required only when extraction AI is enabled (or when the
  separate academic Gemini provider is selected).

The disabled default is the local-development and quota-preserving mode. One
validated structure response is cached beside the owner-scoped upload using a
content/model/prompt hash; repeat processing reuses it. The configured page cap
is a hard quota guard and produces a critical blocker when it prevents every
page from being inspected. The cache contains private extraction data, is never
logged, and is removed with analysis artifacts.

## Review, preview, and deletion privacy

The original exam preview is returned only through an owner-authorized bearer
token endpoint. The frontend fetches a Blob and creates a temporary object URL;
storage keys and server paths are never returned. Selecting a question, option,
blank, warning, or retained local/Gemini candidate moves to its page and
overlays stored geometry. Reviewers can edit existing hierarchy, options,
blanks, marks, types, and material/reference question associations without
altering immutable source spans or the original machine revision.

Analysis deletion is allowed only in `queued`, `review_ready`, `completed`, or
`failed`. Active stages return 409. A predecessor referenced by historical
reanalysis is retained. Database cascades remove analysis-owned rows after the
confirmed-review circular link is cleared; uploaded and generated artifacts
are resolved through safe server-side storage helpers and removed best effort,
including the validated Gemini structure cache when present.
A missing physical artifact does not prevent database deletion. Courses are
not deleted.

## Preparation-mode persistence

No database migration is required. The selected mode is stored in the existing exam-file parser
metadata using a versioned `question_preparation:` prefix and copied into the immutable review
snapshot. A retry reuses that persisted mode. The mode cannot be changed after processing starts.

## Academic Gemini boundary

`AI_PROVIDER=gemini` is a separate post-confirmation semantic provider. It may interpret governed
relationships between confirmed questions and confirmed TP-153 records. It may not create source
questions, marks, CLOs, topics, official mappings, thresholds, or scores. `EXTRACTION_AI_ENABLED`
controls a separate optional visual structure parser and remains false by default.

## Tests

Automated tests use fake OCR and fake Gemini clients. They must never contact an
external provider. Synthetic fixtures cover mixed text, options versus
subquestions, marks, question types, provenance, reconciliation blockers,
snapshot compatibility, preview authorization, and deletion safety.
