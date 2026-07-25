# Scoring Policy

## Approved values
- Satisfied: 1.0
- Partially Satisfied: 0.5
- Not Satisfied: 0.0
- Not Verified: excluded
- Not Applicable: excluded

## Formula
`sum(scored values) / count(verified applicable results) * 100`

## Zero denominator
Return no numeric score and display `Insufficient Evidence`.

## Prohibited additions
No rule weights, dimension weights, severity weights, readiness bands, or labels such as Excellent, Good, or Poor.

## Semantic confidence separation

Semantic confidence is categorical only: `High`, `Medium`, or `Low`. It is not a percentage,
academic status, severity, priority, quality score, readiness label, or scoring weight.

- Confidence never changes the approved value of a verified academic status.
- Low semantic confidence requires the academic status `Not Verified`.
- `Not Verified` remains excluded from the score denominator.
- A Low or Not Verified semantic mapping cannot contribute to deterministic coverage.
- Numeric OCR and extraction confidence are technical source-quality metadata and must not be
  converted into semantic confidence.

The backend will derive categorical semantic confidence from validated evidence conditions in a
later milestone. M1 changes this governance contract only; the current numeric semantic runtime is
an explicitly planned migration, not an alternative scoring policy.

## Reporting
Show the numerical score, denominator, and all five status counts. Not Verified results must remain visible even though excluded from the denominator.
