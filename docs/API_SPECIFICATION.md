# API Specification

Base path: `/api/v1`

Unless an endpoint is explicitly marked **Planned**, it describes the currently implemented API.
Planned contracts are design-authorized by M1 but must not be treated as available until their
implementation milestone is complete.

## Health
- `GET /health`

## Analyses
- `POST /analyses` create metadata.
- `POST /analyses/{id}/files` upload exam and TP-153.
- `POST /analyses/{id}/run` atomically claims a queued analysis as `validating` and schedules the
  background pipeline.
- `GET /analyses/{id}` status and summary.
- `GET /analyses/{id}/progress` stage and safe progress.
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

## Planned Extraction Review contract

These endpoints are design-authorized but not implemented by M1:

- `GET /analyses/{id}/extraction-review` returns one coherent review snapshot, its revision
  identity, source anchors, warnings, and confirmation eligibility.
- `PUT /analyses/{id}/extraction-review` validates a complete source-faithful reviewed snapshot
  against a base revision and creates a new immutable revision.
- `POST /analyses/{id}/extraction-review/confirm` atomically confirms an exact revision and
  schedules post-confirmation evidence, retrieval, and evaluation stages.

The existing `POST /analyses/{id}/run` is planned to validate, extract, create the initial review
revision, and pause. The existing progress endpoint is planned to expose a review-ready state.

Review writes will be owner-authorized and allowed only while review is open. The review contract
will reject:

- new official CLOs, topics, or assessment records;
- manually created question-to-CLO/topic mappings;
- undocumented institutional requirements;
- AI-generated source records;
- stale revisions; and
- writes after confirmation.

No separate mappings endpoint or per-entity edit API is design-authorized for Version 1. Structured
mapping details will be returned with the authoritative rule Finding.

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
