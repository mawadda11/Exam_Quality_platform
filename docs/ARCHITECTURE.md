# Architecture

## Context
A browser client submits analysis metadata and two files to a FastAPI API. The API persists metadata, secures file storage, and enqueues a staged background analysis. Extraction adapters produce structured records. Deterministic rules and semantic AI evaluators consume evidence plus filtered KB records. Validated findings are stored and rendered into a report.

## Components
- React frontend: upload, progress, results, evidence drill-down, history, report download.
- FastAPI API: authentication boundary, validation, orchestration endpoints, result queries.
- Worker: staged processing and retry-safe state transitions.
- PostgreSQL: transactional domain and traceability data.
- ChromaDB: replaceable vector retrieval implementation.
- Object/file storage abstraction: uploads, extracted assets, reports.
- AI provider adapter: structured semantic evaluation.
- OCR/layout adapters: provider-neutral extraction interfaces.

## Processing flow
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

## Key design decisions
- Immutable analysis versions.
- Domain enums shared through generated/documented API contracts.
- AI output validated before persistence.
- Page-aware evidence and explicit source IDs.
- Deterministic score and arithmetic checks.
- KB files mounted read-only in runtime environments.
- External providers hidden behind interfaces for testing and replacement.
