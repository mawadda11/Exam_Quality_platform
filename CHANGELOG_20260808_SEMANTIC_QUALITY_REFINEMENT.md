# Semantic Quality Refinement — 2026-08-08

This update is based on `Exam_Quality_FINAL_SEMANTIC_MAPPING_RESTORED_20260808`.

## Changes

- Kept Gemini as the primary semantic decision-maker for Question → CLO / Topic mapping.
- Strengthened mapping prompts so Gemini may return `Not Satisfied` instead of forcing the nearest CLO/topic.
- Kept `Not Verified` for genuinely insufficient evidence, not ordinary semantic mismatch.
- Added explicit scope-sensitive topic guidance (for example, IPv4 is not automatically IPv6).
- Recovered split exam-level instruction blocks such as `Instructions / التعليمات` followed by bullet lines.
- Isolated `Complete Instructions` evaluation from question text and question-specific instructions.
- Removed administrative missing-mark phrases such as `Mark not stated` from canonical question stems while preserving source provenance and null marks.
- Prevented missing mark values/labels from being treated as task-clarity, wording-ambiguity, or question-information defects by semantic writing rules.
- No scoring formula change and no frontend design change.

## Verification

- 145 targeted backend tests passed across extraction, structure reconciliation, semantic evaluators/validation, persistence, and pipeline integration.
- Real CPIT370 fixture check: Q3(c) retains `marks=None`, the canonical stem no longer contains `Mark not stated`, and the general instruction block is recovered as instruction evidence.
- A full backend suite run was also attempted; it progressed without failures until the execution environment timeout, so only the targeted 145-test result is claimed as completed verification.
