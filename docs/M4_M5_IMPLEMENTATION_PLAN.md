# M4-M5 Implementation Plan

## Scope

This delivery completes Version 1.2 Extraction Review without changing the approved academic
boundary.

### M4 - Review and confirmation API

- Add owner-authorized GET, PUT, and confirmation endpoints under
  `/analyses/{analysis_id}/extraction-review`.
- Return the latest immutable review revision together with revision 1, source anchors, warnings,
  and confirmation eligibility.
- Permit only source-faithful correction, restoration, and false-positive exclusion.
- Reject added or removed source records, immutable-anchor changes, stale base revisions, and all
  writes after confirmation.
- Confirm an exact latest revision atomically, materialize its included reviewed values into the
  downstream source tables, and continue only the post-confirmation pipeline.
- Keep revision 1 immutable as the machine-extraction audit record.

### M5 - Minimal Extraction Review UI

- Route `review_ready` analyses to a dedicated review workspace.
- Provide accessible tabs for questions, CLOs, topics, assessment records, and evidence.
- Show page/confidence anchors and review warnings.
- Support field correction, false-positive exclusion, per-record restoration, save-as-new-revision,
  and exact-revision confirmation.
- Stop confirmation when unsaved edits exist and route confirmed analyses back to progress.

## Explicit non-goals

- No manual creation of official CLOs, topics, assessment records, mappings, or requirements.
- No semantic evaluator changes; those remain M6 and later.
- No database migration; M2 persistence is sufficient.
- No approval workflow or academic sign-off.

## Verification

- Backend API/service/runner tests for ownership, stale revision handling, immutable anchors,
  source-record set enforcement, confirmation, materialization, continuation, and idempotent race
  behavior.
- Frontend API, routing, workspace interaction, accessibility, and confirmation tests.
- Full backend pytest, Ruff, mypy, Alembic drift check, frontend ESLint, TypeScript, Vitest, and
  production build.
