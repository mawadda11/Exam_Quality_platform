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
- Implemented: extraction pauses before evidence gates, KB retrieval, or AI, creates revision 1
  idempotently, and makes no Finding.
- Implemented: confirmation binds the exact latest review revision before post-confirmation
  processing and ignores duplicate/mismatched continuation tasks.
- Implemented: review correction/restoration/exclusion preserves source-record identity and
  immutable anchors, rejects stale or fabricated rows, and closes writes after confirmation.
- Implemented: Low or Not Verified semantic mappings do not contribute positive deterministic
  coverage; complete negative mappings produce Not Satisfied rather than default Not Verified.
- Implemented: all 21 exam-facing rules are accounted for by the runtime coverage audit and a
  supported rule that fails to run is exposed as an operational gap.

## Contract tests
- OCR, AI provider, vector store, and file storage adapters.
- API request/response schemas.
- Governance manifest classifications, system gates, and retained deferrals.
- Implemented M2 contracts: strict source-faithful review snapshot shape, empty collection
  behavior, internal reference validation, immutable revision metadata, and the versioned
  `decision`/`evidence_used`/`reasoning`/`recommendation` evaluation-details core.
- Implemented categorical semantic-output runtime schemas, item-level relationship contracts, and
  rule-coverage response contract.

## Security tests
- Unauthorized access and IDOR.
- Malicious filename and MIME mismatch.
- Oversized file.
- Prompt injection content does not override system constraints.
- Cross-analysis and wrong-source semantic evidence is rejected.
- Unknown derived target IDs and AI-generated source records are rejected.
- Manual CLO/topic/assessment-record/mapping creation is rejected by the implemented review boundary.
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

Automated schema/failure tests use the fake provider. M6-M9 integration tests use the offline local
baseline to prove complete governed execution without network I/O. Neither provider proves
institutional academic validity; production semantic validity requires an approved provider/model
and external academic validation.
