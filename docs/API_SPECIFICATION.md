# API Specification

Base path: `/api/v1`

Unless an endpoint is explicitly marked **Planned**, it describes the currently implemented API.
Planned contracts are design-authorized by M1 but must not be treated as available until their
implementation milestone is complete. M3 adds `review_ready`; M4-M5 implement the owner-scoped
Extraction Review API and workspace. Categorical semantic-confidence API changes remain planned.

## Health
- `GET /health`

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
  `ai_model`, `prompt_template_version`, and `kb_version` provenance fields.
- `GET /analyses/{id}/clos` raw CLO records extracted from TP-153 (alignment/coverage appear as
  Findings, not here).
- `GET /analyses/{id}/topics` raw topic records extracted from TP-153 (alignment/coverage appear
  as Findings, not here).
- `GET /analyses/{id}/score` (M9) read-time score, denominator, and all five status counts,
  computed from the analysis's current Findings - never persisted (see `docs/DATABASE_SCHEMA.md`).
- `GET /analyses/{id}/recommendations` controlled KB recommendations resolved from a semantic
  finding's validated stored recommendation ID, or from the legacy deterministic
  `(rule_id, status)` mapping.
- `POST /analyses/{id}/reanalysis` create linked revised analysis. (Milestone 10.)
- `GET /analyses` owned analysis history.

## Reports
- `POST /analyses/{id}/reports` generate report.
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

## Planned semantic Finding contract

The planned additive Finding response exposes:

- Decision through the existing academic status;
- Evidence Used through validated evidence references and safe excerpts;
- Concise Reasoning through the existing explanation;
- categorical `confidence_level` (`High`, `Medium`, or `Low`);
- versioned rule-specific evaluation details, including derived mapping pairs where applicable;
  and
- an optional controlled Recommendation.

Explicit source mappings and derived relationships must be labeled separately. Derived mappings
reference only confirmed existing question and target IDs, never overwrite extracted source
evidence, and never become source evidence.

The backend derives confidence from validated evidence conditions. Low confidence requires Not
Verified. The current API still returns numeric finding confidence until its planned replacement;
clients must not interpret that implementation gap as the approved target contract.

M2 persists nullable `confidence_level` and `evaluation_details` columns but does not expose or
populate them. `SemanticConfidenceLevel` from the shared backend domain is the only authorized
categorical-confidence enum for the future API. The internal version 1 `evaluation_details`
contract contains `decision`, `evidence_used`, `reasoning`, and `recommendation` (a controlled ID
or null).
