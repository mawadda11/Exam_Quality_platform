# M10-M11 Handoff

## Repository source of truth

Use the repository, Git history, tests, and these handoff documents as the source of truth. Do not
reconstruct project state from a prior chat transcript.

Read in this order:

1. `CLAUDE.md`
2. `README.md`
3. `docs/M10_M11_IMPLEMENTATION_REPORT.md`
4. `docs/M10_M11_VERIFICATION.md`
5. `docs/OWNER_FINAL_CHECKLIST.md`
6. `docs/IMPLEMENTATION_ROADMAP.md`
7. `docs/AI_GOVERNANCE.md`
8. `docs/SCORING_POLICY.md`
9. `docs/TEST_PLAN.md`

## Current state

- M1-M9 were already committed at base commit `5f76d6a`.
- M10 presentation/report refinement is implemented in the working tree.
- M11 integrated release acceptance is implemented in the working tree.
- No migration or knowledge-base source change is part of this delivery.
- Changes are intentionally left uncommitted for the project owner to run the final local gate,
  review, commit, and push.

## First action for the next coding agent

Before editing:

```powershell
git status --short --branch
git log --oneline --decorate -15
git diff --stat
git diff
git diff --cached
```

Do not reset, clean, stash, revert, overwrite, or regenerate the M10-M11 working tree. Inspect it as
intentional prior work.

Then run the required local completion gate in `docs/M10_M11_VERIFICATION.md`. Fix only verified
failures with the smallest coherent changes and add/update tests for each fix.

## Important implementation locations

### Frontend

- `frontend/src/features/analysis-results/FindingCard.tsx`
- `frontend/src/features/analysis-results/SemanticConfidenceBadge.tsx`
- `frontend/src/features/analysis-results/SemanticEvaluationDetails.tsx`
- `frontend/src/features/analysis-results/RuleCoveragePanel.tsx`
- `frontend/src/features/analysis-results/OverviewSection.tsx`
- `frontend/src/features/analysis-results/useAnalysisResultsData.ts`
- `frontend/src/styles/results.css`

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
- RULE015, RULE017, RULE020, and the undefined two-or-more-CLO RULE006 branch remain deferred.

## Suggested commit sequence after all checks pass

```powershell
git add backend/app backend/tests frontend/src docs README.md CLAUDE.md
git status --short
git diff --cached --stat
git commit -m "feat: complete M10 presentation and reporting"

git add -A
git status --short
git diff --cached --stat
git commit -m "test: complete M11 integrated release validation"
git push origin main
```

The owner may instead use one coherent M10-M11 commit. Never commit `.env`, uploads, generated
reports, package caches, virtual environments, real exams, or private TP-153 files.
