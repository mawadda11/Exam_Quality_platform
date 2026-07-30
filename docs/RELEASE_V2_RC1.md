# Exam Quality Analyzer v2.0.0-rc1 — Controlled Pilot Release Notes

## Release status

`v2.0.0-rc1` is a release-candidate draft for controlled pilot evaluation. It is not a claim of
production readiness, accreditation validity, institutional approval, certification, or exam
pass/fail suitability.

## Included pilot capabilities

- A bilingual Arabic/English Faculty Member workflow with RTL/LTR presentation.
- Registration, login, logout, session restoration, password recovery, and authenticated
  owner-isolated analyses and reports.
- Digital PDF extraction and local OCR fallback for image-based exam pages.
- Extraction Review with source-faithful evidence, faculty corrections, append-only review
  revisions, provenance, and confirmation before governed analysis.
- Results for Overview, Questions, Alignment & Coverage, Marks & Structure, Materials & References,
  and Findings & Recommendations.
- Traceable academic statuses, evidence, explanations, and recommendations without changing the
  governed scoring policy.
- Structured figures, tables, code blocks, labels, captions, explicit references, ambiguity, and
  association provenance.
- Arabic and English PDF report generation, protected preview, and protected download.
- An owner-filtered Reports Library for generated and report-eligible completed analyses.
- A bilingual Methodology & Help experience describing workflow, status, score, evidence, privacy,
  and limitations. A revised exam is evaluated by creating a New Analysis; there is no separate
  reanalysis workflow in this release.

## Governed acceptance fixture

The checksum-pinned Batch 4 synthetic documents verify 40 declared and calculated marks, RULE018
Satisfied, six physical materials, three uniquely linked references, one missing reference, one
ambiguous duplicate label, and one proximity-only unresolved advisory. Structural parents are
excluded while independently scorable children are preserved.

## Verification

The release candidate must pass the complete backend, frontend, migration, repository, bilingual
manual, accessibility, responsive, and PDF checks in `docs/PILOT_ACCEPTANCE_CHECKLIST.md`. This
release does not maintain a separate manual pilot-results record document.

## Known limitations

See `docs/KNOWN_LIMITATIONS.md`. Important limits include evidence-quality dependence, faculty
review of suggested relationships, fallible OCR, no accreditation or approval decision, no external
language-model integration in this release, and separate unresolved production-infrastructure
requirements.

