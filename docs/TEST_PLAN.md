# Test Plan

## Unit tests
- Status enum and one-status invariant.
- Score values, exclusions, rounding, and zero denominator.
- Marks arithmetic and numbering rules.
- File validation and path safety.
- AI schema and evidence-link validation.
- Semantic rule/requirement/status/confidence/recommendation/provenance validation.
- Stable embedding IDs, version isolation, metadata filters, and index replacement.
- KB row and relationship validation.

## Integration tests
- Create analysis, upload synthetic fixtures, run the real local fake-provider pipeline, and query
  deterministic plus semantic results.
- PostgreSQL persistence and ownership filtering.
- Chroma adapter ingestion/retrieval with deterministic fixtures.
- Provider/retrieval/invalid-output failures use the processing-failure path and roll back findings.
- Report generation with traceable finding.
- Revised-exam analysis preserves predecessor.

## Contract tests
- OCR, AI provider, vector store, and file storage adapters.
- API request/response schemas.

## Security tests
- Unauthorized access and IDOR.
- Malicious filename and MIME mismatch.
- Oversized file.
- Prompt injection content does not override system constraints.
- Cross-analysis and wrong-source semantic evidence is rejected.
- Sensitive content absent from logs.

## Acceptance fixtures
Use synthetic exams and synthetic TP-153 files only. Include digital PDF, scanned PDF, missing CLO section, unresolved table reference, unreadable asset, incorrect total, duplicate numbering, and a zero-denominator case.
