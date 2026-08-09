# Arabic / Mixed-Language Extraction Regression Fix — 2026-08-08

## Scope

This patch fixes the Arabic and mixed Arabic/English extraction regressions observed in the CPIT405 final test without introducing a separate Arabic extraction pipeline. Gemini remains the visual structure parser for both Arabic and English; deterministic extraction/reconciliation remains the source-faithful guardrail.

## Fixed

- Uses geometry-derived logical reading text for canonical Arabic/mixed source lines while preserving untouched provider text separately as `raw_text` for audit/provenance.
- Preserves left-to-right order of embedded technical phrases inside RTL lines (for example `REST API`, `HTTP method`, `Code 1`, `Input Validation`, and `SQL Injection`).
- Repairs conservative PDF glyph artifacts for detached Arabic tanween/diacritics.
- Recognizes mixed RTL hierarchical labels such as provider-order `1.2 Q ...` as the visual question `Q1.2`.
- Keeps Arabic MCQ choices (`أ/ب/ج/د`) and numeric option values such as `200/301/404/500` as options instead of materializing them as fake questions.
- Prevents duplicate visual candidates from becoming duplicate canonical questions when the same source span is already owned by a question or MCQ option.
- Restores deterministic top-to-bottom sequence after option promotion/table expansion so reconciliation cannot interleave Q2/Q3/Q4 children incorrectly.
- Recovers Arabic True/False table rows from geometry-backed logical cell text, including tables whose response header is exposed in visual glyph order.
- Preserves explicit standalone Arabic mark lines and attaches them to the appropriate question instead of suppressing them as graphic labels.
- Detects vector-drawn figures when an explicit Figure/شكل label is present, keeping diagram labels out of the question stem.
- Expands code-material detection for JavaScript/fetch-style snippets so code text stays supporting material rather than question text.
- Strengthens the Gemini structure prompt for Arabic option labels, numeric choices, mixed RTL/LTR labels, T/F rows, standalone marks, duplicate avoidance, and exact PDF order.

## Regression coverage

Targeted extraction/rules suite: 107 tests passed.

The supplied Arabic CPIT405 fixture was also exercised end-to-end through the local deterministic extraction/structure path with these assertions:

- exactly 22 canonical questions in PDF order;
- Q1 + Q1.1–Q1.6, all MCQ children at 1 mark;
- `200/301/404/500` remain Q1.1 options and never become questions;
- Q2 + Q2.1–Q2.6, with child marks left unset as printed;
- Q3(a–c) and Q4(a–c) each retain explicit 3-mark values;
- no duplicate Q4(a);
- `REST API`, `HTTP method`, `REST endpoint`, `Code 1`, `Input Validation`, and `SQL Injection` preserve their logical order;
- code and vector figure materials are detected separately from question stems;
- `نهاية الاختبار` is not appended to Q4(c).

Two existing English fixtures (CS201 and CPIT425) retained the same deterministic question counts and label order before and after the patch.

## Notes

- No database migration.
- No frontend change.
- No translation model or Gemini translation is added.
- Existing analyses/revisions are not rewritten. Start a new analysis after rebuilding the backend to validate the fix.
- The live Gemini API was not invoked in this offline validation; the Gemini prompt/reconciliation code paths are covered by tests, while the user-facing live run should be used as the final integration check.
