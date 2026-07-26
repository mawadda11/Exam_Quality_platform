# Software Requirements Specification

## Functional requirements
FR-001 Create a new analysis for a computing course.
FR-002 Select Midterm or Final.
FR-003 Upload one exam PDF and one populated TP-153.
FR-004 Validate file type, signature, size, readability, and availability.
FR-005 Extract page-aware exam content from digital PDFs.
FR-006 invoke OCR for scanned/image pages through an adapter.
FR-007 Extract question hierarchy, marks, declared total, instructions, assets, code, and structure.
FR-008 Extract CLOs, topics, assessment methods, activities, hours, and percentages from TP-153.
FR-009 Create immutable source evidence records.
FR-010 Retrieve relevant versioned KB records.
FR-011 Execute deterministic and semantic evaluation rules.
FR-012 Return exactly one approved academic status per executed rule.
FR-013 Generate evidence-based explanation and applicable recommendation.
FR-014 Calculate score according to the approved policy.
FR-015 Display progress, status counts, score, mappings, findings, missing evidence, and recommendations.
FR-016 Generate a downloadable report.
FR-017 Store analysis history.
FR-018 Create a reanalysis linked to its predecessor.
FR-019 Create a durable reviewable extraction before semantic analysis.
FR-020 Permit only source-faithful transcription correction, restoration, false-positive exclusion,
and extraction confirmation during review.
FR-021 Prohibit AI analysis before extraction confirmation.
FR-022 Keep explicit source mappings separate from AI-derived semantic relationships.
FR-023 Require derived relationships to reference existing confirmed question and target
identifiers and compatible evidence.
FR-024 Return backend-derived categorical semantic confidence: High, Medium, or Low.
FR-025 Require Low semantic confidence to produce Not Verified and exclusion from the score
denominator.
FR-026 Present Decision, Evidence Used, Concise Reasoning, categorical Confidence, and an optional
controlled Recommendation for semantic findings.
FR-027 Keep coverage, marks totals, numbering outcomes, and score aggregation deterministic.
FR-028 Prohibit manual or AI creation of official CLOs, topics, assessment records, mappings,
institutional policies, and rule thresholds.
FR-029 Account for every governed exam-facing rule separately from academic status and expose any
supported rule that failed to run as an operational coverage gap.

FR-019 through FR-028 are design-authorized in M1. M2 implements the
revision/categorical-confidence persistence and strict internal schema foundation. M3 implements
the initial revision, `review_ready` pause, and no-pre-confirmation-processing guard. M4-M5
implement source-faithful review editing, immutable saves, exact confirmation, guarded
continuation, and the review workspace. M6-M9 implement the ten-rule semantic/hybrid runtime,
backend-derived categorical confidence, deterministic mapping coverage, and complete exam-facing
rule capability accounting. M10-M11 remain planned.

## Non-functional requirements
- Accuracy: unsupported claims are prohibited; insufficient evidence becomes Not Verified.
- Explainability: rule, evidence, explanation, and recommendation are available where applicable.
- Provenance: original machine extraction, reviewed source evidence, and derived semantic
  relationships remain distinguishable.
- Human review: review validates transcription only and never becomes an academic approval or
  course-authoring workflow.
- AI safety: model output is untrusted; no AI evaluation occurs before extraction confirmation.
- Confidence: semantic confidence is categorical, backend-derived, nonnumeric, and has no scoring
  weight.
- Security: ownership checks, upload validation, restricted storage, safe logging, and secrets management.
- Privacy: limited use, retention hooks, and secure-deletion capability.
- Performance: background jobs and progress polling.
- Maintainability: modular services and versioned contracts.
- Reliability: idempotent stages where practical, processing logs, and safe failure states.

## Status and scoring invariants
See `docs/SCORING_POLICY.md` and `docs/AI_GOVERNANCE.md`.

## Scope invariants

Conclusions are limited to the uploaded Exam and TP-153. The system must not claim program
accreditation, student attainment, learning achievement, faculty performance, teaching quality,
institutional compliance beyond uploaded evidence, or an official accreditation decision.

The unsupported RULE015, RULE017, RULE020, and the two-or-more-CLO branch of RULE006 remain
deferred until their missing governed criteria exist.
