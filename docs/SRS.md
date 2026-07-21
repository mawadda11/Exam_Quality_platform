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

## Non-functional requirements
- Accuracy: unsupported claims are prohibited; insufficient evidence becomes Not Verified.
- Explainability: rule, evidence, explanation, and recommendation are available where applicable.
- Security: ownership checks, upload validation, restricted storage, safe logging, and secrets management.
- Privacy: limited use, retention hooks, and secure-deletion capability.
- Performance: background jobs and progress polling.
- Maintainability: modular services and versioned contracts.
- Reliability: idempotent stages where practical, processing logs, and safe failure states.

## Status and scoring invariants
See `docs/SCORING_POLICY.md` and `docs/AI_GOVERNANCE.md`.
