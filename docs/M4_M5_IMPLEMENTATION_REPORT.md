# M4-M5 Implementation Report

## Delivery identity

- Base commit: `ff78686` (`feat: implement M3 extraction review pause`)
- Delivery branch: `m4-m5-extraction-review`
- Delivery policy: changes remain uncommitted for manual review before commit and merge.
- Database migration: none. M2's immutable review-revision persistence and confirmed-revision
  pointer are reused.

## M4 - Review and Confirmation API

### Added API endpoints

- `GET /api/v1/analyses/{analysis_id}/extraction-review`
- `PUT /api/v1/analyses/{analysis_id}/extraction-review`
- `POST /api/v1/analyses/{analysis_id}/extraction-review/confirm`

Every endpoint uses the existing owned-analysis dependency, so inaccessible and cross-owner analyses
remain owner-safe `404` responses.

### Review contract

The API returns the latest immutable revision together with revision 1, warnings, source anchors,
and edit/confirmation eligibility. A saved edit appends a complete immutable revision; it never
updates or deletes an earlier revision.

The backend permits only source-faithful transcription correction, restoration, and false-positive
exclusion. It rejects:

- added or removed source-record identifiers;
- modified immutable page, geometry, hierarchy, sequence, source-document, evidence-type, or
  extraction-confidence anchors;
- stale base revisions;
- confirmation of a non-latest revision; and
- any review write after confirmation.

Corrections to question, CLO, topic, and assessment source records are normalized into their linked
trace evidence so downstream evaluators cannot consume stale duplicate text.

### Confirmation boundary

Confirmation revalidates the selected revision against immutable revision 1, materializes only the
included reviewed source transcription into canonical downstream tables, binds the exact revision
to `analyses.confirmed_review_id`, and atomically claims `building_evidence`.

Only after that commit does the API schedule `run_post_confirmation_pipeline`. The worker accepts
only the exact confirmed revision and ignores delayed, mismatched, or duplicate jobs. The
confirmation event is recorded once; the continuation worker does not duplicate it.

## M5 - Minimal Extraction Review UI

### Routing and workflow

- A `review_ready` analysis routes to `/analyses/{analysis_id}/review`.
- The progress poll stops at `review_ready` and redirects to the dedicated review workspace.
- After confirmation, the UI returns to progress while the guarded downstream pipeline continues.
- The workflow stepper now includes a distinct Extraction Review step.

### Workspace capabilities

The workspace provides tabs for:

- Questions
- CLOs
- Topics
- Assessment records
- Evidence

It displays source page and extraction-confidence anchors, warnings, revision status, and
confirmation blockers. The user can correct editable transcription fields, exclude false-positive
records, restore original machine values, save a new immutable revision, and confirm the exact
saved revision.

Question exclusions cascade to descendants and linked trace evidence. Re-including a child question
or linked evidence re-includes its source-question ancestors, preventing an invalid draft reference
graph. Confirmation remains disabled while unsaved changes exist.

## Governance preserved

This delivery does not:

- create official CLOs, topics, assessment records, mappings, requirements, or policy thresholds;
- allow AI to run before extraction confirmation;
- change scoring, semantic evaluators, or categorical-confidence policy;
- implement academic approval or accreditation conclusions; or
- alter the controlled knowledge base.

M6 and later remain responsible for the approved semantic-output redesign and expanded governed
analysis.
