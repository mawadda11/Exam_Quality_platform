# Exam Quality Analyzer — Analysis Foundation Fix

Date: 2026-08-05

## Implemented changes

1. **Declared total marks extraction**
   - Added deterministic token-and-geometry recovery for compact bilingual header rows.
   - Correctly distinguishes `Duration: 75 minutes` from `Total Marks: 30` when both appear on the same PDF row.
   - Persists the canonical evidence text as `Total Marks: 30` while retaining the source span for audit.

2. **Unassigned candidate cleanup**
   - Hides answer-space dotted lines, `No. Statement T/F` table headers, synthetic-document footers, standalone page fractions, empty text, and punctuation-only geometry artifacts.
   - Keeps genuine unassigned text visible, including legitimate questions containing fractions.
   - Source rows remain in the immutable review snapshot for audit; only the noisy reviewer-facing list is filtered.

3. **Supporting-material applicability**
   - `Supporting Material Association` now returns `Not Applicable` when detected layout/decorative material is present but no question explicitly references or depends on it.
   - Explicit figure/table/code references continue to use the governed association rules.

4. **More conservative local-only semantic decisions**
   - Lack of lexical overlap is no longer treated as proof of a negative CLO/topic relationship or out-of-scope content.
   - The local-only baseline returns `Not Verified` when it cannot establish a controlled relationship.
   - Question-format suitability also becomes `Not Verified` when no intended CLO relationship can be established locally.

5. **Finding explanations tied to evidence**
   - Local semantic findings now include the status distribution and up to three concrete question/source labels with their reasons.
   - Replaces the repeated generic explanation that only stated how many source items were evaluated.

## Verification performed

- 77 targeted backend tests passed across:
  - declared total extraction
  - marks and totals rules
  - digital PDF extraction
  - line classification
  - structured evidence rules
  - local semantic evaluation regressions
- The first Saudi realistic database exam was extracted directly and produced one declared-total evidence row:
  - `Total Marks: 30`
  - parsed value: `30.0`
  - confidence: `0.95`
- FastAPI application import succeeded.
- Changed TypeScript/TSX files passed TypeScript syntax transpilation.
- Full frontend Vitest execution was not available because `node_modules` was not installed in the build environment.
- No Gemini call was made.
- No Google Document AI integration was added.
- No database migration was added.

## Required retest behavior

Create a **new analysis** after installing this version. Existing confirmed extraction revisions and previously generated findings remain immutable and are not rewritten automatically.
