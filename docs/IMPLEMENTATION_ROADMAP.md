# Implementation Roadmap

## Status vocabulary

- **Design-authorized**: approved target architecture.
- **Currently implemented**: operational and covered by tests.
- **Planned**: design-authorized but not implemented.
- **Deferred**: prohibited until a missing criterion, policy, or artifact is approved.

## Delivered baseline

1. Foundation and CI.
2. Domain model, authentication boundary, and secure upload.
3. Background-job orchestration and progress API.
4. Digital PDF and TP-153 extraction fixtures.
5. OCR/layout adapter integration.
6. KB validation, normalization, versioning, and retrieval.
7. Deterministic rules and exact scoring for the current supported set.
8. Governed semantic runtime for RULE002, RULE004, and RULE008.
9. Results UI and evidence drill-down.
10. Report generation and revised-exam history.
11. Training-project security, performance, deployment-readiness, and observability review.

## Approved hybrid redesign roadmap

The design-authorized evaluation order is:

`confirmed source evidence -> deterministic checks -> constrained semantic relationships -> deterministic aggregation and scoring`

### Version 1.1 - Governed foundation

- **M1 - Governance and Contract Freeze: currently implemented by the documentation/manifest
  milestone once its validation passes.** It authorizes the target design but does not implement
  runtime behavior.
- **M2 - Minimal persistence foundation: currently implemented.** Migration `0008` adds the
  immutable review-revision table, the nullable analysis confirmation pointer, and nullable
  categorical-confidence/evaluation-detail Finding fields. Strict internal snapshot and
  evaluation-detail contracts are implemented, but no revision is created and no runtime behavior
  changes until M3 or later.

### Version 1.2 - Extraction Review

- **M3 - Pipeline pause and initial snapshot: currently implemented.** New analyses create one
  immutable, source-faithful revision 1 and pause at `review_ready`.
- **M4 - Review and confirmation API: currently implemented.** Owner-authorized GET/PUT/confirm
  endpoints preserve immutable revisions, reject stale or fabricated source rows, bind the exact
  latest confirmed revision, materialize the reviewed transcription, and schedule only the guarded
  post-confirmation stages.
- **M5 - Minimal Extraction Review UI: currently implemented.** `review_ready` analyses route to a
  dedicated workspace with source anchors, warnings, correction/restoration/exclusion controls,
  immutable revision saves, exact-revision confirmation, and confirmed-state continuation.

No AI evaluator may run before the implemented confirmation boundary.

### Version 1.3 - Semantic alignment

- **M6 - Governed semantic output and categorical-confidence contract: planned.** It will migrate
  the currently implemented RULE002, RULE004, and RULE008 runtime away from numeric semantic
  confidence.
- **M7 - Semantic RULE001/RULE007 relationships and deterministic RULE005/RULE009 coverage:
  planned.**

### Version 1.4 - Complete governed semantic evaluation

- **M8 - RULE003 assessment consistency and RULE021 instructions: planned.**
- **M9 - RULE011, RULE012, and RULE013 question-writing semantics: planned.**
- **M10 - Reasoning, mapping, confidence, evidence, and report presentation: planned.**

### Version 1.5 - Acceptance release

- **M11 - Full integrated acceptance and release hardening: planned.**

The approved semantic/hybrid target set is RULE001, RULE002, RULE003, RULE004, RULE007, RULE008,
RULE011, RULE012, RULE013, and RULE021. Only RULE002, RULE004, and RULE008 are currently implemented
as RAG-backed semantic evaluators. Documentation must never use "approved semantic scope" as a
synonym for "currently implemented semantic runtime."

Deterministic final decisions or aggregation remain RULE005, governed branches of RULE006, RULE009,
RULE014, RULE016, RULE018, RULE019, and RULE022. RULE010 and RULE023-RULE030 remain unscored system
or governance gates.

RULE015, RULE017, RULE020, and the two-or-more-CLO branch of RULE006 remain deferred. No milestone
may invent criteria to remove these deferrals.

## Notes on delivered scope vs. this list
- Item 5 (OCR/layout adapter integration) is delivered: `PdfPlumberExamExtractor`
  (`backend/app/services/extraction/digital_pdf_extractor.py`) now falls back to OCR (local
  Tesseract, via `backend/app/services/extraction/ocr.py`) for any page with no extractable
  digital text. A cloud OCR vendor was deliberately not used - `docs/SECURITY_AND_PRIVACY.md`
  requires an undocumented privacy-policy decision before sending files to an external provider,
  and none exists.
- Item 6 is delivered: the controlled KB is validated, normalized, hashed, projected into reviewed
  embedding text, and indexed behind a provider-neutral vector-store interface. Chroma is the
  deployed adapter; a deterministic in-memory adapter supports tests and safe native development.
- The currently implemented semantic runtime includes `RULE002`, `RULE004`, and `RULE008`. Outputs
  are strict, versioned, evidence-linked, deterministically validated, and provenance-persisted.
  The broader design-authorized semantic set is planned above and is not yet operational.
  `RULE006` is unchanged: its zero/one-CLO deterministic branches remain supported and its
  undefined two-or-more-CLO branch produces no finding.
- Items 9 and 10 are delivered: results/evidence/recommendations UI, score display, PDF report
  generation/download, and linked reanalysis history are implemented.
- The original Item 11 review is delivered for the training-project baseline. Version 1.5 M11 is a
  separate integrated acceptance milestone for the hybrid redesign and does not authorize
  institutional production deployment.
