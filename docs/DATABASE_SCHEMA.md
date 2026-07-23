# Database Schema

## Core tables
- `users`: Faculty Member identity, institution, and department. Version 1 does not require multi-role authorization.
- `courses`: course code/name, department, program.
- `analyses`: course/user, exam type, term, state, score, predecessor, KB version, timestamps.
- `uploaded_files`: analysis, type, original name, storage key, MIME, size, hash.
- `questions`: hierarchy, page, text, marks, confidence, geometry.
- `clos`: code, text, optional program-outcome link.
- `topics`: code, text, expected hours.
- `assessment_records`: methods, activities, percentages, source location.
- `evidence`: source, page, item, type, text span, geometry, confidence.
- `findings`: requirement/rule, status, explanation, model metadata.
- `finding_evidence`: many-to-many trace links.
- `recommendations`: finding, KB recommendation ID, rendered text.
- `reports`: storage key, generated time, format, KB version.
- `processing_events`: stage, state, safe message, timestamps.

## Constraints
- Academic status is a database enum or checked value.
- One released finding belongs to one rule execution.
- Analysis versions are immutable after completion except permitted review metadata.
- Reanalysis uses `predecessor_analysis_id`.
- File hashes support integrity and duplicate detection.
- Page indexing convention: API uses 1-based page numbers; internal extractor offsets must be converted at the boundary.

## M9 status note
This document describes the full target schema; as of M9 the `analyses` table has no `score`,
`predecessor`, or `kb_version` columns yet, and the `recommendations` and `reports` tables do not
exist. This is an explicit M9 decision, not an oversight:
- Overall score (`GET /analyses/{id}/score`) and recommendations
  (`GET /analyses/{id}/recommendations`) are computed read-time from the analysis's current
  `findings` rows plus the versioned KB - no migration was needed or added.
- Persisting a score/recommendation snapshot, `predecessor_analysis_id` (reanalysis), `kb_version`,
  and the `reports` table remain Milestone 10 scope ("Report generation and revised-exam
  history"), where persistence and immutability-at-completion-time genuinely matter (a rendered
  report must reflect the KB version and findings at generation time, not drift with later KB
  edits the way a live read-time view intentionally does).
