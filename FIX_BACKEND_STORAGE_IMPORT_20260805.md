# Backend storage import fix — 2026-08-05

## Root cause
The distributed ZIP omitted the required Python package:

`backend/app/services/storage/`

Several backend modules import `app.services.storage.*`, so Uvicorn failed during startup with:

`ModuleNotFoundError: No module named 'app.services.storage'`

## Restored files
- `backend/app/services/storage/__init__.py`
- `backend/app/services/storage/files.py`
- `backend/app/services/storage/keys.py`
- `backend/app/services/storage/validation.py`

These files were restored from the last working project version without changing database schemas, migrations, extraction behavior, Gemini settings, or user data.

## Verification
- `import app.main` passed.
- Backend tests passed:
  - `tests/test_health.py`
  - `tests/test_file_validation.py`
  - `tests/test_uploads_api.py`
  - `tests/test_analysis_deletion.py`
  - `tests/test_reports_api.py`
- 65 selected tests passed.
