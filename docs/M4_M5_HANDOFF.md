# M4-M5 Manual Handoff

## Open the delivery

The ZIP preserves `.git` and the branch `m4-m5-extraction-review`. Extract it to a new folder and
open that folder in Visual Studio Code. Do not overwrite the M3 backup until this delivery passes
local verification.

Confirm the base and branch:

```powershell
git branch --show-current
git log -1 --oneline
git status --short
```

Expected:

- branch: `m4-m5-extraction-review`
- last committed base: `ff78686 feat: implement M3 extraction review pause`
- `git status --short`: the intentional M4-M5 modified and new files, because the delivery is not
  pre-committed.

## Install and verify

```powershell
cd frontend
npm ci
npm run lint
npm run typecheck
npm test -- --run
npm run build

cd ..\backend
.\.venv\Scripts\Activate.ps1
ruff check .
ruff format --check .
mypy app
pytest -q
alembic check
```

## Runtime smoke test

From the repository root:

```powershell
docker compose up -d --build
```

Open `http://localhost:5173`, then:

1. Create an analysis.
2. Upload an Exam PDF and populated TP-153 PDF.
3. Start Analysis.
4. Confirm the analysis reaches `review_ready` and opens the Extraction Review workspace.
5. Check the Questions, CLOs, and Topics tabs. Assessment records and evidence remain internal and are surfaced only through relevant warnings or result evidence.
6. Correct one visibly inaccurate transcription and save a new revision.
7. Exclude one clear false-positive record where appropriate.
8. Confirm that the revision number increases and confirmation is disabled while edits are unsaved.
9. Confirm the latest saved revision.
10. Confirm the UI returns to progress, downstream processing resumes, and refresh does not reopen
    editing.
11. Confirm results become available after completion and no pre-confirmation finding/report exists.

Stop services after verification:

```powershell
docker compose down
```

## Commit only after review

```powershell
git status
git diff --check
git add -A
git commit -m "feat: implement M4-M5 extraction review workflow"
git push -u origin m4-m5-extraction-review
```

After manual approval, merge the branch into `main` using the user's normal review process.

## Future agent context

Claude Code or Codex should read, in this order:

1. `CLAUDE.md`
2. `docs/M4_M5_IMPLEMENTATION_REPORT.md`
3. `docs/M4_M5_VERIFICATION.md`
4. `docs/IMPLEMENTATION_ROADMAP.md`
5. `docs/ARCHITECTURE.md`
6. `docs/API_SPECIFICATION.md`
7. `docs/V1_TRACEABILITY_MATRIX.md`

The next planned milestone is M6. Do not bypass the confirmed-review boundary or reinterpret M4-M5
as academic approval.
