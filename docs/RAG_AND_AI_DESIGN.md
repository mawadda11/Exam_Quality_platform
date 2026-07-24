# RAG and AI Design

## KB ingestion
1. Validate presence, names, columns, IDs, and relationships across all 11 workbooks.
2. Normalize rows into typed knowledge records.
3. Mark provenance category: official reference, official criterion, template evidence, derived requirement, system rule, or system policy.
4. Hash source files and records.
5. Build a version manifest.
6. Project only reviewed fields from references, standards, criteria, requirements, evidence types,
   and rules into embedding text. Recommendations remain exact-ID controlled data and are not
   embedded.
7. Assign deterministic IDs in the form `<kb-version>:<entity-type>:<official-id>`.
8. Store text and embeddings through a provider-independent vector-store interface, retaining the
   official ID, record hash, source workbook/row, provenance category, aggregate KB hash, and KB
   version.

Rebuilding an existing KB version deletes that version's records before upsert so stale records do
not survive. Other versions remain isolated. The native/test adapter is deterministic in-memory
token retrieval. The runtime adapter is ChromaDB, with both Python client and server pinned to
`1.5.9`.

## Retrieval
Construct queries from the minimum question and TP-153 evidence needed by the evaluator. Every
query names an explicit KB version and may filter by entity type, dimension, requirement ID, and
rule ID. Semantic evaluator queries are constrained by their controlled dimension and requirement.
Results return source IDs, reviewed text, record/source provenance, and KB version.

Exact-ID lookups remain authoritative for rule definitions, allowed statuses, requirement metadata,
and recommendation applicability. Similarity retrieval never overrides those governance records.

## Semantic evaluation
The approved semantic scope is exactly:

- `RULE002` / `REQ002` — CLO Relevance.
- `RULE004` / `REQ004` — Question Format Suitability.
- `RULE008` / `REQ008` — Out-of-Scope Content.

Each independent evaluator receives only compatible question/TP-153 evidence, filtered KB records,
and a versioned prompt with a strict output schema. It must choose exactly one KB-approved status,
cite evidence IDs, explain the relationship, and select an applicable controlled recommendation ID
or no recommendation. Recommendation text displayed to faculty always comes from the KB.

`RULE006` remains the existing partial deterministic evaluator: zero and one applicable CLO
branches are supported, while two-or-more CLOs produce no `RULE006` finding because the KB defines
no concentration threshold. It is not a semantic evaluator.

`AI_PROVIDER=fake` is the safe local/test default and performs no network calls. The provider factory
also supports the Anthropic adapter for optional manual use. Evaluators depend only on the provider
interface; no evaluator contains vendor-specific code.

## Validation gates
- JSON/schema validation with exactly one output object and no unknown fields.
- Approved rule, requirement, and academic-status validation.
- Confidence bounds and duplicate-evidence rejection.
- Evidence ID existence, analysis ownership, evaluator compatibility, and source-document checks.
- Question/CLO/topic evidence must match an extracted domain row from the same analysis.
- Recommendation applicability validation.
- Provider/model, prompt-template version, and KB-version provenance validation.
- Duplicate finding protection by `(analysis_id, rule_id)`.

Missing required academic evidence or empty relevant retrieval produces a traceable `Not Verified`
finding. Provider, Chroma, configuration, malformed-output-after-bounded-retry, and persistence
failures propagate through the existing safe processing-failure path; infrastructure failures never
become academic statuses.

## Chroma endpoints

- Native backend: `CHROMA_HOST=localhost`, `CHROMA_PORT=8001`.
- Docker Compose backend: `CHROMA_HOST=chromadb`, `CHROMA_PORT=8000`.
- Tests/native safe default: `VECTOR_STORE_PROVIDER=memory`.
- Docker Compose override: `VECTOR_STORE_PROVIDER=chroma`.
