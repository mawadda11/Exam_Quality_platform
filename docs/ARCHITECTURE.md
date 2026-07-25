# Architecture

## Context
A browser client submits analysis metadata and two files to a FastAPI API. The API persists metadata, secures file storage, and enqueues a staged background analysis. Extraction adapters produce structured records. Deterministic rules and semantic AI evaluators consume evidence plus filtered KB records. Validated findings are stored and rendered into a report.

The design-authorized target architecture is evidence-gated:

`confirmed source evidence -> deterministic checks -> constrained semantic relationships -> deterministic aggregation and scoring`

Milestone M1 freezes this target. M2 implements only its dormant persistence and strict internal
schema foundation: no review revision is created yet, and the review pause, API, UI,
categorical-confidence runtime behavior, and expanded semantic evaluators remain planned.

## Components
- React frontend: upload, progress, results, evidence drill-down, history, report download.
- FastAPI API: authentication boundary, validation, orchestration endpoints, result queries.
- Worker: staged processing and retry-safe state transitions.
- PostgreSQL: transactional domain and traceability data.
- ChromaDB: replaceable vector retrieval implementation.
- Object/file storage abstraction: uploads, extracted assets, reports.
- AI provider adapter: structured semantic evaluation.
- OCR/layout adapters: provider-neutral extraction interfaces.

## Currently implemented processing flow
1. `queued`
2. `validating`
3. `extracting_exam`
4. `extracting_tp153`
5. `building_evidence`
6. `retrieving_knowledge`
7. `applying_rules`
8. `generating_report`
9. `completed`

Failures use a separate processing state and error record. They never become an academic status.

The currently implemented runner is uninterrupted and the currently implemented semantic runtime
contains RULE002, RULE004, and RULE008. Numeric semantic confidence is still stored and displayed.
These are explicit planned gaps, not the approved target contract.

## Design-authorized target processing flow

1. Upload and parser validation.
2. Exam and TP-153 extraction.
3. Durable Extraction Review.
4. Source-faithful correction, restoration, or false-positive exclusion.
5. Explicit extraction confirmation.
6. Deterministic evidence and applicability gates.
7. Constrained semantic relationships over confirmed source records.
8. Deterministic coverage, marks, numbering, and score aggregation.
9. Validated findings and completed results.
10. On-demand immutable report.

No AI call occurs before step 5. Review never creates official CLOs, topics, assessment records, or
mappings. Explicit source mappings remain separate from labeled AI-derived relationships.

## Key design decisions
- Immutable analysis versions.
- Domain enums shared through generated/documented API contracts.
- AI output validated before persistence.
- Page-aware evidence and explicit source IDs.
- Deterministic score and arithmetic checks.
- Deterministic coverage aggregation over validated relationships.
- Categorical semantic confidence derived by backend validation, not model self-assessment.
- Low semantic confidence produces Not Verified.
- Concise evidence-to-rule reasoning rather than private model chain-of-thought.
- KB files mounted read-only in runtime environments.
- External providers hidden behind interfaces for testing and replacement.

See `docs/DESIGN_DECISIONS.md` for alternatives, technical justification, academic justification,
consequences, and limitations.
