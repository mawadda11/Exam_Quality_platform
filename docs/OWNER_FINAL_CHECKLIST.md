# Owner Final Checklist

Use this checklist after extracting the delivered ZIP on the Windows development computer.

## 1. Preserve the working tree

Open the repository root in VS Code and run:

```powershell
git status --short --branch
git log --oneline --decorate -5
git diff --stat
```

The M10-M11 files are intentionally uncommitted. Do not run `git reset`, `git clean`, or discard
changes.

## 2. Backend verification

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
mypy app
pytest
cd ..
```

Expected test baseline for this delivery: 526 backend tests pass. A different count is acceptable
only when a documented later change intentionally adds or removes tests.

## 3. Frontend verification

```powershell
cd frontend
npm ci
npm run lint
npm run typecheck
npm test -- --run
npm run build
cd ..
```

All commands must exit successfully before commit.

## 4. Knowledge-base verification

```powershell
python scripts/validate_knowledge_base.py
```

Expected controlled baseline: 437 normalized records across 11 workbooks and no unreviewed change
to `knowledge_base/source/`.

## 5. Manual supported workflow

Start the application with Docker:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open `http://localhost:5173` and use synthetic/non-private PDFs only. Confirm:

1. A Midterm or Final analysis requires both the exam PDF and populated TP-153.
2. Extraction pauses at the review workspace.
3. Exact-revision confirmation resumes processing.
4. Completed results show categorical semantic confidence without a numeric AI confidence.
5. RULE001/RULE007 relationships are labelled AI-derived advisory relationships.
6. Overview shows earned-credit and denominator transparency.
7. Rule execution coverage remains separate from academic status.
8. The generated PDF contains assessment records, score transparency, coverage, evidence,
   semantic reasoning, and source-versus-derived mapping labels.
9. No real exam, TP-153, generated report, `.env`, or credential appears in Git status.

Stop the stack when finished:

```powershell
docker compose down
```

## 6. Commit and push

Review before staging:

```powershell
git status --short
git diff --stat
git diff
```

After every required check passes:

```powershell
git add -A
git status --short
git diff --cached --stat
git commit -m "feat: complete M10-M11 presentation and release acceptance"
git push origin main
```

Do not force-push. If a check fails, give the next coding agent the exact command, complete error
output, and `docs/M10_M11_HANDOFF.md`.
