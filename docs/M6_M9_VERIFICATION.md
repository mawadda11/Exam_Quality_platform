# M6-M9 Verification

## Automated verification completed in the delivery environment

- Knowledge-base validation: 437 governed records across all 11 controlled workbooks validated and normalized deterministically.
- Python compilation: application and tests compile successfully.
- Backend full suite: all 522 collected pytest tests passed.
- Focused semantic validation/evaluator/retrieval/persistence/coverage tests passed.
- M6-M9 real pipeline integration tests passed for:
  - complete Exam + TP-153;
  - uncited but semantically evaluable questions;
  - partial mappings;
  - hyphenated/bracketed controlled identifiers;
  - missing CLO source data;
  - single-CLO Not Applicable distribution;
  - exact ten-rule semantic runtime; and
  - invalid provider output rollback.
- Coverage audit accounts for all 21 exam-facing rules and detects silent supported-rule omissions.
- Frontend source syntax/transpile inspection passed for all 99 TypeScript/TSX source files without dependencies.

## Delivery-environment limitations

The delivery environment could not install the frontend npm dependency tree, so ESLint, the full
TypeScript project check, Vitest, and the Vite production build were not executed here. Ruff and
mypy were also unavailable from the delivery package index. These checks remain mandatory on the
user's Windows environment before commit and merge. The backend pytest suite, Python compilation,
knowledge-base validation, and dependency-free TypeScript syntax/transpile inspection did run here.

## Required Windows verification before merge

From `backend/` with the project virtual environment active:

```powershell
ruff check .
ruff format --check .
mypy app
pytest -q
```

From `frontend/`:

```powershell
npm ci
npm run lint
npm run typecheck
npm test -- --run
npm run build
```

From the repository root:

```powershell
python scripts/validate_knowledge_base.py
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose ps
```

## Manual acceptance

1. Create an analysis and upload a complete Exam PDF and TP-153 PDF.
2. Review and confirm extraction.
3. Confirm processing completes without silently collapsing supported semantic rules to Not
   Verified.
4. Inspect Findings for RULE001/002/003/004/005/007/008/009/011/012/013/018/019/021.
5. Confirm semantic Findings expose `confidence_level` and structured `evaluation_details`.
6. Call `/api/v1/analyses/{analysis_id}/rule-coverage` and verify:
   - 21 total rules;
   - 14 evaluated unconditional rules for complete inputs;
   - 1 conditional RULE006 capability gap for two-or-more CLOs;
   - 6 explicit unsupported/deferred rules;
   - 0 unexpected `not_run` rules.
7. Repeat with a TP-153 missing CLOs and verify only CLO-dependent rules become genuine Not
   Verified while topic, assessment, and question-writing rules still execute.
