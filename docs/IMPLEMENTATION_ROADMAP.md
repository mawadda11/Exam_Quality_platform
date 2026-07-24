# Implementation Roadmap

1. Foundation and CI.
2. Domain model, authentication boundary, and secure upload.
3. Background-job orchestration and progress API.
4. Digital PDF and TP-153 extraction fixtures.
5. OCR/layout adapter integration.
6. KB validation, normalization, versioning, and retrieval.
7. Deterministic rules and exact scoring.
8. Semantic evaluators and governance validation.
9. Results UI and evidence drill-down.
10. Report generation and revised-exam history.
11. Security hardening, performance tests, observability, and deployment.

## Notes on delivered scope vs. this list
- Item 5 (OCR/layout adapter integration) is delivered: `PdfPlumberExamExtractor`
  (`backend/app/services/extraction/digital_pdf_extractor.py`) now falls back to OCR (local
  Tesseract, via `backend/app/services/extraction/ocr.py`) for any page with no extractable
  digital text. A cloud OCR vendor was deliberately not used - `docs/SECURITY_AND_PRIVACY.md`
  requires an undocumented privacy-policy decision before sending files to an external provider,
  and none exists. Item 8's semantic-evaluator half remains deferred - see below.
- Item 8's semantic-evaluator half is intentionally deferred, not forgotten: no semantic-AI
  capability has been built yet. Deterministic rules that would require one are marked
  `unsupported` in `backend/app/services/rules/capability_manifest.py` and produce no Finding,
  rather than being skipped without a trace. This also depends on item 6's runtime KB retrieval
  (below), which remains unbuilt.
- Item 6's runtime KB retrieval (similarity-based retrieval feeding semantic evaluators) also
  remains unimplemented - `run_retrieving_knowledge` is still a no-op placeholder. Only offline KB
  validation/normalization/versioning has been built. M9's read-time KB reference lookups
  (`backend/app/services/knowledge_base/reference_data.py`) are a separate, narrower, exact-ID
  lookup for display purposes only, not this retrieval capability.
- Item 9 (this milestone) covers the Results UI and evidence drill-down for already-persisted
  Findings/Questions/CLOs/Topics, plus read-time (not persisted) overall-score display and KB
  recommendation lookup. Persistence of a score/recommendation snapshot, PDF report rendering, and
  reanalysis history remain item 10.
