# M10-M11 Verification

## Environment

- Python: 3.13.5 (project contract is 3.12+)
- Node.js: 22.16.0
- npm: 10.9.2
- Backend semantic provider in acceptance tests: offline `local`
- Test documents: synthetic only

## Passed checks

### Backend

- `python -m compileall -q app tests`
  - Passed.
- `python -m pytest`
  - **526 passed in 30.54 seconds.**
- Focused M10 reporting suites:
  - `tests/test_report_content.py`
  - `tests/test_report_pdf.py`
  - `tests/test_reports_api.py`
  - Passed.
- Integrated M10-M11 release acceptance:
  - `tests/test_m10_m11_release_acceptance.py`
  - Passed.

### Knowledge base

- `python scripts/validate_knowledge_base.py`
  - Passed.
  - Validated and normalized 437 records across 11 workbooks.
  - The regenerated manifest matched the committed manifest; source workbooks were not modified.

### Frontend source integrity

- Parsed all 105 TypeScript/TSX source files with the TypeScript 5.8.3 parser.
  - Zero syntax diagnostics.

## Environment-blocked checks

The container package registry returned HTTP 503 responses while `npm ci` downloaded frontend
dependencies. Consequently the following commands could not be executed reliably in this
container:

- `npm run lint`
- `npm run typecheck`
- `npm test -- --run`
- `npm run build`

This is a dependency-registry availability issue, not a reported application-test failure. These
four commands remain the first local verification gate before committing or pushing. Do not bypass
them.

The same package index did not expose installable `ruff`, `mypy`, or `types-openpyxl` distributions,
so the repository-standard Ruff and mypy commands could not be rerun in this container. The full
Python test suite and bytecode compilation passed, but local Ruff and mypy remain required before
commit.

## Required local completion gate

From a clean local checkout with dependencies available:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
ruff check .
ruff format --check .
mypy app
pytest

cd ..\frontend
npm ci
npm run lint
npm run typecheck
npm test -- --run
npm run build

cd ..
python scripts/validate_knowledge_base.py
```

Any failure must be fixed and documented before M10-M11 is committed. Do not weaken a test,
validation, security, evidence, confidence, or governance rule to make the gate pass.
