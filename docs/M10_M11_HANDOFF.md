# Version 1.0.0 Handoff

## Repository source of truth

Use the repository, Git history, tests, and these handoff documents as the source of truth. Do not
reconstruct project state from a prior chat transcript.

Read in this order:

1. `CLAUDE.md`
2. `README.md`
3. `docs/RELEASE_V1.md`
4. `docs/M10_M11_IMPLEMENTATION_REPORT.md`
5. `docs/M10_M11_VERIFICATION.md`
6. `docs/OWNER_FINAL_CHECKLIST.md`
7. `docs/V2_ROADMAP.md`
8. `docs/AI_GOVERNANCE.md`
9. `docs/SCORING_POLICY.md`
10. `docs/TEST_PLAN.md`

## Current Git state

- Branch: `release/v1.0.0`.
- M1-M9 base: `5f76d6a`.
- M10-M11 commit: `d2eb3d4` (`feat: complete M10 presentation and M11 release validation`).
- The final Version 1 UX refinement is intentionally left as uncommitted working-tree changes for
  the project owner to test, review, commit, and push.
- No migration or knowledge-base source-workbook change belongs to the final UX refinement.
- `VERSION` declares product release `1.0.0`.

## Final Version 1 UX refinement

The final refinement separates platform capability from an individual exam result:

- The Overview no longer shows the full 21-rule capability table or the mostly fixed
  evaluated/limited/planned counts.
- The Overview shows only a concise completion message relevant to the current analysis.
- A separate **What the Platform Evaluates** page documents 14 available checks, one check with a
  defined limitation, and six planned/deferred checks.
- Planned or deferred platform capability is never presented as failure of the uploaded exam.
- The user-facing Overview no longer shows arithmetic working for the score. The governed scoring
  contract remains unchanged and remains documented and auditable.

## First action for the next coding agent

Before editing:

```powershell
git status --short --branch
git log --oneline --decorate -15
git diff --stat
git diff
git diff --cached
```

Do not reset, clean, stash, revert, overwrite, or regenerate the Version 1 working tree. Inspect it
as intentional prior work. Run the completion gate in `docs/OWNER_FINAL_CHECKLIST.md`, and fix only
verified failures with the smallest coherent change and corresponding tests.

## Important implementation locations

### Frontend

- `frontend/src/features/analysis-results/OverviewSection.tsx`
- `frontend/src/features/analysis-results/RuleCoveragePanel.tsx`
- `frontend/src/features/analysis-results/SemanticConfidenceBadge.tsx`
- `frontend/src/features/analysis-results/SemanticEvaluationDetails.tsx`
- `frontend/src/features/platform-scope/platformScopeData.ts`
- `frontend/src/routes/EvaluationScopeRoute.tsx`
- `frontend/src/components/layout/PrimaryNavigation.tsx`
- `frontend/src/styles/results.css`
- `frontend/src/styles/evaluation-scope.css`

### Backend/reporting

- `backend/app/services/reporting/content.py`
- `backend/app/services/reporting/pdf.py`
- `backend/app/api/analyses.py`
- `backend/tests/test_report_content.py`
- `backend/tests/test_report_pdf.py`
- `backend/tests/test_m10_m11_release_acceptance.py`

## Contracts that must remain unchanged

- Exactly five academic statuses.
- Exact scoring: 1.0 / 0.5 / 0.0; exclude Not Verified and Not Applicable.
- `Insufficient Evidence` for a zero denominator.
- Semantic confidence is backend-derived categorical High/Medium/Low and has no scoring weight.
- Low semantic confidence releases as Not Verified.
- Runtime capability dispositions are not academic statuses.
- Derived mappings reference confirmed evidence, remain advisory, and never overwrite source facts.
- No AI evaluation before exact extraction-review confirmation.
- Exam PDF plus populated TP-153 remain required.
- Unsupported/deferred rules remain documented; do not delete them from the knowledge base merely
  because Version 1 does not execute them.

## Final commit and push after validation

```powershell
git add -A
git status --short
git diff --cached --stat
git commit -m "feat: finalize AI Exam Quality Platform v1.0.0"
git push -u origin release/v1.0.0
```

Never commit `.env`, uploads, generated reports, package caches, virtual environments, real exams,
or private TP-153 files. Do not force-push.
