# Version 2 Batch 3 Test Results

## Backend verification in the package build environment

- All backend test files were executed in two complete groups.
- Total collected backend tests: **570**.
- Result: **570 passed**.
- Changed Batch 3 tests cover account language preference, migration upgrade/downgrade metadata,
  safe failed-stage progress fields, retry acceptance and rejection boundaries, duplicate/concurrent
  recovery protection, report language persistence, and Arabic/English PDF generation.
- Python compile validation completed for application, migrations, and tests.

## Frontend static verification in the package build environment

- TypeScript/TSX syntax transpilation completed with zero syntax errors.
- A JSX user-visible-text scan found no untranslated hard-coded English strings except the intentional
  language option label `English`.
- New/updated tests are included for language persistence and direction, Retry Analysis UI/API,
  question hierarchy behavior, and report language selection.

## Required owner-machine gate after applying

The package intentionally retains the project's existing dependency lockfile and adds no frontend
runtime dependency. Run the normal project gates on the owner machine:

- Backend: Ruff check/format, mypy, and pytest.
- Frontend: ESLint, TypeScript typecheck, Vitest, and production build.
- Manual: Arabic/English switching, refresh persistence, failed-analysis retry, parent/child review,
  Arabic report, English report, RTL desktop, and mobile-width review.
