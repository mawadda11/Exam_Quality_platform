# Exam Quality Analyzer — Stable Project Rules

- Approved visible names only: `محلل جودة الاختبارات` and `Exam Quality Analyzer`.
- Never expose prohibited or legacy branding in UI, metadata, email, or reports.
- Arabic is the anonymous first-visit default; authenticated preference wins after session load.
- Arabic UI is fully Arabic/RTL; English UI is fully English/LTR.
- Translate governed display content only in presentation/reporting layers. Never mutate source or database records.
- Keep uploaded text, TP-153 excerpts, direct evidence excerpts, filenames, course codes, identifiers, and technical snippets source-faithful and bidi-isolated.
- Preserve scoring, statuses, rules, requirements, evidence mapping, semantic behavior, extraction, retry contracts, review immutability, and question hierarchy.
- No administrator or approval workflow, external provider expansion, runtime downloads, secrets, or unrelated features.
- Keep the navy/teal academic design direction, accessible keyboard behavior, responsive layouts, and WCAG AA contrast.
- Add or update tests for every behavior change and run the full frontend/backend gates before completion.
- Preserve all existing local work. The user handles Git; do not stage, commit, push, change branches, or run destructive Git commands.
