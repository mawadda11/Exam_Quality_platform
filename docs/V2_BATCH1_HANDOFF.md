# Version 2 Batch 1 Handoff

## Included

Batch 1 completes Milestone 0 and Milestone 1:

- frozen architecture/governance decisions;
- public Faculty Member registration;
- login, logout, and password reset;
- protected application routes;
- verified bearer authentication;
- strict analysis/report ownership;
- private dashboard/history per Faculty Member;
- migration `0009`;
- backend and frontend authentication tests.

## Apply and run

Run from the repository root on branch `develop/v2.0.0-arabic-pilot`.

```powershell
git status --short --branch
Copy-Item .env.example .env -ErrorAction SilentlyContinue
docker compose build backend frontend
docker compose up -d postgres chromadb
docker compose run --rm backend alembic upgrade head
docker compose up -d backend frontend
```

Do not use `docker compose down -v`; that deletes the database volume.

Open:

- Frontend: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`

## Manual acceptance

1. Register Faculty Member A.
2. Create an analysis and confirm it appears on A's dashboard.
3. Sign out and sign back in.
4. Request a password reset; local development shows a reset link.
5. Set a new password and verify the old access token/password no longer works.
6. Register Faculty Member B in a private/incognito window.
7. Confirm B has an empty dashboard and cannot access A's copied analysis/report URL.
8. Start two analyses in separate accounts and confirm their state/history remain independent.

## Required local quality gates

```powershell
cd backend
python -m pytest
python -m ruff check app tests
python -m mypy app
cd ..\frontend
npm ci
npm run lint
npm run typecheck
npm test -- --run
npm run build
```

The supplied workspace verified all 540 backend tests and TypeScript/TSX syntax. The full frontend gates must be run locally because the build workspace's npm registry returned HTTP 503 during dependency installation.

## Commit

After all local checks pass:

```powershell
git add -A
git commit -m "feat: add faculty authentication and private dashboards"
git push origin develop/v2.0.0-arabic-pilot
```

## Production/pilot configuration

Before using `APP_ENV=staging` or `APP_ENV=production`, configure:

- a random `SECRET_KEY` of at least 32 characters;
- `SMTP_HOST` and `SMTP_FROM_EMAIL`;
- optional SMTP username/password/TLS settings;
- `PASSWORD_RESET_URL` for the deployed frontend;
- TLS and deployment-level rate limiting.
