# Database Schema

This file lists the currently implemented schema. Milestone M2 added the minimum durable
Extraction Review foundation in migration `0008`. M3 creates revision 1 and pauses processing.
M4-M5 reuse the same schema to append immutable review revisions, bind the exact confirmed revision,
and continue processing. M6-M9 reuse the same nullable semantic columns and populate them; no new
database migration is required.

## Core tables
- `users`: Faculty Member identity, institution, department, password hash, activation state, token version, and last login. Version 1 does not require multi-role authorization.
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
- `password_reset_tokens`: hashed single-use reset token, owner, expiry, and used time.
- `extraction_review_revisions`: immutable analysis-local, versioned extraction snapshots.

## Constraints
- Academic status is a database enum or checked value.
- One released finding belongs to one rule execution.
- `(analysis_id, rule_id)` is unique, preventing duplicate deterministic or semantic findings.
- Every finding-evidence link is application-validated to keep finding and evidence ownership on
  the same analysis.
- Analysis versions are immutable after completion except permitted review metadata.
- `predecessor_analysis_id` is retained on `analyses` for backward compatibility with historical
  reanalysis records; no current workflow sets it on newly created analyses. Evaluating a revised
  exam uses New Analysis.
- File hashes support integrity and duplicate detection.
- Page indexing convention: API uses 1-based page numbers; internal extractor offsets must be converted at the boundary.

## Current persistence note
The `analyses` table intentionally has no persisted score or general KB-version column:
- Overall score (`GET /analyses/{id}/score`) and recommendations
  (`GET /analyses/{id}/recommendations`) are computed read-time from the analysis's current
  `findings` rows plus controlled KB data.
- `predecessor_analysis_id` preserves linked-analysis history from historical reanalysis records
  only; it is not set by any current workflow.
- Generated report rows persist their KB version and aggregate scoring snapshot.
- Semantic findings persist the exact KB and prompt versions used for their evaluation.

## M2-M5 Extraction Review persistence - currently implemented

Migration `0008` adds one table and three nullable columns. Existing analyses and Findings require
no backfill. M3-M5 now use the review table and confirmation pointer without adding another
migration.

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
placeholder records are fabricated. M4 appends complete immutable snapshots only after validating
the original source-record set and immutable source anchors. M4 confirmation points to the exact
latest revision, materializes included reviewed fields into the canonical extraction tables for
existing downstream evaluators, and leaves revision 1 unchanged as the machine-extraction audit
record. Excluded false-positive rows are removed only from the canonical post-confirmation view.

### Columns added to existing tables

- `analyses.confirmed_review_id`: binds all downstream results to the exact confirmed snapshot.
- `findings.confidence_level`: nullable categorical semantic confidence; deterministic and legacy
  findings may remain null.
- `findings.evaluation_details`: versioned JSON for rule-specific derived details and confidence
  basis.

`SemanticConfidenceLevel` in `app.core.domain` is the single authoritative `High`/`Medium`/`Low`
enum for ORM, Pydantic, API, and AI validation. Alternative semantic-confidence enums are
prohibited. The existing numeric `findings.confidence` is retained temporarily as a categorical
compatibility projection (High=1, Medium=.5, Low=0); it is never provider-supplied and must not be
threshold-converted into categories.

`evaluation_details` remains null and unused in M2. Its version 1 internal core contract is:

- `decision`: one approved academic status;
- `evidence_used`: unique evidence UUIDs;
- `reasoning`: concise evidence-to-rule reasoning, never private chain-of-thought; and
- `recommendation`: a controlled KB recommendation ID or null;
- `confidence_basis`: backend-observed reasons for the categorical level;
- `item_judgments`: source-to-controlled-target judgments; and
- `retrieved_knowledge_ids`: governed KB records retrieved for the evaluation.

The JSON carries `schema_version = 1`. M6-M9 populate this contract for semantic findings while
deterministic findings may keep both semantic fields null.

### Explicitly rejected Version 1 schema additions

- child edit-event tables;
- a separate semantic-mapping table;
- a confidence-basis column;
- a reasoning table;
- review-status columns duplicating analysis state; and
- reviewed-value columns duplicated across each extraction entity.

These additions are unnecessary for the bounded Version 1 workflow. Derived mappings remain
analysis details on their authoritative Finding and never use Exam or TP-153 source provenance.


## Version 2 Batch 1 authentication persistence

Migration `0009` adds nullable `users.password_hash` for safe Version 1 upgrades, plus non-null
`is_active`, `email_verified`, and `token_version`, and nullable `last_login_at`. New public accounts
always receive a password hash. Existing development identities receive no invented credential.

`password_reset_tokens` stores only SHA-256 hashes of random reset tokens. Each row belongs to one
user and contains `expires_at` and nullable `used_at`; confirmation is rejected after expiry or first
use. Password reset increments `users.token_version`, invalidating older bearer tokens.

## Version 2 Batch 3 bilingual and retry metadata

Migration `0011` adds:

- `users.preferred_language`: non-null controlled `ar` / `en` preference, defaulting to Arabic for
  upgraded and newly created accounts unless explicitly changed;
- `processing_events.failed_stage`: nullable exact pipeline stage that failed;
- `processing_events.error_code`: nullable safe stable failure code;
- `processing_events.retryable`: non-null operational retry eligibility flag;
- `reports.language`: non-null language of the immutable generated PDF snapshot.

Failure events retain only safe user-facing metadata. Server exception details remain in protected
logs. Retry does not overwrite the confirmed extraction revision, prior events, completed reports,
or source uploads.
