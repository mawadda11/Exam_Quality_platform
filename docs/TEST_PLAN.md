# Test Plan

## Unit tests
- Status enum and one-status invariant.
- Score values, exclusions, rounding, and zero denominator.
- Marks arithmetic and numbering rules.
- File validation and path safety.
- AI schema and evidence-link validation.
- KB row and relationship validation.

## Integration tests
- Create analysis, upload fixtures, run stub pipeline, query results.
- PostgreSQL persistence and ownership filtering.
- Chroma adapter ingestion/retrieval with deterministic fixtures.
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
- Sensitive content absent from logs.

## Acceptance fixtures
Use synthetic exams and synthetic TP-153 files only. Include digital PDF, scanned PDF, missing CLO section, unresolved table reference, unreadable asset, incorrect total, duplicate numbering, and a zero-denominator case.
