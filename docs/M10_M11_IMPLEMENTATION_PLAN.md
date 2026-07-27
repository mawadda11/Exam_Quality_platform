# M10-M11 Implementation Plan

## Recovery state

- Repository source of truth: current `main` at `5f76d6a` (`feat: implement M6-M9 governed hybrid evaluation`).
- Working tree at recovery: clean.
- M1-M9: implemented and committed.
- M10-M11: implemented in this delivery. Verification evidence and environment-limited checks are recorded in `docs/M10_M11_VERIFICATION.md`.

## Non-negotiable boundaries

This work preserves `CLAUDE.md`, the PRD/SRS, the controlled knowledge base, the five academic statuses, deterministic scoring, the extraction-confirmation boundary, and all evidence/governance restrictions. It does not add Limited Exam Review, manual mappings, new academic thresholds, new rules, accreditation decisions, or production authentication/deployment assumptions.

## M10 - Presentation and report refinement

1. Present backend-derived semantic confidence (`High`, `Medium`, `Low`) as a categorical, nonnumeric contract.
2. Present concise governed semantic details: decision, reasoning, confidence basis, retrieved KB identifiers, and item judgments.
3. Present question-to-CLO and question-to-topic relationships from `RULE001`/`RULE007` as **AI-derived advisory relationships**, never as source TP-153 mappings.
4. Present runtime rule coverage and keep `evaluated`, `conditional_capability_gap`, `unsupported`, and `not_run` operationally separate from academic statuses.
5. Expand score-denominator transparency without changing the scoring formula.
6. Expand generated reports with semantic confidence/details, derived relationships, assessment source records, runtime coverage, evidence traceability, and denominator transparency.
7. Add focused backend/frontend tests for every presentation and report change.

## M11 - Integrated acceptance and release validation

1. Add an integrated API acceptance test covering upload, extraction pause, confirmation, governed evaluation, score, rule coverage, report generation/download, and owner isolation.
2. Run backend lint, formatting, typing, full tests, Python compilation, and controlled-KB validation.
3. Run frontend lint, typecheck, tests, and production build when the dependency registry is available; otherwise record the exact environmental blocker and provide mandatory Windows commands.
4. Remove local ignored uploads/build caches from the delivery archive while retaining `.gitkeep` files.
5. Update roadmap, traceability, API/frontend/test documentation, README, and durable M10-M11 handoff/verification reports.

## Planned file areas

- Backend report assembly/rendering and report API wiring.
- Frontend results data loader, overview, finding details, coverage panel, styles, and tests.
- Backend report and integrated acceptance tests.
- Project documentation and handoff artifacts.

## Completion gate

M10-M11 are complete only when the repository contains the implementation, focused tests, full verification evidence or explicit environment limitations, a clean handoff, and no secrets/private uploads in the delivery archive.
