# M6-M9 Handoff

## Branch and base

- Branch: `m6-m9-governed-semantic-evaluation`
- Base commit: `cce3dc0` (`feat: implement M4-M5 extraction review workflow`)
- Changes are intentionally left uncommitted for local review.

## Review priority

The principal acceptance question is whether supported KB criteria execute from confirmed evidence
instead of defaulting to `Not Verified`. Do not judge success by the number of Satisfied results.
Judge it by complete governed execution, honest statuses, evidence traceability, and explicit
capability accounting.

## Important files

- Semantic contract: `backend/app/services/rules/semantic_types.py`
- Backend validation/confidence: `backend/app/services/rules/semantic_validation.py`
- Semantic evaluators: `backend/app/services/rules/semantic_evaluators.py`
- Offline development adapter: `backend/app/services/ai/local_provider.py`
- Deterministic coverage: `backend/app/services/rules/clo_topic_coverage.py`
- Runtime pipeline: `backend/app/services/processing/stages.py`
- Capability manifest: `backend/app/services/rules/capability_manifest.py`
- Coverage audit: `backend/app/services/rules/coverage_audit.py`
- API schema/route: `backend/app/schemas/rule_coverage.py`, `backend/app/api/analyses.py`
- Main integration test: `backend/tests/test_m8_pipeline_integration.py`

## Safety notes

- The local provider is development-only and blocked when `APP_ENV=production`.
- Fake provider is test-only and blocked in production.
- Never add a threshold or institutional policy absent from the controlled KB.
- Never convert unsupported implementation into academic Not Verified.
- Do not modify `knowledge_base/source/` without a separately reviewed KB change.

## Commit after verification

```powershell
git add -A
git commit -m "feat: implement M6-M9 governed hybrid evaluation"
git push -u origin m6-m9-governed-semantic-evaluation
```

Merge to `main` only after backend/frontend/static/manual verification passes.
