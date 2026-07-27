# Owner Final Checklist — Version 1.0.0

Use this checklist after extracting the final Version 1 ZIP on the Windows development computer.

## 1. Confirm the branch and intended changes

```powershell
git status --short --branch
git log --oneline --decorate -5
git diff --stat
```

Expected branch: `release/v1.0.0`. The M10-M11 commit should be present, with the final UX refinement
shown as uncommitted changes. Do not run `git reset`, `git clean`, or discard changes.

## 2. Backend verification

```powershell
cd backend
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy app
.\.venv\Scripts\python.exe -m pytest
cd ..
```

Expected backend baseline: 526 tests pass. A later intentional test addition may increase the count.

## 3. Frontend verification

```powershell
cd frontend
npm ci
npm run lint
npm run typecheck
npm test -- --run
npm run build
npm audit
cd ..
```

Do not run `npm audit fix --force`. Version 1 currently retains the documented React Router advisory
because npm proposes a breaking forced change; treat dependency remediation as a separately tested
maintenance task.

## 4. Knowledge-base verification

```powershell
.\backend\.venv\Scripts\python.exe scripts\validate_knowledge_base.py
git restore knowledge_base/manifest.json
git status --short -- knowledge_base
```

Expected controlled baseline: 437 normalized records across 11 workbooks. No source workbook under
`knowledge_base/source/` may be changed by this release.

## 5. Manual workflow and final UX

Start the application with Docker:

```powershell
Copy-Item .env.example .env -Force
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose restart backend
docker compose ps
```

Open `http://localhost:5173` and use synthetic/non-private PDFs only. Confirm:

1. A Midterm or Final analysis requires both the exam PDF and populated TP-153.
2. Extraction pauses at the review workspace and exact-revision confirmation resumes processing.
3. Completed results show categorical semantic confidence without numeric AI confidence.
4. AI-derived CLO/topic relationships are clearly advisory and do not overwrite TP-153 evidence.
5. Overview shows the final score and plain-language result counts without an arithmetic equation.
6. Overview does not show the full 21-rule capability table or the fixed six unsupported checks.
7. Overview shows a concise analysis-completion message and a link to **What the Platform Evaluates**.
8. The **What the Platform Evaluates** page shows available, limited, and planned checks separately.
9. Planned checks are not shown as failures of an individual exam and do not reduce its score.
10. Generated PDF reporting still contains the governed audit detail, evidence, reasoning, mappings,
    recommendations, score methodology, and runtime coverage required for traceability.
11. No real exam, TP-153, report, `.env`, or credential appears in Git status.

Stop the stack:

```powershell
docker compose down
```

## 6. Security and repository hygiene

```powershell
git diff --check
git status --short | Select-String "\.env|node_modules|\.venv|dist|\.pdf"
git status --short -- knowledge_base/source
git ls-files .env
```

All four checks should produce no unexpected output.

## 7. Commit and push the release branch

```powershell
git add -A
git status --short
git diff --cached --stat
git commit -m "feat: finalize AI Exam Quality Platform v1.0.0"
git push -u origin release/v1.0.0
```

Do not force-push. Merge to `main` only after the release branch has been reviewed and the final
manual checks pass.
