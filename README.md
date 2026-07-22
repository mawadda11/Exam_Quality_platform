# AI Exam Quality Platform

Repository scaffold for an evidence-based Midterm and Final exam quality-analysis platform for Faculty Members.

## Start with Claude Code
1. Upload this repository to GitHub.
2. Confirm the 11 approved knowledge-base `.xlsx` files are present in `knowledge_base/source/`.
3. Open the repository in VS Code.
4. Start Claude Code in the repository root.
5. Paste the contents of `CLAUDE_CODE_PROMPT.md`.
6. Ask Claude Code to inspect the repository and implement one milestone at a time.

Claude Code automatically reads `CLAUDE.md` in the repository root.

## Local development
```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

## Repository map
- `frontend/`: React/TypeScript application.
- `backend/`: FastAPI application and tests.
- `knowledge_base/`: approved Excel sources, manifest, and validation guidance.
- `docs/`: PRD, SRS, architecture, API, AI/RAG, database, security, and tests.
- `scripts/`: validation and developer utilities.
- `infrastructure/`: deployment-related configuration.

## Important
This scaffold is not a completed production system. It establishes the approved contracts, safe structure, starter services, and implementation instructions. Do not add real exam files or secrets to Git.
