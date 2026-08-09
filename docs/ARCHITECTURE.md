# Architecture

## Context
A browser client submits analysis metadata and two files to a FastAPI API. The API persists metadata, secures file storage, and enqueues a staged background analysis. Extraction adapters produce structured records. Deterministic rules and semantic AI evaluators consume evidence plus filtered KB records. Validated findings are stored and rendered into a report.

The design-authorized target architecture is evidence-gated:

`confirmed source evidence -> deterministic checks -> constrained semantic relationships -> deterministic aggregation and scoring`

Milestone M1 freezes this target. M2 implements its persistence and strict internal schema
foundation. M3 creates immutable revision 1 and pauses new analyses at `review_ready`. M4-M5 now
implement source-faithful review revisions, exact-revision confirmation, guarded continuation, and
the review workspace. M6-M9 now add backend-derived categorical confidence, all ten governed
semantic/hybrid evaluators, deterministic mapping coverage, and complete rule-capability auditing.

## Components
- React frontend: upload, progress, results, evidence drill-down, history, report download.
- FastAPI API: authentication boundary, validation, orchestration endpoints, result queries.
- Worker: staged processing and retry-safe state transitions.
- PostgreSQL: transactional domain and traceability data.
- ChromaDB: replaceable vector retrieval implementation.
- Object/file storage abstraction: uploads, extracted assets, reports.
- AI provider adapter: structured semantic evaluation.
- OCR/layout adapters: provider-neutral extraction interfaces.

## Currently implemented review-gated processing flow

The detailed provider-neutral OCR, reconciliation, structure parsing, source
provenance, and review-v2 contracts are documented in
[`EXTRACTION_ARCHITECTURE.md`](EXTRACTION_ARCHITECTURE.md). Native pdfplumber
and local Tesseract remain independent evidence paths; no cloud OCR provider is
part of this release.
1. `queued`
2. `validating`
3. `extracting_exam`
4. `extracting_tp153`
5. materialize immutable extraction-review revision 1
6. `review_ready`
7. exact latest review revision confirmed
8. `building_evidence`
9. `retrieving_knowledge`
10. `applying_rules`
11. `generating_report`
12. `completed`

Failures use a separate processing state and error record. They never become an academic status.

The initial runner stops at `review_ready`. The review API appends immutable revisions and
atomically binds the exact latest revision to `analyses.confirmed_review_id`. Only then does a
separate continuation worker run `building_evidence`, `retrieving_knowledge`, `applying_rules`,
and `generating_report`; duplicate or mismatched continuation tasks are ignored. The existing
downstream semantic implementation contains the complete ten-rule target. Numeric confidence is
retained only as a derived compatibility field; categorical confidence is authoritative. M10 will
refine presentation of
that runtime contract.

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


## M9 runtime coverage boundary

The rule-coverage service compares persisted Findings with the governed capability manifest for all
21 exam-facing rules. It exposes implementation disposition separately from academic status, making
unsupported/deferred rules and unexpected supported-rule omissions visible without contaminating
scoring.
