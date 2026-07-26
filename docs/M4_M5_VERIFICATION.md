# M4-M5 Verification Record

## Automated checks completed in the delivery environment

### Backend

- Focused M4-M5 and pipeline-boundary suite: **20 passed**.
- Extended affected pipeline/API suite: **61 passed**.
- Backend collection: **519 tests**.
- The full suite produced progress through `100%` with no failure output. The container wrapper did
  not return cleanly after the test output, so the focused and extended affected suites were rerun
  separately and completed with successful exit codes.
- `python -m compileall -q app tests`: passed.
- Alembic upgraded a clean SQLite database through migration `0008` and `alembic check` reported no
  new upgrade operations.
- `git diff --check`: passed.

Temporary local import stubs for unavailable `anthropic` and `chromadb` packages were used only to
exercise code that replaces those providers with test doubles. Those stubs are outside the project
and are not included in the delivery ZIP.

### Frontend

- ESLint: passed for the full frontend source tree.
- TypeScript strict project check: passed after supplying a temporary declaration for the one
  dependency absent from the recovered Linux test environment (`react-router-dom`). No declaration
  file was retained in the repository.
- The new API client, routing, workflow, and review-workspace tests are included in the project.

## Checks that must be rerun on the user's Windows environment

The delivery environment could not install the exact frontend dependency tree because its internal
npm registry returned package-download errors. The recovered `node_modules` tree also contained a
Windows Rolldown binary, so Vitest and the production Vite build could not run on Linux. Ruff and
mypy executables were likewise unavailable from the environment's package index.

Run these commands before committing:

```powershell
cd frontend
npm ci
npm run lint
npm run typecheck
npm test -- --run
npm run build
```

Then run backend static checks:

```powershell
cd ..\backend
.\.venv\Scripts\Activate.ps1
ruff check .
ruff format --check .
mypy app
pytest -q
alembic check
```

Finally perform the M4-M5 runtime smoke test documented in `docs/M4_M5_HANDOFF.md`.

## Acceptance interpretation

Passing automated tests confirms the implemented orchestration, schema validation, revision
immutability, ownership, source-faithfulness, route behavior, and UI interaction contracts. It does
not by itself prove academic semantic validity; semantic evaluator validation remains governed by
later milestones and approved fixtures.
