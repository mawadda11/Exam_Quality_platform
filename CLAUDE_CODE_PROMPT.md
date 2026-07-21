# Claude Code Master Implementation Prompt

You are the principal software engineer, AI systems engineer, and technical documentation owner for the **AI Exam Quality Platform** repository.

Read these files before making changes:
1. `CLAUDE.md`
2. `PROJECT_SPEC.md`
3. `docs/PRD.md`
4. `docs/SRS.md`
5. `docs/ARCHITECTURE.md`
6. `docs/AI_GOVERNANCE.md`
7. `docs/SCORING_POLICY.md`
8. `docs/DATABASE_SCHEMA.md`
9. `docs/API_SPECIFICATION.md`
10. `docs/RAG_AND_AI_DESIGN.md`
11. `docs/SECURITY_AND_PRIVACY.md`
12. `docs/TEST_PLAN.md`
13. `knowledge_base/README.md`

## Working protocol
Before coding:
- Summarize your understanding of the requested task.
- Inspect relevant files and identify dependencies.
- Present a concise, ordered plan.
- State assumptions only when unavoidable; prefer repository evidence.

During implementation:
- Work in small, reviewable increments.
- Preserve existing behavior unless the task changes it.
- Add typed models and validation at boundaries.
- Add tests with every feature or correction.
- Never invent official accreditation text or academic evidence.
- Never bypass failing tests, weaken validation, or remove security controls.

After implementation:
- Run the smallest relevant checks and then broader checks when practical.
- Report exactly what changed, tests run, results, and unresolved limitations.
- Do not claim a command passed unless it was executed successfully.

## Product to build
Create a secure web platform for faculty members, course coordinators, and quality officers to upload:
- one Midterm or Final exam PDF; and
- the corresponding populated TP-153 Course Specification.

The platform must extract and analyze exam questions, sub-questions, marks, instructions, tables, images, diagrams, code snippets, numbering, structure, and source locations. It must extract CLOs, topics, assessment methods, activities, hours, and percentages from TP-153 where available.

It must produce evidence-based analysis for:
- CLO alignment and applicable coverage;
- topic alignment and applicable coverage;
- assessment-method consistency;
- question clarity and completeness;
- marks and total validation;
- numbering and structure;
- supporting-material presence, legibility, linkage, and cross-references;
- traceability;
- actionable recommendations;
- an overall score based only on verified applicable rules.

## Required technology baseline
- React + TypeScript frontend.
- FastAPI + Python backend.
- PostgreSQL relational database.
- ChromaDB through a replaceable vector-store interface.
- Background analysis jobs so HTTP requests remain responsive.
- Docker Compose for local development.
- GitHub Actions for CI.

## First implementation sequence
Unless the repository already contains a later completed stage, implement in this order:

### Phase 1 — Foundation
- Confirm repository structure and configuration.
- Implement health endpoints.
- Configure typed settings and safe environment loading.
- Configure database session and initial models/migrations.
- Add CI lint, type, test, and build checks.

### Phase 2 — Core domain and upload safety
- Add domain enums for user type, exam type, processing state, and academic status.
- Implement analysis, uploaded-file, course, and exam records.
- Implement authenticated ownership boundaries or a clearly documented local-development identity adapter.
- Validate PDF file extension, MIME type, magic bytes, size, filename, and readability.
- Store files using generated IDs and hashes.

### Phase 3 — Asynchronous processing pipeline
- Create analysis-job stages:
  `queued -> validating -> extracting_exam -> extracting_tp153 -> building_evidence -> retrieving_knowledge -> applying_rules -> generating_report -> completed`.
- Keep failures in separate processing error fields.
- Expose progress safely through API polling.

### Phase 4 — Extraction adapters
- Implement interfaces for digital PDF extraction, OCR, layout/vision analysis, and TP-153 extraction.
- Persist page-aware structured output.
- Preserve confidence and bounding boxes when available.
- Build deterministic fixture-based tests before integrating paid/external providers.

### Phase 5 — Knowledge base and RAG
- Validate all 11 Excel source files and required columns.
- Convert rows to normalized knowledge records.
- Version the KB using a manifest and hashes.
- Create embeddings only for suitable text fields.
- Apply metadata filters by entity type/dimension.
- Return source IDs with every retrieved record.

### Phase 6 — Rules and scoring
- Implement deterministic rules first.
- Add AI semantic evaluators behind typed interfaces.
- Require exactly one valid academic status per executed rule.
- Validate evidence references and rule/requirement identifiers.
- Implement the exact scoring policy and insufficient-evidence behavior.

### Phase 7 — Results and reports
- Implement dashboard, question detail, CLO/topic views, missing evidence, and recommendations.
- Generate a downloadable report with scope disclaimer and traceable findings.
- Add revised-exam reanalysis linked to the prior analysis without overwriting history.

## Mandatory domain invariants
1. A released finding has at least one valid evidence link unless its rule explicitly represents missing evidence and links to the trace showing the missing/unresolved reference.
2. Each executed rule has exactly one status.
3. Status is one of the five approved values only.
4. `Not Verified` and `Not Applicable` never enter the score denominator.
5. A numeric score is absent when the denominator is zero.
6. AI output is schema-validated before persistence.
7. CLOs and topics originate from the uploaded TP-153; they are never invented.
8. Every stored source page uses a clear indexing convention documented in the API.
9. Reanalysis creates a new immutable analysis version linked to its predecessor.
10. Official-source wording and derived system rules remain distinguishable.

## Explicit exclusions
Do not implement assignments, projects, labs, quizzes, Blackboard assessments, student answers, grades, distributions, difficulty estimation, Bloom taxonomy, student-performance prediction, faculty evaluation, teaching evaluation, facilities evaluation, program management evaluation, full accreditation evaluation, automatic document modification, or approval/rejection workflow.

## Initial task
Inspect the current repository against the project documents. Produce:
1. a gap analysis grouped by critical, required, and optional work;
2. a proposed implementation plan with milestones;
3. the smallest useful first coding increment;
4. tests for that increment;
5. updated documentation only where the implementation changes an agreed contract.

Do not attempt to implement the entire platform in one uncontrolled change.
