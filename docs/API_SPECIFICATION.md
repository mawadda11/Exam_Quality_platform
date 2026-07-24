# API Specification

Base path: `/api/v1`

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
