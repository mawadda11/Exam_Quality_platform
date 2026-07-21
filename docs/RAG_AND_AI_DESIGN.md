# RAG and AI Design

## KB ingestion
1. Validate presence, names, columns, IDs, and relationships across all 11 workbooks.
2. Normalize rows into typed knowledge records.
3. Mark provenance category: official reference, official criterion, template evidence, derived requirement, system rule, or system policy.
4. Hash source files and records.
5. Build a version manifest.
6. Embed only retrieval-relevant text and retain metadata IDs.
7. Store embeddings through a vector-store interface.

## Retrieval
Construct queries from question text, nearby instructions/assets, target dimension, and available TP-153 records. Filter by entity type and dimension. Return source IDs, text, provenance, and KB version.

## Semantic evaluation
The model receives only the minimum relevant question context, TP-153 evidence, retrieved KB records, and a strict output schema. It must choose exactly one approved status, cite evidence IDs, explain the relationship, and select a known recommendation or provide no recommendation when prohibited.

## Validation gates
- JSON/schema validation.
- Approved enum validation.
- Requirement/rule existence.
- Evidence ID existence and ownership.
- CLO/topic IDs originate from the same analysis.
- Recommendation policy validation.
- Unsupported or conflicting output is rejected or converted to a controlled retry/failure, not silently stored.
