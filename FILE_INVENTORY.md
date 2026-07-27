# Package Inventory

## Coding-agent continuity

- `CLAUDE.md`
- `CLAUDE_CODE_PROMPT.md`
- `docs/M10_M11_HANDOFF.md`
- `docs/M10_M11_IMPLEMENTATION_PLAN.md`
- `docs/M10_M11_IMPLEMENTATION_REPORT.md`
- `docs/M10_M11_VERIFICATION.md`
- `docs/OWNER_FINAL_CHECKLIST.md`
- `docs/RELEASE_V1.md`
- `docs/V2_ROADMAP.md`
- `VERSION`
- Earlier milestone reports under `docs/` remain part of the audit trail.

## Product and technical documentation

- `PROJECT_SPEC.md`
- `docs/PRD.md`
- `docs/SRS.md`
- `docs/ARCHITECTURE.md`
- `docs/DATABASE_SCHEMA.md`
- `docs/API_SPECIFICATION.md`
- `docs/RAG_AND_AI_DESIGN.md`
- `docs/AI_GOVERNANCE.md`
- `docs/SCORING_POLICY.md`
- `docs/SECURITY_AND_PRIVACY.md`
- `docs/TEST_PLAN.md`
- `docs/IMPLEMENTATION_ROADMAP.md`
- `docs/V1_TRACEABILITY_MATRIX.md`
- `docs/FRONTEND_DESIGN_SYSTEM.md`

## Implemented application

- React/TypeScript frontend with upload, processing, extraction review, history, results,
  evidence, recommendations, concise analysis-completion messaging, a separate **What the Platform Evaluates**
  page, and reports.
- Python/FastAPI backend with owner-scoped analysis APIs, secure PDF upload, extraction review,
  governed deterministic/semantic evaluation, scoring, coverage audit, and PDF reporting.
- PostgreSQL application persistence, ChromaDB adapter, offline deterministic development vector
  store, and offline local/fake AI adapters for tests and safe development.
- Docker Compose and GitHub Actions gates.
- Backend unit, integration, security, report, and complete synthetic M10-M11 acceptance tests.

## Knowledge base

- Eleven approved Excel workbooks in `knowledge_base/source/`.
- `knowledge_base/manifest.json` with file and record hashes.
- Validation/normalization script in `scripts/validate_knowledge_base.py`.
- Generated/vector artifacts remain excluded from Git.

## Excluded private/generated content

- `.env` and credentials.
- Real exam or TP-153 uploads.
- Generated reports and extraction artifacts.
- `node_modules`, virtual environments, caches, coverage, and build output.
