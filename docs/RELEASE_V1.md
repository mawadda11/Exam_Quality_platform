# AI Exam Quality Platform v1.0.0

## Release position

Version 1.0.0 is the first complete internal release of the approved Version 1 scope. M1-M11 are
included. The release supports the governed exam-analysis workflow, evidence review, traceable
findings, scoring, recommendations, reporting, and release validation.

This release is suitable for controlled local or internal evaluation. It is **not yet a public,
market-ready SaaS release** because authentication is still a temporary development identity,
production hosting/security operations are not complete, the interface is English-only, and Arabic
document analysis is not yet governed or release-tested.

## User-facing Version 1 refinement

The final v1.0.0 refinement separates two different questions:

1. What did the platform find in this uploaded exam?
2. What is the platform currently capable of evaluating?

Individual exam results now show only a concise, analysis-specific completion message. The full
platform capability catalogue is available from the separate **What the Platform Evaluates** page. Platform
limitations are not presented as failures of the uploaded exam.

The Overview score presentation also removes the arithmetic expression previously shown to users.
The interface keeps a concise explanation that the score is based on verified, applicable checks,
while the governed scoring policy remains documented for audit and maintenance.

The extraction review is limited to Questions, CLOs, and Topics. Assessment records and evidence
remain preserved internally for governed evaluation and traceability, but are not exposed as editable
review tabs. The generated report no longer lists the course-wide assessment percentage distribution
or platform implementation-coverage diagnostics.

The upload step states the currently supported document language in plain user-facing language,
without exposing release numbers or internal roadmap terminology in the workflow.

## Included capability scope

- 14 currently available exam-facing checks.
- 1 check with a defined conditional limitation.
- 6 documented checks planned or deferred until the required extraction method or academic policy
  is approved.

No knowledge-base source workbook or rule was deleted to make implementation coverage appear higher.
Unsupported/deferred capability remains documented and is excluded from academic scoring.

## Verification expectation

Before release, run the complete backend, frontend, knowledge-base, Docker, and manual workflow gates
in `docs/M10_M11_VERIFICATION.md` and `docs/OWNER_FINAL_CHECKLIST.md`.
