# RAG and AI Design

## Contract status

This document distinguishes the approved target design from current runtime capability:

- **Design-authorized**: approved as the target Version 1 architecture.
- **Currently implemented**: operational and covered by tests.
- **Planned**: design-authorized but not yet operational.
- **Deferred**: prohibited until a missing criterion, policy, or artifact is approved.

Milestone M1 changes this design contract only. It does not implement Extraction Review,
categorical-confidence persistence, expanded evaluators, or new API/UI behavior.

## KB ingestion

1. Validate presence, names, columns, IDs, and relationships across all 11 workbooks.
2. Normalize rows into typed knowledge records.
3. Mark provenance category: official reference, official criterion, template evidence, derived
   requirement, system rule, or system policy.
4. Hash source files and records.
5. Build a version manifest.
6. Project only reviewed fields from references, standards, criteria, requirements, evidence
   types, and rules into embedding text. Recommendations remain exact-ID controlled data and are
   not embedded.
7. Assign deterministic IDs in the form `<kb-version>:<entity-type>:<official-id>`.
8. Store text and embeddings through a provider-independent vector-store interface, retaining the
   official ID, record hash, source workbook/row, provenance category, aggregate KB hash, and KB
   version.

Rebuilding an existing KB version deletes that version's records before upsert so stale records do
not survive. Other versions remain isolated. The native/test adapter is deterministic in-memory
token retrieval. The runtime adapter is ChromaDB, with both Python client and server pinned to
`1.5.9`.

## Retrieval

Construct queries from the minimum confirmed question and TP-153 evidence needed by the evaluator.
Every query names an explicit KB version and may filter by entity type, dimension, requirement ID,
and rule ID. Semantic evaluator queries are constrained by their controlled dimension and
requirement. Results return source IDs, reviewed text, record/source provenance, and KB version.

Exact-ID lookups remain authoritative for rule definitions, allowed statuses, requirement metadata,
and recommendation applicability. Similarity retrieval never overrides those governance records.

## Evaluation architecture

The design-authorized Version 1 order is:

`confirmed source evidence -> deterministic checks -> constrained semantic relationships -> deterministic aggregation and scoring`

### Design-authorized semantic and hybrid-semantic rules

- `RULE001` / `REQ001` - Question-to-CLO Mapping.
- `RULE002` / `REQ002` - CLO Relevance.
- `RULE003` / `REQ003` - Assessment Method Consistency.
- `RULE004` / `REQ004` - Question Format Suitability.
- `RULE007` / `REQ007` - Question-to-Topic Alignment.
- `RULE008` / `REQ008` - Out-of-Scope Content.
- `RULE011` / `REQ011` - Clear Task Statement.
- `RULE012` / `REQ012` - Unambiguous Wording.
- `RULE013` / `REQ013` - Complete Question Information.
- `RULE021` / `REQ021` - Complete Instructions.

The currently implemented RAG-backed semantic runtime remains limited to `RULE002`, `RULE004`, and
`RULE008`. The other design-authorized semantic behaviors are planned and must not be reported as
operational until their later milestones and tests are complete. `RULE001` and `RULE007` currently
have deterministic exact-citation behavior; their AI-derived mapping behavior is planned.

### Deterministic final decisions and aggregation

- `RULE005` - Applicable CLO Coverage.
- `RULE006` - CLO Coverage Distribution for the governed zero- and one-CLO branches only.
- `RULE009` - Applicable Topic Coverage.
- `RULE014` - Referenced Material Availability.
- `RULE016` - Supporting Material Association.
- `RULE018` - Correct Total Marks.
- `RULE019` - Consistent Numbering.
- `RULE022` - Resolvable Cross-References.

Semantic AI may establish validated relationships. Deterministic logic calculates coverage, marks
totals, numbering outcomes, and score aggregation. A Low or Not Verified mapping cannot contribute
to coverage. Confidence never changes the approved score value of a verified academic status.

### System and governance gates

`RULE010` and `RULE023` through `RULE030` validate inputs or released platform outputs. They do not
create additional scored exam-facing Findings.

### Retained deferrals

- `RULE015` - no approved supporting-material legibility threshold or governed vision evaluator.
- `RULE017` - no approved institutional visible-marks applicability policy.
- `RULE020` - no approved required/essential exam-identification field set.
- `RULE006` with two or more applicable CLOs - no approved concentration criterion.

AI must not invent criteria that remove these deferrals. An unavailable evaluator is not
represented by an unconditional Not Verified Finding.

## Semantic evaluation contract

No semantic evaluator may run before the planned Extraction Review is confirmed. Each independent
evaluator receives only compatible confirmed Exam/TP-153 evidence, filtered KB records, and a
versioned prompt with a strict output schema. It must choose exactly one KB-approved status, cite
evidence IDs, provide a concise evidence-to-rule explanation, and select an applicable controlled
recommendation ID or no recommendation. Recommendation text displayed to faculty always comes from
the KB.

An explicit source mapping and an AI-derived relationship remain separate:

- a derived relationship is not official source evidence;
- question and target identifiers must already exist in the confirmed extraction;
- the output is labeled `AI-assisted` or `derived`;
- evidence and concise reasoning are mandatory; and
- source evidence is never overwritten.

The future semantic finding contract exposes Decision, Evidence Used, Concise Reasoning,
categorical Confidence, and an optional controlled Recommendation. Reasoning is not private model
chain-of-thought; private chain-of-thought must not be requested, stored, or displayed.

## Categorical semantic confidence

The design-authorized semantic confidence values are:

- **High**: confirmed, source-anchored, unambiguous evidence with direct textual or deterministic
  support and no material conflict.
- **Medium**: confirmed, traceable, non-conflicting evidence where semantic interpretation is
  necessary.
- **Low**: missing, unreadable, incomplete, conflicting, unconfirmed, or unvalidated evidence.

The backend, not the model, is authoritative for confidence. Low confidence requires Not Verified
and exclusion from the score denominator. Confidence is not a percentage, severity, priority,
quality score, readiness label, or scoring weight. Numeric OCR and extraction confidence remain
separate technical metadata and are never converted into semantic confidence.

The current semantic provider schema still uses numeric confidence. Replacing that runtime contract
and the frontend percentage display is planned for later milestones; M1 does not silently change
runtime behavior.

`RULE006` remains the existing partial deterministic evaluator: zero and one applicable CLO
branches are supported, while two-or-more CLOs produce no `RULE006` finding because the KB defines
no concentration threshold. It is not a semantic evaluator.

`AI_PROVIDER=fake` is the safe local/test default and performs no network calls. The provider
factory also supports the Anthropic adapter for optional manual use. Evaluators depend only on the
provider interface; no evaluator contains vendor-specific code.

## Validation gates

- JSON/schema validation with exactly one output object and no unknown fields.
- Approved rule, requirement, and academic-status validation.
- Categorical-confidence evidence conditions and duplicate-evidence rejection in the planned
  contract. Current numeric validation remains implemented until its planned replacement.
- Evidence ID existence, analysis ownership, evaluator compatibility, and source-document checks.
- Question/CLO/topic evidence must match a confirmed domain row from the same analysis once
  Extraction Review is implemented.
- Derived mapping target IDs must be drawn from server-provided confirmed candidates.
- Low semantic confidence must be paired with Not Verified.
- Recommendation applicability validation.
- Provider/model, prompt-template version, and KB-version provenance validation.
- Duplicate finding protection by `(analysis_id, rule_id)`.

Missing required academic evidence or empty relevant retrieval produces a traceable `Not Verified`
finding for an implemented evaluator. Provider, Chroma, configuration, malformed-output-after-
bounded-retry, and persistence failures propagate through the existing safe processing-failure
path; infrastructure failures never become academic statuses.

The model never creates questions, CLOs, topics, assessment records, institutional policies, rule
thresholds, source pages, marks, or official mappings. Uploaded text and retrieved KB text are
treated as untrusted data, not instructions.

## Chroma endpoints

- Native backend: `CHROMA_HOST=localhost`, `CHROMA_PORT=8001`.
- Docker Compose backend: `CHROMA_HOST=chromadb`, `CHROMA_PORT=8000`.
- Tests/native safe default: `VECTOR_STORE_PROVIDER=memory`.
- Docker Compose override: `VECTOR_STORE_PROVIDER=chroma`.
