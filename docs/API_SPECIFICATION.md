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
- `GET /analyses/{id}/findings` filterable findings.
- `GET /analyses/{id}/clos` CLO mappings and coverage.
- `GET /analyses/{id}/topics` topic mappings and coverage.
- `GET /analyses/{id}/recommendations` recommendations.
- `POST /analyses/{id}/reanalysis` create linked revised analysis.
- `GET /analyses` owned analysis history.

## Reports
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
