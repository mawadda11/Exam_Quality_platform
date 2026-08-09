# Source-faithful Extraction Review fix — 2026-08-08

This patch keeps Extraction Review focused on transcription and structure, not analysis commentary.

## Changes

- Prevent explicit synthetic QA fixture/test-harness notes from becoming canonical question text.
- Keep those visible source lines available for provenance/PDF review instead of deleting them from the source model.
- Prevent wrapped fixture-note continuation lines from leaking into stems.
- Treat `End of Examination` / Arabic end-of-exam furniture as non-question text.
- Expand missing-mark administrative-note cleanup (for example, `No individual mark is printed for Q3(c).`).
- Strengthen the Gemini structure prompt: AI may understand boundaries and roles, but it must not author, paraphrase, or append test-harness commentary to canonical stems.
- Preserve the previously added context-aware MCQ vs lettered-subquestion behavior.

## Regression checks

For the CPIT370 marks-policy fixture, deterministic extraction now keeps:

- Q2: `Question 2 - True / False`
- Q3(c): only the actual gateway question
- Q4(c): only the actual delay question
- Q5(b): only the actual VLAN question

Fixture intent / analyzer instructions remain outside canonical question text.
