# Version 2 Batch 3 — Complete Bilingual UX and Failure Recovery

## Scope

This batch combines the approved 3A–3D slices:

1. Arabic/English interface with runtime switching, Arabic first-visit default, account preference,
   local persistence, RTL/LTR document direction, localized dates, and mixed-direction isolation.
2. Safe failed-analysis recovery with stage-specific failure metadata and an owner-scoped retry API.
3. Explicit parent/container and child-question review presentation without scoring container rows as
   independent semantic items or silently excluding children.
4. Arabic/English report selection, localized static PDF presentation, responsive RTL/mobile layout,
   and accessibility-preserving controls.

## Backend additions

- Migration `0011_add_batch3_bilingual_retry_metadata.py`.
- Controlled `LanguageCode` and `ReportLanguage` enums.
- Account language preference endpoint and response fields.
- Durable safe failure stage, code, and retryability metadata.
- Atomic `POST /analyses/{id}/retry` recovery path using existing uploads and confirmed review.
- Language-aware immutable report generation and report metadata.

## Frontend additions

- Dependency-free centralized `I18nProvider` and `LanguageSwitcher`.
- Arabic translations for all user-visible application routes and feature workspaces.
- Automatic `<html lang>` and `dir` switching, Arabic default, and account/local preference sync.
- Stage-friendly processing labels, localized safe failure guidance, and Retry Analysis action.
- Hierarchical extraction-review rendering for container and child questions.
- Arabic/English report language selector and language-labelled report history.
- RTL and small-screen styling for navigation, review cards, results, tables, and controls.

## Governance boundaries preserved

- No scoring formula or knowledge-base rule changes.
- No translation or rewriting of uploaded source evidence.
- No hidden replacement of TP-153 CLOs, topics, or mappings.
- No exception traceback or provider secret exposed to clients.
- No admin or approval/rejection workflow added.
