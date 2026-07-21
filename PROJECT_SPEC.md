# AI Exam Quality Platform — Approved Project Specification

## Purpose
An AI-powered academic support platform that performs a structured, evidence-based first-level review of Midterm and Final examinations in computing courses by comparing an exam PDF with its populated TP-153 Course Specification.

## Users
- Faculty Member
- Course Coordinator
- Quality Officer

All roles use the same core analysis workflow. Version 1 has no Administrator role and no formal approval/rejection flow.

## Inputs
- Midterm or Final exam PDF, digital or scanned.
- Corresponding populated TP-153.

## Core outputs
- Overall score or `Insufficient Evidence`.
- Five-status distribution.
- Question-level findings and evidence.
- Question-to-CLO and question-to-topic mappings.
- Applicable CLO and topic coverage.
- Assessment-method consistency.
- Clarity, completeness, supporting-material, marks, totals, numbering, structure, instructions, and cross-reference findings.
- Actionable recommendations.
- Downloadable report.
- Immutable reanalysis history for revised exams.

## Status model
`Satisfied`, `Partially Satisfied`, `Not Satisfied`, `Not Verified`, `Not Applicable`.

## Scoring
Equal contribution:
- 1.0, 0.5, 0.0 for the first three statuses.
- Exclude Not Verified and Not Applicable.
- No denominator means `Insufficient Evidence`.

## Knowledge sources
- DP-100: relevant accreditation reference areas only.
- ABET CAC 2025–2026: supporting reference areas only.
- TP-153: course-specific evidence baseline, not an accreditation standard.
- Exam Quality Knowledge Base v1.0: eleven versioned Excel files.

## Analysis approach
Hybrid deterministic rules, OCR, layout/vision analysis, semantic AI, and RAG with typed structured output and evidence validation.

## Boundaries
The platform supports academic review; it does not issue accreditation decisions, evaluate a full program, analyze student answers or grades, estimate difficulty, classify Bloom levels, modify source documents, or approve/reject exams.
