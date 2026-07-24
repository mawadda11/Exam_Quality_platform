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
  and none exists.
- Item 6 is delivered: the controlled KB is validated, normalized, hashed, projected into reviewed
  embedding text, and indexed behind a provider-neutral vector-store interface. Chroma is the
  deployed adapter; a deterministic in-memory adapter supports tests and safe native development.
- Item 8 is delivered for the explicitly approved semantic scope: `RULE002`, `RULE004`, and
  `RULE008`. Outputs are strict, versioned, evidence-linked, deterministically validated, and
  provenance-persisted. `RULE006` is unchanged: its zero/one-CLO deterministic branches remain
  supported and its undefined two-or-more-CLO branch produces no finding.
- Items 9 and 10 are delivered: results/evidence/recommendations UI, score display, PDF report
  generation/download, and linked reanalysis history are implemented.
- Item 11 remains the final roadmap area. Existing security, performance, deployment-readiness,
  and observability work should continue under that scope.
