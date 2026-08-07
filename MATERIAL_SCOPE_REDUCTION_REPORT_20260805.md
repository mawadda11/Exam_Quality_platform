# Final controlled-pilot material-scope update — 2026-08-05

## Decision

Automatic supporting-material extraction is narrowed instead of removed.

The review now keeps only a figure, table, or code/schema block when:

1. a question contains an explicit label such as `Table 1` / `Figure 2`, or
2. the question contains a clear contextual cue such as `Use the following schema`,
   `Refer to the table`, or `Based on the diagram`, and there is one unambiguous physical
   candidate of the expected type on the same page.

## Excluded automatically

- cover/course-information tables;
- True/False answer grids that are part of the question itself;
- generic layout tables and blank answer grids;
- logos and decorative assets;
- ambiguous pages with multiple equally plausible materials.

## Review behavior

- Retained context is linked to the question that called for it.
- The Faculty Member can confirm the question link or exclude the item.
- Unlabeled but directly reviewed context can satisfy the association check.
- Unlinked retained context is `Not Verified`, never an automatic negative judgment.
- If no question-linked context remains, the material-association check is `Not Applicable`.

## UI changes

- The review section is now titled **Linked supporting context**.
- Empty label/caption fields are hidden.
- A short scope explanation appears above the retained items.

## Validation performed

- 51 targeted backend tests passed across digital extraction, structured evidence,
  persistence, and rule integration.
- The first synthetic Saudi database exam was checked directly: the cover metadata table
  and the True/False grid were removed; only the Q4 database schema remained and was linked
  to Q4.
- TypeScript transpilation/syntax checks passed for both modified frontend files.
- Knowledge-base validation passed: 441 records across 11 workbooks.
- Full backend test execution reached 52% before stopping on two pre-existing semantic
  baseline expectation failures (`Medium` versus `High`, and `Not Verified` versus an older
  negative-status expectation). These failures are outside this material-scope change.
- Frontend dependency installation could not complete because the configured internal npm
  registry returned 404 for `zod-validation-error@4.0.2`.

## No platform changes

- No database migration.
- No Gemini call and no quota consumption.
- Google Document AI remains excluded.
- Scoring weights and academic-status values are unchanged.
