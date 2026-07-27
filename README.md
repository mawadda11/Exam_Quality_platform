# AI Exam Quality Platform

Evidence-based Midterm and Final exam quality-analysis platform for Faculty Members. Deterministic aggregation and ten governed advisory semantic/hybrid evaluators produce traceable
findings; the faculty member retains final academic responsibility.

## Start with Claude Code
1. Upload this repository to GitHub.
2. Confirm the 11 approved knowledge-base `.xlsx` files are present in `knowledge_base/source/`.
3. Open the repository in VS Code.
4. Start Claude Code in the repository root.
5. Paste the contents of `CLAUDE_CODE_PROMPT.md`.
6. Ask Claude Code to inspect the repository and implement one milestone at a time.

Claude Code automatically reads `CLAUDE.md` in the repository root.

## Current implementation status

M1-M9 are committed through base commit `5f76d6a`. The current working-tree delivery completes:

- **M10:** categorical-confidence, semantic reasoning, derived mapping, evidence, score-denominator,
  runtime rule-coverage, and PDF-report presentation; and
- **M11:** a synthetic, offline, API-level acceptance test for the complete supported upload ->
  extraction review -> confirmation -> governed evaluation -> score/coverage -> report workflow.

Read `docs/M10_M11_HANDOFF.md`, `docs/M10_M11_IMPLEMENTATION_REPORT.md`, and
`docs/M10_M11_VERIFICATION.md` before editing or committing. The final local frontend/Ruff/mypy
checks documented there remain mandatory where package registries are available.

## Local development

With Docker (entire stack - frontend, backend, PostgreSQL, ChromaDB):
```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

Without Docker (native backend dev server): PostgreSQL must still run somewhere reachable at
`localhost:5432` (via `docker compose up -d postgres`, or a native install) - see "Running
PostgreSQL locally" and the backend commands in `CLAUDE.md`.

Native development uses the deterministic in-memory vector store and fake AI provider by default,
so tests and local runs never make external AI calls. Docker Compose selects ChromaDB at
`chromadb:8000`; its host-published native-development endpoint is `localhost:8001`. To perform an
optional manual Anthropic run, set `AI_PROVIDER=anthropic`, an approved exact `AI_MODEL`, and
`AI_API_KEY`. Do this only where the privacy policy permits sending the minimized evidence context.
See [RAG and AI Design](docs/RAG_AND_AI_DESIGN.md) for the provider, validation, and failure policy.

## Repository map
- `frontend/`: React/TypeScript application.
- `backend/`: FastAPI application and tests.
- `knowledge_base/`: approved Excel sources, manifest, and validation guidance.
- `docs/`: PRD, SRS, architecture, API, AI/RAG, database, security, and tests.
- `scripts/`: validation and developer utilities.
- `infrastructure/`: deployment-related configuration.

## Important
This remains a development system, not a production accreditation or approval platform. Do not add
real exam files or secrets to Git.
