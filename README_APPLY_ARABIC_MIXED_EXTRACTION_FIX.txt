Exam Quality Analyzer — Arabic/Mixed Extraction Fix

This patch is an overlay for the current project. It contains backend extraction code and regression tests only.
It supersedes the earlier RTL-only Arabic reading-order patch; you do not need to apply that older patch first.

Apply on Windows PowerShell from the project directory after extracting this ZIP over the project root, then rebuild only the backend:

docker compose -p exam_quality_fixed up -d --build --no-deps backend

After the backend is running, create a NEW analysis for the Arabic fixture. Existing saved extraction revisions keep their old extracted data and are not rewritten automatically.

No DB migration is required.
