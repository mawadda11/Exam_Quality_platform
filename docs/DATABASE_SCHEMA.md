# Database Schema

This file lists the currently implemented schema. Milestone M2 added the minimum durable
Extraction Review foundation in migration `0008`. M3 uses that unchanged schema to create revision
1 and pause processing; it creates no migration and adds no review API or categorical semantic
behavior.

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
- `extraction_review_revisions`: immutable analysis-local, versioned extraction snapshots.

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

## M2 persistence and M3 initial snapshot - currently implemented

Migration `0008` adds one table and three nullable columns. Existing analyses and Findings require
no backfill, and current runtime/API behavior remains unchanged until later milestones.

### Table: `extraction_review_revisions`

Each row represents one immutable complete review snapshot:

- `id`: revision identity.
- `analysis_id`: owning analysis.
- `revision_number`: positive, unique analysis-local version.
- `snapshot`: versioned JSON containing only source-faithful extraction entities and evidence that
  genuinely existed when the snapshot was created. Empty collections are valid; placeholder
  questions, CLOs, topics, or assessment records are prohibited.
- `created_at`: audit ordering.

The internal Pydantic contract uses `schema_version = 1`, stable source-record identifiers,
source-faithful fields, explicit inclusion state, source geometry, and numeric
`extraction_confidence`. It permits empty entity collections and validates internal question and
evidence references. M3 creates revision 1 idempotently from genuine persisted machine extraction
rows. Concurrent creation uses a savepoint and safe requery; empty collections stay empty and no
placeholder records are fabricated. M4 will append review saves and enforce
correction/restoration/exclusion-only behavior against that original revision.

### Columns added to existing tables

- `analyses.confirmed_review_id`: binds all downstream results to the exact confirmed snapshot.
- `findings.confidence_level`: nullable categorical semantic confidence; deterministic and legacy
  findings may remain null.
- `findings.evaluation_details`: versioned JSON for rule-specific derived details and confidence
  basis.

`SemanticConfidenceLevel` in `app.core.domain` is the single authoritative `High`/`Medium`/`Low`
enum for ORM, Pydantic, API, and future AI logic. Alternative semantic-confidence enums are
prohibited. The existing numeric `findings.confidence` is retained temporarily for compatibility
but must not be threshold-converted into categories.

`evaluation_details` remains null and unused in M2. Its version 1 internal core contract is:

- `decision`: one approved academic status;
- `evidence_used`: unique evidence UUIDs;
- `reasoning`: concise evidence-to-rule reasoning, never private chain-of-thought; and
- `recommendation`: a controlled KB recommendation ID or null.

The JSON also carries `schema_version = 1`. Future rule-specific schemas may extend this core
contract without replacing or renaming its required fields.

### Explicitly rejected Version 1 schema additions

- child edit-event tables;
- a separate semantic-mapping table;
- a confidence-basis column;
- a reasoning table;
- review-status columns duplicating analysis state; and
- reviewed-value columns duplicated across each extraction entity.

These additions are unnecessary for the bounded Version 1 workflow. Derived mappings remain
analysis details on their authoritative Finding and never use Exam or TP-153 source provenance.
