# CLAUDE.md — AI Exam Quality Platform

## Mission
Build and maintain an evidence-based platform that analyzes Midterm and Final exam PDFs for computing courses against a populated TP-153 Course Specification and the versioned Exam Quality Knowledge Base.

## Non-negotiable product boundaries
- Supported assessments: Midterm and Final exams only.
- Supported domain: computing courses.
- Inputs: exam PDF and populated TP-153.
- No student-answer analysis, grade analysis, difficulty estimation, Bloom classification, faculty evaluation, or accreditation decision.
- No formal Approve/Reject workflow.
- Do not modify uploaded exams or TP-153.
- Do not present derived project rules as official quotations.

## Required behavior
1. Always show a concise implementation plan before coding.
2. Inspect existing code, tests, docs, and migrations before changing behavior.
3. Make the smallest coherent change that completes the task.
4. Write or update tests for every feature and bug fix.
5. Run relevant checks before declaring completion.
6. Explain changed files, validation performed, and known limitations.
7. Never commit secrets, API keys, tokens, private exam content, or real personal data.
8. Never silently weaken evidence, traceability, security, validation, or governance rules.

## Academic-status contract
Every executed academic evaluation rule returns exactly one of:
- `Satisfied`
- `Partially Satisfied`
- `Not Satisfied`
- `Not Verified`
- `Not Applicable`

Never add severity, priority, Critical/High/Medium/Low, rule weights, dimension weights, readiness bands, or qualitative score labels.

Processing failures are not academic statuses. Use separate processing states/errors.

## Scoring contract
- Satisfied = 1.0
- Partially Satisfied = 0.5
- Not Satisfied = 0.0
- Exclude Not Verified and Not Applicable.
- If no verified applicable rules exist, return `Insufficient Evidence`, not a numeric score.

## Evidence and AI governance
- Never generate a released finding without evidence.
- Never invent CLOs, topics, marks, questions, citations, pages, or knowledge-base records.
- Use `Not Verified` when evidence is missing, unreadable, unreliable, or insufficient.
- Store source document, page, question/item, evidence identifier, requirement ID, and rule ID where applicable.
- Require structured model output and validate it with typed schemas before persistence.
- Treat model output as untrusted input.
- Keep deterministic calculations deterministic.
- Limit conclusions to the uploaded exam and TP-153.
- Recommendations are academic support, not institutional decisions.

## Architecture rules
- Frontend: React + TypeScript.
- Backend: Python + FastAPI.
- Relational database: PostgreSQL.
- Vector database: ChromaDB behind an interface.
- Background processing: worker/job abstraction; long analysis must not block HTTP requests.
- Keep frontend, API, extraction, AI/RAG, rules, reporting, and storage concerns separated.
- Keep the knowledge base outside application source code and version it.
- Use dependency injection and interfaces at external-service boundaries.
- Do not call AI providers directly from route handlers.

## Coding conventions
### Python
- Python 3.12+.
- Type hints for public functions.
- Pydantic v2 schemas at API and AI boundaries.
- SQLAlchemy 2.x style.
- Ruff for lint/format; mypy for type checking; pytest for tests.
- Prefer small pure functions for scoring and deterministic rules.
- Use explicit domain enums; do not rely on free-form status strings.

### TypeScript
- Strict TypeScript.
- Functional React components.
- Keep server state in query/service layers, not duplicated across components.
- Validate external payloads at boundaries.
- Vitest + React Testing Library for tests.
- ESLint and Prettier must pass.

## Security and privacy
- Validate extension, MIME type, file signature, size, and PDF readability.
- Generate server-side storage names; never trust uploaded paths.
- Prevent path traversal and unauthorized file access.
- Do not log full exam content, full TP-153 content, credentials, or sensitive prompts.
- Store only necessary metadata in logs.
- Enforce ownership checks on analyses, files, findings, and reports.
- Use environment variables for secrets and provide placeholders only in `.env.example`.
- Define and honor retention/deletion policy hooks.

## Files and areas that must not be changed casually
- `knowledge_base/source/`: official/source KB files; never alter rows unless the task explicitly requests a reviewed KB update.
- `knowledge_base/manifest.json`: update only through the KB validation/versioning workflow.
- Database migrations already deployed: never rewrite; create a new migration.
- Governance and scoring rules in `docs/AI_GOVERNANCE.md` and `docs/SCORING_POLICY.md`: changes require explicit task scope and corresponding tests.
- `.github/workflows/`: do not remove security/test gates to make CI pass.
- User uploads and generated reports: never commit them.

## Definition of done
A task is complete only when:
- Behavior matches the project scope and governance rules.
- Tests cover success, failure, and insufficient-evidence cases where relevant.
- Relevant lint/type/test commands pass, or failures are reported precisely.
- API/schema/documentation changes are synchronized.
- No secret or private document is added.
- The final response names modified files and verification performed.

## Standard commands
```bash
# Entire local stack
cp .env.example .env
docker compose up --build

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e '.[dev]'
ruff check .
ruff format --check .
mypy app
pytest

# Frontend
cd frontend
npm ci
npm run lint
npm run typecheck
npm test -- --run
npm run build

# Knowledge base
python scripts/validate_knowledge_base.py
```
