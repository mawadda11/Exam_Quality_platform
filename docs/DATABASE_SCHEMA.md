# Database Schema

This file lists the currently implemented schema first. The final section records the
design-authorized M2 persistence plan so later sessions can distinguish planned schema from deployed
schema. Milestone M1 creates no table, column, constraint, or migration.

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

## Design-authorized M2 persistence plan - not implemented in M1

The approved minimum persistence design adds one table and three columns in one future migration.
Names remain planned until M2 creates and verifies the migration.

### Planned table: `extraction_review_revisions`

Each row represents one immutable complete review snapshot:

- `id`: revision identity.
- `analysis_id`: owning analysis.
- `revision_number`: monotonic analysis-local version.
- `snapshot`: versioned, strictly validated JSON containing the coherent reviewable extraction.
- `created_at`: audit ordering.

The first revision preserves the original machine extraction. Review saves append complete
snapshots rather than replaying polymorphic edit events. On confirmation, one selected snapshot is
planned to be materialized into the existing relational extraction projection. Relational
extraction records then become immutable for analysis.

### Planned columns

- `analyses.confirmed_review_id`: binds all downstream results to the exact confirmed snapshot.
- `findings.confidence_level`: nullable categorical semantic confidence; deterministic and legacy
  findings may remain null.
- `findings.evaluation_details`: versioned JSON for rule-specific derived details and confidence
  basis.

The existing numeric `findings.confidence` is retained temporarily for compatibility but is not the
approved future semantic-confidence contract. It must not be threshold-converted into categories.

### Explicitly rejected Version 1 schema additions

- child edit-event tables;
- a separate semantic-mapping table;
- a confidence-basis column;
- a reasoning table;
- review-status columns duplicating analysis state; and
- reviewed-value columns duplicated across each extraction entity.

These additions are unnecessary for the bounded Version 1 workflow. Derived mappings remain
analysis details on their authoritative Finding and never use Exam or TP-153 source provenance.
