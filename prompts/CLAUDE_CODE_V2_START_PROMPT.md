You are continuing the existing AI Exam Quality Platform repository for Version 2.

Do not edit code yet.

Read first:
1. CLAUDE.md
2. README.md
3. docs/PRD.md
4. docs/ARCHITECTURE.md
5. docs/V2_SCOPE_AND_IMPLEMENTATION_PLAN.md
6. current models, migrations, APIs, worker flow, extractors, rule manifest, reports, frontend routes, and tests

Target release: v2.0.0-arabic-pilot.
Timebox: less than one week.
Primary role: Faculty Member.

Frozen scope:
- Public faculty sign-up, sign-in, sign-out, password reset.
- Private dashboard and strict ownership for analyses, files, revisions, findings, and reports.
- Concurrent multi-user analysis.
- Arabic, English, and mixed-document analysis.
- Arabic/English OCR with page geometry and confidence.
- Adaptive Course Specification parsing for different layouts. TP-153 is one supported format, not the primary UI label.
- Complete RULE014, RULE015, RULE016, RULE017, RULE020, and RULE022.
- Question-type classification with High/Medium/Low confidence and review correction.
- Distribution by question count and marks; advisory only, not scored.
- Arabic/English primary UI, RTL/LTR, bilingual PDF reports.
- Simplified Methodology page.
- In-app completion/review/failure notifications.

Deferred:
- Exam-version comparison.
- Detailed user-facing change history.
- Admin and quality-reviewer roles.
- Institutional policy engine.
- Payments.
- Student-answer analysis and empirical difficulty.

Non-negotiable constraints:
- Preserve: confirmed evidence -> deterministic checks -> constrained semantic evaluation -> deterministic aggregation/scoring.
- No AI before exact extraction-review confirmation.
- Never invent CLOs, topics, percentages, policies, or thresholds.
- Keep exact academic statuses.
- Insufficient evidence must produce Not Verified where governed.
- Question-type concentration must not change the score.
- Do not change the knowledge-base source meaning.
- Do not commit secrets.
- Write tests for every feature.
- Preserve Version 1 behavior unless the new scope explicitly changes it.

Your first response must contain only:
A. Current-state audit.
B. Gap-to-scope matrix: supported / partial / missing / blocked.
C. Dependency-ordered implementation plan with migrations, APIs, workers, frontend, reports, tests, files, dependencies, and risks.
D. Honest feasibility assessment for the timebox and smallest compliant fallback for blockers.
E. Precise Milestone 1 plan.

Stop and wait for approval before editing any file.
