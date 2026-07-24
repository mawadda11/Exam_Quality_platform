# Database Schema

## Core tables
- `users`: Faculty Member identity, institution, and department. Version 1 does not require multi-role authorization.
- `courses`: course code/name, department, program.
- `analyses`: course/user, exam type, term, state, predecessor, timestamps.
- `uploaded_files`: analysis, type, original name, storage key, MIME, size, hash.
- `questions`: hierarchy, page, text, marks, confidence, geometry.
- `clos`: code, text, optional program-outcome link.
- `topics`: code, text, expected hours.
- `assessment_records`: methods, activities, percentages, source location.
- `evidence`: source, page, item, type, text span, geometry, confidence.
- `findings`: requirement/rule, status, explanation, evaluator type, controlled recommendation ID,
  AI provider/model, prompt-template version, and finding-time KB version.
- `finding_evidence`: many-to-many trace links.
- `reports`: storage key, generated time, format, KB version.
- `processing_events`: stage, state, safe message, timestamps.

## Constraints
- Academic status is a database enum or checked value.
- One released finding belongs to one rule execution.
- `(analysis_id, rule_id)` is unique, preventing duplicate deterministic or semantic findings.
- Every finding-evidence link is application-validated to keep finding and evidence ownership on
  the same analysis.
- Analysis versions are immutable after completion except permitted review metadata.
- Reanalysis uses `predecessor_analysis_id`.
- File hashes support integrity and duplicate detection.
- Page indexing convention: API uses 1-based page numbers; internal extractor offsets must be converted at the boundary.

## Current persistence note
The `analyses` table intentionally has no persisted score or general KB-version column:
- Overall score (`GET /analyses/{id}/score`) and recommendations
  (`GET /analyses/{id}/recommendations`) are computed read-time from the analysis's current
  `findings` rows plus controlled KB data.
- `predecessor_analysis_id` preserves linked reanalysis history.
- Generated report rows persist their KB version and aggregate scoring snapshot.
- Semantic findings persist the exact KB and prompt versions used for their evaluation.
