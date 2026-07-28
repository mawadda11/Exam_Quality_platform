# Version 2 Batch 2 Handoff — Milestones 2 and 3

## Included

Batch 2 completes:

- **Milestone 2:** Arabic/English/mixed exam extraction, quality-gated OCR fallback, Arabic numbering/marks/totals, extraction diagnostics, and persisted file metadata.
- **Milestone 3:** adaptive Course Specification parsing for section-heading, compact, table-led, reordered, Arabic, English, and mixed layouts.

## Important safety boundaries

- The original source line is preserved in review evidence.
- Normalization is used only for matching and number parsing.
- Missing CLOs, topics, assessment percentages, and metadata are never invented.
- Low-confidence extraction remains visible at Extraction Review.
- TP-153 remains supported internally, but the parser now treats it as one Course Specification layout.

## Apply from the repository root

Use the included `APPLY_BATCH2.ps1` from the patch package, or copy the `patch` folder contents into the repository root with overwrite enabled.

Confirm the branch and clean state first:

```powershell
git status
git branch --show-current
```

Expected branch:

```text
develop/v2.0.0-arabic-pilot
```

## Rebuild and migrate

The backend image must be rebuilt because the Dockerfile now installs the Arabic Tesseract language pack.

```powershell
Copy-Item .env.example .env -ErrorAction SilentlyContinue
docker compose build backend
docker compose up -d postgres chromadb
docker compose run --rm backend alembic upgrade head
docker compose up -d backend frontend
```

Do not run `docker compose down -v`; that deletes the database volume.

## Backend quality gates

```powershell
docker compose run --rm `
  -v "${PWD}\backend:/app" `
  -v "${PWD}\docs:/app/docs:ro" `
  -v "${PWD}\CLAUDE.md:/app/CLAUDE.md:ro" `
  backend sh -lc "pip install -e '.[dev]' >/dev/null && ruff format --check . && ruff check app tests && mypy app && pytest"
```

Expected test count after this batch: **554 tests**.

## Frontend regression gates

```powershell
cd frontend
npm ci
npm run lint
npm run typecheck
npm test -- --run
npm run build
cd ..
```

## Manual acceptance

1. Upload an English digital exam and English Course Specification; confirm Extraction Review is unchanged from Version 1 behavior.
2. Upload an Arabic or mixed exam containing `س١`, Arabic sub-questions, Arabic marks, and Arabic total marks; confirm canonical hierarchy and original Arabic source text are both present.
3. Upload a scanned Arabic page; confirm it reaches Extraction Review and low confidence produces a warning rather than silent acceptance.
4. Test a section-heading Course Specification.
5. Test a compact Course Specification.
6. Test a table-led/reordered Course Specification.
7. Confirm missing sections produce missing evidence and no placeholder CLO/topic/percentage.
8. Recheck two-user ownership isolation from Batch 1.

## Commit

After every gate is green:

```powershell
git add -A
git commit -m "feat: add bilingual extraction and adaptive course specification parsing"
git push origin develop/v2.0.0-arabic-pilot
```
