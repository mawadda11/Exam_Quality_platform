# Version 2.0 Roadmap — Public, Bilingual, Production-Ready Platform

## Version goal

Version 2.0.0 turns the controlled Version 1 implementation into a deployable multi-user platform
with real authentication, Arabic/English use, Arabic exam analysis, production operations, and a
simpler end-user experience.

Version 2 is a major release because it changes identity, privacy boundaries, deployment,
localization, document processing, and operational support. It must not be treated as a small visual
update.

## Phase 1 — Production identity and access

### User capabilities

- Real sign-up and sign-in.
- Verified email address.
- Password reset and account recovery.
- Sign-out and session management.
- User profile and language preference.
- Optional institutional SSO after the basic identity flow is stable.

### Security and ownership

- Replace the temporary development identity with a production authentication provider or a
  carefully reviewed first-party implementation.
- Enforce owner/tenant isolation for analyses, uploads, findings, and reports.
- Add roles such as Faculty Member and Platform Administrator only where required.
- Add rate limiting, secure cookies/tokens, CSRF protection, brute-force protection, and audit logs.
- Add account deletion, data export, retention, and consent workflows.

### Acceptance requirement

No public deployment is allowed while the development identity is enabled or while one user can
access another user's files or analyses.

## Phase 2 — Production hosting and operations

- Deploy frontend, API, PostgreSQL, background workers, and vector storage to a supported cloud
  environment.
- Use managed secret storage; never deploy `.env` secrets in source control.
- Store uploaded documents and reports in private object storage with short-lived authorized links.
- Add TLS, domain configuration, security headers, malware/file scanning, backups, restore tests,
  monitoring, alerts, structured logs, and health checks.
- Separate development, staging, and production environments.
- Define capacity, upload-size, timeout, queue, and cost controls.
- Complete a privacy notice, terms of use, retention policy, and incident-response procedure.

## Phase 3 — Arabic and English interface

- Introduce a proper internationalization framework rather than duplicating strings in components.
- Add an Arabic/English language switch stored in the user profile and browser preference.
- Support RTL and LTR layout, navigation, tables, forms, dialogs, charts, and PDF reports.
- Localize dates, numbers, validation errors, emails, accessibility labels, and report templates.
- Use reviewed academic Arabic terminology for CLOs, assessment, evidence, findings, and statuses.
- Add visual regression and accessibility tests for both directions and languages.

## Phase 4 — Arabic exam and TP-153 analysis

- Add governed Arabic PDF text extraction and OCR evaluation.
- Support Arabic and mixed Arabic/English question numbering and hierarchy.
- Normalize Arabic punctuation, digits, ligatures, diacritics, and common OCR variants without
  changing source meaning.
- Add Arabic evidence schemas and bilingual semantic-evaluation prompts with the same strict output
  validation used in Version 1.
- Build a reviewed Arabic terminology/knowledge layer rather than translating source standards
  automatically at runtime.
- Add Arabic and bilingual synthetic fixtures plus reviewed real-world validation samples that are
  permitted for testing.
- Report language-specific extraction confidence separately from semantic confidence.

### Acceptance requirement

The interface language and the uploaded-document language are separate choices. A user may use the
Arabic interface with an English exam, the English interface with an Arabic exam, or analyze a mixed
exam when the extractor can preserve the source faithfully.

## Phase 5 — End-user experience simplification

- Replace programmer-facing wording with faculty-facing explanations.
- Keep implementation diagnostics in administrator or methodology views, not in the primary exam
  result.
- Add progressive disclosure: summary first, evidence and technical detail on request.
- Add guided upload checks, clear extraction-review instructions, contextual help, and plain-language
  recovery steps.
- Keep the score concise in the Overview. Put detailed scoring methodology in a dedicated methodology
  page and audit documentation.
- Conduct usability testing with faculty members before finalizing navigation and terminology.

## Phase 6 — Expand rule support without changing the knowledge base dishonestly

### Structured extraction candidates

Implement when layout evidence is reliable and persisted:

- RULE014 — Referenced Material Availability.
- RULE016 — Supporting Material Association.
- RULE022 — Resolvable Cross-References.

Required foundation includes figure/table/code extraction, page geometry, labels, explicit
references, and unique association logic.

### Policy-configurable candidates

Implement only after an approved institutional configuration exists:

- RULE017 — Visible Marks.
- RULE020 — Exam Identification.

The configuration must be versioned, auditable, institution-scoped, and included in each finding's
provenance.

### Governed visual-evaluation candidate

- RULE015 — Supporting Material Legibility.

Do not implement this rule using an arbitrary model opinion. First approve measurable visual-quality
criteria, validation data, failure handling, and a governed vision/OCR evaluator.

### Conditional rule improvement

- RULE006 — CLO Coverage Distribution.

Approve either a deterministic concentration threshold or a governed semantic rubric for the
multiple-CLO case before changing the current limitation.

## Phase 7 — Public release quality gates

- Threat model and security review.
- Dependency and container vulnerability gates.
- Privacy and data-protection review for target markets.
- Accessibility review for Arabic and English.
- Load, queue, storage, backup, and disaster-recovery testing.
- Cross-browser and mobile testing.
- Production AI-provider privacy and data-processing approval.
- Human-reviewed Arabic extraction and evaluation acceptance set.
- Staged pilot with controlled users before open registration.

## Recommended delivery sequence

1. V2.0-alpha: authentication, tenant isolation, staging deployment.
2. V2.0-beta: bilingual interface and Arabic extraction baseline.
3. V2.0-release-candidate: production operations, security, accessibility, and usability gates.
4. V2.0.0: controlled public launch after all release blockers are closed.

## Explicit non-goals until separately approved

- Student-answer or grade analysis.
- Automated accreditation decisions.
- Faculty performance evaluation.
- Invented institutional policies or rule thresholds.
- Hidden replacement of official CLOs, topics, or TP-153 evidence.
