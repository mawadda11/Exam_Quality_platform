# API Specification

Base path: `/api/v1`

Unless an endpoint is explicitly marked **Planned**, it describes the currently implemented API.
Planned contracts are design-authorized by M1 but must not be treated as available until their
implementation milestone is complete. M3 adds `review_ready`; M4-M5 implement the owner-scoped
Extraction Review API/workspace, the M6-M9 categorical semantic/coverage contracts, and M10
presentation/report refinements are currently implemented. M11 adds integrated release acceptance
without changing the public API contract.

## Health
- `GET /health`


## Authentication
- `POST /auth/register` create a Faculty Member account and return a bearer session.
- `POST /auth/login` authenticate email/password and return a bearer session.
- `GET /auth/me` return the verified current Faculty Member.
- `POST /auth/logout` revoke all currently issued access tokens for the account.
- `POST /auth/password-reset/request` return a generic anti-enumeration response and create a
  single-use reset token for an eligible account.
- `POST /auth/password-reset/confirm` consume the reset token, replace the password hash, and revoke
  earlier access tokens.

All analysis and report endpoints require `Authorization: Bearer <token>`. Development identity
headers are no longer accepted.

## Analyses
- `POST /analyses` create metadata.
- `POST /analyses/{id}/files` upload exam and TP-153.
- `POST /analyses/{id}/run` atomically claims a queued analysis as `validating`, schedules
  extraction, creates immutable extraction-review revision 1, and pauses at `review_ready`.
- `GET /analyses/{id}` status and summary.
- `GET /analyses/{id}/progress` stage and safe progress.
- `GET /analyses/{id}/extraction-review` return the latest immutable review revision, original
  machine snapshot, source anchors, warnings, and edit/confirmation eligibility.
- `PUT /analyses/{id}/extraction-review` validate a complete snapshot against an exact base
  revision and append a new immutable source-faithful revision.
- `POST /analyses/{id}/extraction-review/confirm` atomically confirm the exact latest revision,
  materialize its included reviewed transcription, and schedule guarded downstream processing.
- `GET /analyses/{id}/questions` question summaries.
- `GET /analyses/{id}/findings` filterable findings, enriched (M9) with each finding's official
  requirement display metadata (`requirement_name`, `dimension`, `source_type`, `officiality`)
  resolved from the KB. Semantic findings also expose nullable `recommendation_id`, `ai_provider`,
  `ai_model`, `prompt_template_version`, and `kb_version` provenance fields, categorical
  `confidence_level`, and versioned `evaluation_details`.
- `GET /analyses/{id}/rule-coverage` account for all 21 governed exam-facing rules using operational
  dispositions (`evaluated`, `conditional_capability_gap`, `unsupported`, `not_run`) that are
  deliberately separate from academic statuses.
- `GET /analyses/{id}/clos` raw CLO records extracted from TP-153 (alignment/coverage appear as
  Findings, not here).
- `GET /analyses/{id}/topics` raw topic records extracted from TP-153 (alignment/coverage appear
  as Findings, not here).
- `GET /analyses/{id}/score` (M9) read-time score, denominator, and all five status counts,
  computed from the analysis's current Findings - never persisted (see `docs/DATABASE_SCHEMA.md`).
- `GET /analyses/{id}/recommendations` controlled KB recommendations resolved from a semantic
  finding's validated stored recommendation ID, or from the legacy deterministic
  `(rule_id, status)` mapping.
- `GET /analyses` owned analysis history. Evaluating a revised exam uses `POST /analyses` (New
  Analysis); there is no dedicated reanalysis endpoint.

## Reports
- `POST /analyses/{id}/reports` generate an immutable user-facing PDF snapshot containing the score and denominator context, all five status counts, finding evidence, categorical semantic confidence, governed reasoning, item judgments, source-versus-derived mapping labels, controlled KB references, provenance, and recommendations. Course-wide assessment percentages and platform implementation diagnostics remain internal and are not rendered in the report.
- `GET /analyses/{id}/reports` list report metadata for an analysis.
- `GET /reports/{id}` metadata.
- `GET /reports/{id}/download` authorized download.

## Conventions
- UUID identifiers.
- 1-based page numbers externally.
- ISO-8601 UTC timestamps.
- Problem Details-style error payloads.
- Academic statuses use exact approved display values or stable documented enum keys.
- File upload is multipart and must be validated server-side.
- `review_ready` is an additive processing-state value. It means extraction has paused for review;
  it is not an academic status and does not mean the analysis is completed.

## Extraction Review contract - currently implemented

The existing `POST /analyses/{id}/run` validates, extracts, creates immutable revision 1, and
pauses at `review_ready`. Review requests are owner-authorized and allowed only while review is
open.

`PUT` accepts `{base_revision_id, snapshot}` and returns `201` with the appended revision. The
snapshot must preserve the complete machine-extraction source-record set and immutable anchors;
editable transcription fields and `included` state may change. A stale base revision returns
`409`, source-faithfulness violations return `422`, and inaccessible analyses remain owner-safe
`404` responses.

`POST .../confirm` accepts `{revision_id}` and returns `202` with `building_evidence`. Only the
latest revision may be confirmed. Confirmation binds `analyses.confirmed_review_id`, closes review
writes, materializes the included reviewed transcription for existing downstream evaluators, and
schedules evidence building, KB retrieval, rule application, and report-stage continuation.

The review contract rejects:

- new official CLOs, topics, or assessment records;
- manually created question-to-CLO/topic mappings;
- undocumented institutional requirements;
- AI-generated source records;
- stale revisions; and
- writes after confirmation.

No database migration is required for M4-M5; the immutable revision table and exact confirmation
pointer introduced in M2 are reused. No separate mappings endpoint or per-entity edit API is design-authorized for Version 1. Structured mapping details will be returned with the authoritative rule Finding.

## Semantic Finding contract - currently implemented

Semantic Findings additively expose:

- Decision through the exact academic status;
- Evidence Used through validated same-analysis evidence references;
- Concise Reasoning and item-level judgments through `evaluation_details`;
- categorical `confidence_level` (`High`, `Medium`, or `Low`);
- an optional controlled Recommendation ID; and
- provider/model, prompt-template, KB-version, and retrieved governed-record provenance.

The backend derives confidence from validated evidence conditions. Low confidence requires Not
Verified. Numeric `confidence` remains a derived compatibility field only and is not the
authoritative semantic contract. OCR/extraction confidence is separate.

The rule-coverage endpoint does not create Findings or scores. A supported rule with no persisted
Finding is `not_run`, which is a system coverage gap rather than academic Not Verified.

Explicit source mappings remain source evidence. AI-derived relationships are labeled derived,
reference confirmed IDs, and never overwrite a source mapping or source record.

## Version 2 Batch 3 bilingual and recovery additions

- `PATCH /auth/preferences` updates the authenticated Faculty Member's `preferred_language` using
  the controlled `ar` / `en` language codes.
- `GET /analyses/{id}/progress` additionally returns nullable `failed_stage`, nullable safe
  `error_code`, and `can_retry`.
- `POST /analyses/{id}/retry` atomically resumes an owner-scoped failed analysis from its last
  durable failed-stage boundary. Existing uploads and the exact confirmed review revision are reused;
  file re-upload is not required. A non-failed analysis, missing source files, unsafe boundary, or
  concurrent retry returns `409`.
- `POST /analyses/{id}/reports` accepts an optional `{ "language": "ar" | "en" }` body. Generated
  report metadata includes the selected language. Static report presentation is localized while
  governed source evidence and official knowledge-base wording remain source-faithful.
