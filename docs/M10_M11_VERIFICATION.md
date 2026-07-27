# Version 1.0.0 Verification Record

## Owner workstation environment

- Windows 10
- Python 3.13.14 (project contract: 3.12+)
- Node.js 24.18.0
- Docker 29.6.2
- Docker Compose 5.3.1
- Test documents: synthetic/non-private only

## Passed checks before the final UX refinement

### Backend

- `ruff check .` — passed.
- `ruff format --check .` — passed after formatting the two identified files.
- `mypy app` — passed for 107 source files.
- `pytest tests/test_m10_m11_release_acceptance.py -q` — passed.
- `pytest` — **526 passed**, with one third-party Starlette/httpx deprecation warning.

The warning is not a test failure. It should be handled through a separately tested dependency
maintenance change rather than an unreviewed package substitution.

### Frontend

- `npm run lint` — passed.
- `npm run typecheck` — passed.
- `npm test -- --run` — **156 passed across 38 test files** before the final UX refinement.
- `npm run build` — passed with Vite production output.
- `npm audit fix` — applied the non-breaking available remediation.
- `npm audit` — two high-severity React Router advisory entries remain. npm proposes
  `npm audit fix --force` with a breaking version change; do not apply it without a dedicated
  compatibility and security maintenance task.

### Knowledge base

- The 11 controlled source workbooks were not modified.
- The validator-normalized manifest was restored to the committed version after validation.
- No rule or criterion was deleted to make implementation coverage appear higher.

### Manual workflow

The owner successfully started and reviewed the application locally with Docker and completed more
than one synthetic analysis. That review identified the final Version 1 UX refinement: platform
capability counts and the full 21-rule table should not dominate each individual exam result.

## Final UX refinement verification required

The final refinement adds frontend tests and changes the Overview, navigation, and the new
**What the Platform Evaluates** page. Before the final commit and push, rerun:

```powershell
cd frontend
npm run lint
npm run typecheck
npm test -- --run
npm run build
cd ..
```

Then run the full repository gate in `docs/OWNER_FINAL_CHECKLIST.md` and manually confirm:

- no arithmetic score equation is visible in Overview;
- no full 21-rule capability table is visible in Overview;
- only analysis-specific completion information is shown there;
- platform capability is available on the separate scope page;
- the generated PDF retains the detailed audit information;
- no private upload, `.env`, report, or credential is staged.
