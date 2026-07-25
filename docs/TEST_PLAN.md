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
- Design-authorized versus currently implemented versus planned versus deferred capability
  classification.
- Categorical semantic confidence conditions and Low-to-Not-Verified enforcement.
- Confidence has no score-weight effect and numeric extraction/OCR confidence remains separate.
- Derived relationships reference confirmed allowlisted source identifiers.
- Concise reasoning contains evidence-to-rule justification without private chain-of-thought.

## Integration tests
- Create analysis, upload synthetic fixtures, run the real local fake-provider pipeline, and query
  deterministic plus semantic results.
- PostgreSQL persistence and ownership filtering.
- Chroma adapter ingestion/retrieval with deterministic fixtures.
- Provider/retrieval/invalid-output failures use the processing-failure path and roll back findings.
- Report generation with traceable finding.
- Revised-exam analysis preserves predecessor.
- Planned: extraction pauses before KB retrieval or AI, creates revision 1, and makes no Finding.
- Planned: confirmation binds an exact review revision before post-confirmation processing.
- Planned: review correction/restoration/exclusion remains source-faithful and atomic.
- Planned: a Low or Not Verified semantic mapping does not contribute to deterministic coverage.

## Contract tests
- OCR, AI provider, vector store, and file storage adapters.
- API request/response schemas.
- Governance manifest classifications, system gates, and retained deferrals.
- Planned review snapshot and categorical semantic-output schemas.

## Security tests
- Unauthorized access and IDOR.
- Malicious filename and MIME mismatch.
- Oversized file.
- Prompt injection content does not override system constraints.
- Cross-analysis and wrong-source semantic evidence is rejected.
- Unknown derived target IDs and AI-generated source records are rejected.
- Manual CLO/topic/assessment-record/mapping creation is rejected by the planned review boundary.
- AI providers are not invoked before extraction confirmation.
- Sensitive content absent from logs.

## Acceptance fixtures
Use synthetic exams and synthetic TP-153 files only. Include digital PDF, scanned PDF, missing CLO section, unresolved table reference, unreadable asset, incorrect total, duplicate numbering, and a zero-denominator case.

Add governed semantic cases for:

- explicit and derived CLO/topic relationships;
- complete and incomplete candidate sets;
- exact assessment-method match and bounded wording equivalence;
- clear task, material ambiguity, missing explicit dependency, and complete instructions;
- every categorical confidence level;
- Low confidence producing Not Verified;
- retained RULE015, RULE017, RULE020, and RULE006 two-or-more-CLO deferrals; and
- decision-support disclaimers that prohibit accreditation and attainment claims.

Automated tests use the fake provider by default. Passing fake-provider tests proves orchestration,
schema, validation, and reproducibility; it does not by itself prove academic semantic validity.
