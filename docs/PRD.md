# Product Requirements Document

## Product Vision

Develop an AI-powered platform that helps academic users evaluate and improve the quality of Midterm and Final examinations for computing courses through consistent, evidence-based analysis.

The platform uses:

- the uploaded examination PDF;
- the uploaded populated TP-153 Course Specification; and
- a controlled, versioned knowledge base.

The platform supports one evidence-based analysis workflow. Both the examination PDF and the
populated TP-153 are mandatory, and analysis does not start until both files are uploaded and
pass validation.

---

## Primary User

- Faculty Member

Version 1 is intentionally scoped to Faculty Members only. It does not include Course Coordinator, Quality Officer, Administrator, or approval-workflow functionality.

---

## Evaluation Scope

Required documents (both mandatory):

- Midterm or Final examination PDF.
- Populated TP-153 Course Specification.

Evaluation scope:

- CLO Alignment
- CLO Coverage
- Topic Alignment
- Topic Coverage
- Assessment-Method Consistency
- Question Clarity
- Question Completeness
- Marks and Total Validation
- Numbering and Structure
- Instructions
- Supporting Materials
- Cross-References
- Evidence Traceability
- Recommendations
- Overall Score Calculation

Displayed score:

`Overall Exam Quality Score`

The platform never generates or infers missing:

- CLOs
- Topics
- Assessment Methods
- Learning Activities
- Contact Hours
- Assessment Percentages

When required evidence for a dimension is missing, unreadable, ambiguous, or insufficient within
the uploaded exam or TP-153, that dimension receives the academic status `Not Verified` and is
excluded from score calculation.

---

## Primary Journey

1. Create a new analysis.
2. Upload the examination PDF and the populated TP-153.
3. Validate uploaded documents.
4. Process the analysis.
5. Review results.
6. Download the report.
7. Create a linked reanalysis for a revised examination when needed.

When either the examination PDF or the populated TP-153 is missing or fails validation, the
platform:

- prevents analysis execution;
- informs the user which required document is missing or invalid;
- provides a blank TP-153 template; and
- provides a TP-153 completion guide.

---

## Results Interface

Every completed analysis is presented through six primary sections.

1. Overview
2. Questions
3. Alignment & Coverage
4. Marks & Structure
5. Findings & Recommendations
6. Report

The **Alignment & Coverage** section presents:

- CLO Alignment
- CLO Coverage
- Topic Alignment
- Topic Coverage

The **Findings & Recommendations** section presents:

- Findings
- Recommendations
- Missing Evidence
- Evidence Traceability

The interface provides access to evidence, mappings, findings, recommendations, scoring information, and downloadable reports through a consistent navigation structure.

---

## Must-Have Capabilities

- Secure PDF upload and validation.
- Examination PDF required for every analysis.
- Populated TP-153 required for every analysis.
- Digital PDF extraction.
- OCR support for scanned documents.
- Question extraction.
- Marks extraction.
- Instruction extraction.
- Table extraction.
- Image extraction.
- Diagram extraction.
- Code extraction.
- Numbering extraction.
- Layout extraction.
- TP-153 extraction.
- Versioned knowledge-base retrieval.
- Deterministic rule evaluation.
- Semantic AI evaluation.
- Five-status evaluation model.
- Deterministic score calculation.
- Evidence traceability.
- Downloadable reports.
- Separate reporting of `Not Verified` results.
- Analysis history.
- Linked reanalysis for revised examinations.
- Six-section results interface.
- Downloadable blank TP-153 template.
- Downloadable TP-153 completion guide.
- Required TP-153 sections reference.

---

## TP-153 Assistance

The upload interface provides:

- Download Blank TP-153 Template
- Download TP-153 Completion Guide
- View Required TP-153 Sections

The template is presented as a reference document.

Version 1 accepts only official TP-153 evidence and does not allow manual entry of CLOs or course topics.

---

## Scoring Requirements

The platform uses the following scoring model:

- `Satisfied` = 1.0
- `Partially Satisfied` = 0.5
- `Not Satisfied` = 0.0
- `Not Verified` = Excluded
- `Not Applicable` = Excluded

When no verified applicable rules exist, the platform displays:

`Insufficient Evidence`

Displayed score label:

`Overall Exam Quality Score`

---

## Acceptance Criteria

- Every analysis requires a valid examination PDF and a valid populated TP-153.
- Analysis does not start until both required documents are uploaded and pass validation.
- Dimensions receive the status `Not Verified` when required evidence is missing, unreadable, ambiguous, or insufficient within the uploaded exam or TP-153.
- Missing or insufficient evidence never produces the status `Not Satisfied`.
- Course-specific information is never inferred when official evidence is unavailable.
- Every reported finding references supporting evidence or a documented missing-evidence record.
- Every revised examination produces a new linked analysis without replacing previous results.

---

## Exclusions

Version 1 does not include:

- Course Coordinator or Quality Officer interfaces.
- Limited Exam Review or any exam-only analysis workflow.
- Analysis-mode selection.

- Student answer analysis.
- Student grade analysis.
- Grade distribution analysis.
- Examination difficulty estimation.
- Bloom's Taxonomy classification.
- Student performance prediction.
- Faculty performance evaluation.
- Teaching quality evaluation.
- Complete accreditation evaluation.
- Automatic document modification.
- Automatic reconstruction of missing TP-153 information.
- Manual CLO or topic entry as official evidence.
- Approval workflows.

---

## Product Success Metrics

- Every reported finding is supported by valid evidence.
- Score calculations pass deterministic validation.
- Users can locate the evidence supporting every finding.
- Extraction failures are reported without producing unsupported academic conclusions.
- Every analysis requires both the examination PDF and the populated TP-153.
- Dimensions dependent on TP-153 evidence are correctly reported as `Not Verified` when that evidence is genuinely missing, unreadable, ambiguous, or insufficient within the uploaded TP-153.
- Revised examinations generate linked analyses without overwriting previous results.