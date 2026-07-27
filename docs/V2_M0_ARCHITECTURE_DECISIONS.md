# Version 2 Milestone 0 — Architecture and Governance Decisions

**Target:** `v2.0.0-arabic-pilot`  
**Status:** frozen for the controlled pilot

## ADR-01 — Faculty authentication

Version 2 uses first-party Faculty Member accounts for the pilot:

- normalized email + password registration;
- Argon2id password hashing through `argon2-cffi`;
- signed short-lived bearer access tokens;
- token-version revocation on logout or password reset;
- single-use, random password-reset tokens stored only as SHA-256 hashes;
- SMTP delivery in staging/production;
- one application role: `Faculty Member`.

The Version 1 `X-Dev-User-Email` trust boundary is removed from runtime code. Test fixtures use signed test tokens and can provision fixture identities only when `APP_ENV=test`.

## ADR-02 — Ownership and non-disclosure

`analyses.user_id` remains the ownership root. Files, extraction-review revisions, evidence, findings, and reports inherit ownership through the analysis. Every protected endpoint must resolve the current verified user and return the same owner-safe `404` for a missing resource and a resource owned by another user.

The frontend never supplies an owner ID when creating an analysis. The backend derives ownership from the authenticated account.

## ADR-03 — Password reset

Password reset requests always return the same public message to avoid account enumeration. A valid request creates a single-use token with a configurable expiry. Staging and production fail startup unless SMTP and a strong secret are configured. Development/test may return a debug token to make local verification possible; production never does.

## ADR-04 — Concurrent analyses

Background jobs continue receiving only `analysis_id` and opening a separate database session. They do not depend on browser session state. Atomic state claims and existing uniqueness constraints remain the concurrency boundary. Cross-user isolation applies before a job is scheduled.

## ADR-05 — Arabic/OCR acceptance boundary

The Arabic pilot will claim support only for the reviewed acceptance fixtures, not every possible PDF. Direct extraction is attempted first; OCR is a page-level fallback. Arabic/English OCR must preserve page number, geometry, hierarchy, marks, and extraction confidence. Low-confidence content pauses at Extraction Review and is never silently treated as reliable source evidence.

## ADR-06 — Adaptive Course Specification scope

The pilot supports TP-153 plus at least two materially different layout families:

1. section-heading layouts;
2. table-led layouts;
3. reordered/bilingual variants of those families.

The user-facing term is `Course Specification / توصيف المقرر`. The parser may propose source-faithful candidates, but it must not create missing CLOs, topics, assessment percentages, or institutional requirements.

## ADR-07 — RULE015 supporting-material legibility

RULE015 may use only measurable evidence such as:

- asset exists and is not blank;
- crop completeness;
- effective resolution;
- contrast/readability indicators;
- OCR confidence for text-bearing assets.

Insufficient or ambiguous evidence produces `Not Verified`. No general visual-quality opinion or invented institutional threshold is allowed.

## ADR-08 — RULE017 visible marks

RULE017 detects marks at question and sub-question level and records evidence. A negative academic finding is permitted only where the governed requirement establishes that the marks must be visible. Otherwise the platform may show descriptive completeness information without changing the score.

## ADR-09 — RULE020 exam identification

The parser may detect course title, course code, exam type, total marks, duration, date, and term when present. Mandatory-field judgments must come from the governed knowledge base. Missing fields not governed as mandatory remain descriptive and do not create an invented failure.

## ADR-10 — Question-type analytics

Question type is a derived classification, not source evidence. It must be stored separately from the immutable source-faithful Extraction Review snapshot. A faculty correction is a human override on the derived classification. Type concentration is advisory and never changes the Overall Exam Quality Score without an approved policy.

## Acceptance fixture inventory

The later milestones must include at least:

- digital English exam;
- digital Arabic exam;
- scanned Arabic exam;
- mixed Arabic/English exam with code;
- TP-153;
- two additional Course Specification layouts;
- referenced figure present/missing/ambiguous;
- readable/unreadable supporting material;
- visible/partial/missing marks;
- complete/incomplete identification;
- valid/broken cross-references;
- MCQ-heavy, essay-heavy, and mixed-type exams;
- two concurrent users and cross-user URL attempts;
- Arabic and English reports.
