# API Specification

Base path: `/api/v1`

## Health
- `GET /health`

## Analyses
- `POST /analyses` create metadata.
- `POST /analyses/{id}/files` upload exam and TP-153.
- `POST /analyses/{id}/run` enqueue analysis.
- `GET /analyses/{id}` status and summary.
- `GET /analyses/{id}/progress` stage and safe progress.
- `GET /analyses/{id}/questions` question summaries.
- `GET /analyses/{id}/findings` filterable findings, enriched (M9) with each finding's official
  requirement display metadata (`requirement_name`, `dimension`, `source_type`, `officiality`)
  resolved from the KB.
- `GET /analyses/{id}/clos` raw CLO records extracted from TP-153 (alignment/coverage appear as
  Findings, not here).
- `GET /analyses/{id}/topics` raw topic records extracted from TP-153 (alignment/coverage appear
  as Findings, not here).
- `GET /analyses/{id}/score` (M9) read-time score, denominator, and all five status counts,
  computed from the analysis's current Findings - never persisted (see `docs/DATABASE_SCHEMA.md`).
- `GET /analyses/{id}/recommendations` (M9) KB recommendations resolved read-time from each
  Finding's `(rule_id, status)` - never persisted.
- `POST /analyses/{id}/reanalysis` create linked revised analysis. (Milestone 10.)
- `GET /analyses` owned analysis history.

## Reports
Not yet implemented (Milestone 10 - "Report generation and revised-exam history"). The M9 Results
UI's Report section says so explicitly rather than exposing a non-functional control.
- `POST /analyses/{id}/reports` generate report.
- `GET /reports/{id}` metadata.
- `GET /reports/{id}/download` authorized download.

## Conventions
- UUID identifiers.
- 1-based page numbers externally.
- ISO-8601 UTC timestamps.
- Problem Details-style error payloads.
- Academic statuses use exact approved display values or stable documented enum keys.
- File upload is multipart and must be validated server-side.
