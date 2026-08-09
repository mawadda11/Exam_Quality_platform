Exam Quality Analyzer — General mixed Arabic/English display fix

Apply AFTER Exam_Quality_ARABIC_MIXED_EXTRACTION_FULL_FIX_20260808.

What this patch changes:
- Removes duplicated leading question identifiers from faculty-facing question text even when PDF spacing differs (Q1.1 vs Q 1.1, Q3(a) vs Q 3 (a)).
- Lets dir="auto" determine direction from the actual question sentence instead of a leading Latin question identifier.
- Uses unicode-bidi: plaintext consistently for question text in Extraction Review and Results.
- Does not translate, reorder, or rewrite Arabic/English technical terms.
- Does not change canonical source evidence or extraction logic.
- No database migration.

After extracting into the project root, rebuild the frontend only:
  docker compose -p exam_quality_fixed up -d --build --no-deps frontend

Then hard-refresh the browser with Ctrl+Shift+R.
