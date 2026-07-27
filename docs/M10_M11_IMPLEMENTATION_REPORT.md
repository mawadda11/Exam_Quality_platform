# M10-M11 Implementation Report

## Delivery summary

M10 completes the presentation layer for the governed hybrid evaluation runtime delivered in
M6-M9. M11 adds an integrated release-acceptance test and synchronizes the repository handoff so a
future coding agent can continue from the repository rather than from a lost chat transcript.

This delivery does not broaden product scope. A valid analysis still requires one Midterm or Final
exam PDF and one populated TP-153 for a computing course. No limited exam-only mode, accreditation
decision, student-answer analysis, grade analysis, difficulty estimate, Bloom classification,
faculty evaluation, or approve/reject workflow was added.

## M10 - presentation and report refinement

### Results workspace

- Displays backend-derived semantic confidence only as the categorical values `High`, `Medium`, or
  `Low`.
- Explicitly states that semantic confidence is not a score, severity, priority, probability, or
  scoring weight.
- Presents the governed semantic decision reasoning, confidence basis, controlled KB references,
  and evidence-linked item judgments retained in `evaluation_details`.
- Labels RULE001 and RULE007 target relationships as **AI-derived advisory relationships** and
  states that they are not official TP-153 mappings and do not overwrite source evidence.
- Preserves the runtime rule-coverage audit independently from academic statuses using
  `evaluated`, `conditional_capability_gap`, `unsupported`, and `not_run`. The final Version 1 UX
  presents only an analysis-specific completion message in Overview and moves the complete platform
  capability catalogue to the separate **What the Platform Evaluates** page.
- Keeps the score concise for faculty users. The final Overview does not expose arithmetic working;
  the exact governed methodology remains in the report and technical documentation.

### PDF report

Generated reports now freeze and present:

- score, earned credit, denominator, and all five academic-status counts;
- the runtime rule-coverage audit and integrity result;
- confirmed TP-153 assessment-method source records;
- categorical semantic confidence and its basis;
- concise governed reasoning;
- item-level source and target evidence relationships;
- explicit source-versus-derived relationship labels;
- controlled KB identifiers and provider/model/prompt/KB provenance; and
- existing controlled recommendations.

The report renderer remains presentation-only. It reuses persisted findings, source evidence,
assessment records, the authoritative scoring service, and the authoritative coverage audit. It
does not infer new academic facts.

## Final Version 1 UX refinement

After manual review, the capability catalogue was identified as platform-level information rather
than an exam-specific result. Version 1.0.0 therefore removes the large 21-rule table and mostly
fixed support counts from the default Overview, adds a separate platform-scope page, and replaces
the visible score equation with a plain-language explanation. No knowledge-base rule, scoring rule,
or report audit detail was removed.

## M11 - integrated release validation

A real API-level acceptance test now exercises the complete supported workflow with synthetic
files and the offline local semantic provider:

1. create an owned analysis;
2. upload an exam and populated TP-153;
3. start extraction;
4. pause at `review_ready`;
5. load and confirm the exact extraction revision;
6. continue governed evaluation to completion;
7. inspect semantic findings and retained relationships;
8. verify exact score-denominator arithmetic;
9. verify all-rule runtime coverage;
10. generate and download the PDF report; and
11. verify owner isolation for protected results.

The test uses synthetic data only and makes no external AI call.

## Files added

- `backend/tests/test_m10_m11_release_acceptance.py`
- `frontend/src/features/analysis-results/SemanticConfidenceBadge.tsx`
- `frontend/src/features/analysis-results/SemanticEvaluationDetails.tsx`
- `frontend/src/features/analysis-results/SemanticEvaluationDetails.test.tsx`
- `frontend/src/features/analysis-results/RuleCoveragePanel.tsx`
- `frontend/src/features/analysis-results/RuleCoveragePanel.test.tsx`
- `docs/M10_M11_IMPLEMENTATION_PLAN.md`
- `docs/M10_M11_IMPLEMENTATION_REPORT.md`
- `docs/M10_M11_VERIFICATION.md`
- `docs/M10_M11_HANDOFF.md`

## Files materially updated

- report content assembly and PDF rendering;
- report-generation API assembly;
- report unit/API tests;
- analysis-results loading, overview, finding presentation, tests, and styles;
- README, roadmap, SRS, API, test-plan, frontend-design, and traceability status documentation.

## Intentionally unchanged

- knowledge-base source workbooks;
- scoring formula and academic statuses;
- migrations and persistence schema;
- semantic confidence derivation;
- provider safety gates;
- retained rule deferrals;
- upload, extraction-review, and confirmation contracts.
