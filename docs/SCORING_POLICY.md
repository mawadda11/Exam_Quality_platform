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

## Reporting
Show the numerical score, denominator, and all five status counts. Not Verified results must remain visible even though excluded from the denominator.
