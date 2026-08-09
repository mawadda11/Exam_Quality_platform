# Marks Finding Flow Fix — 2026-08-08

## Purpose
Extraction Review now verifies transcription against the source PDF without forcing faculty to repair confirmed exam-quality defects before analysis.

## Behavior
- A confirmed parent/child marks mismatch no longer blocks **Confirm Extraction and Continue**.
- The red **Confirmation unavailable** message is therefore not shown for marks arithmetic mismatches.
- Deterministic single-unknown-child inference remains unchanged:
  - parent 9 + children 3, 3, ? -> inferred child = 3.
  - parent 9 + children 3, ?, ? -> no assumed distribution.
- `Correct Total Marks` can now return **Not Satisfied** for a mathematically proven internal marks inconsistency even when the declared exam total still matches the parent totals.
- General declared-total mismatches continue to return **Not Satisfied**.
- Missing/unreadable marks remain **Not Verified** only when the available evidence is insufficient to judge correctness.
- Parent marks remain authoritative for overall total calculation, so parent and child marks are never double-counted.

## Verification
Targeted backend tests were run for extraction review, marks rules, scoring, findings, reports, and batch acceptance fixtures: 85 passed.
