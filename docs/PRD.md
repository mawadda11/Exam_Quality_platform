# Product Requirements Document

## Product Vision

Develop an AI-powered platform that helps academic users evaluate and improve the quality of Midterm and Final examinations for computing courses through consistent, evidence-based analysis.

The platform uses:

- the uploaded examination PDF;
- the uploaded populated TP-153 Course Specification; and
- a controlled, versioned knowledge base.

The platform supports one evidence-based analysis workflow. Both the examination PDF and the
populated TP-153 are mandatory. Extraction does not start until both files are uploaded and pass
validation, and AI analysis does not start until the extracted evidence is reviewed and confirmed.
The review-and-confirm workflow is design-authorized in M1 and planned for later implementation.

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
4. Extract source evidence.
5. Review source-faithful extraction.
6. Confirm the reviewed extraction.
7. Run deterministic checks and constrained semantic analysis.
8. Review results.
9. Download the report.
10. Create a linked reanalysis for a revised examination when needed.

Extraction Review is not a course-authoring or mapping workflow. It may correct an existing
transcription, restore the original machine extraction, exclude a false positive, and confirm the
reviewed extraction. It may not create official CLOs, topics, assessment records, question-to-CLO
mappings, question-to-topic mappings, institutional requirements, or AI-generated source records.

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
- Source-faithful Extraction Review and explicit confirmation before AI analysis.
- Clear separation of explicit source mappings from AI-derived semantic relationships.
- Categorical semantic confidence (`High`, `Medium`, `Low`) derived by the backend.
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
It also does not allow manual creation of official assessment records or question-to-CLO/topic
mappings. AI-derived relationships are analysis outputs, not official TP-153 evidence.

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
- No semantic AI evaluator runs before extraction confirmation.
- An AI-derived relationship references only confirmed source records, is clearly labeled as
  derived or AI-assisted, and never overwrites source evidence.
- Low semantic confidence produces `Not Verified` and is excluded from score calculation.
- Confidence never changes the approved score value of a verified academic status.
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
- Manual assessment-record or question-to-CLO/topic mapping creation as official evidence.
- AI-generated source facts or official mappings.
- Approval workflows.

---

## Academic and Institutional Scope

The platform evaluates only the uploaded examination evidence against the uploaded TP-153 and the
controlled KB. It is a decision-support tool and does not establish:

- full program accreditation;
- student attainment or learning achievement;
- institutional compliance beyond the uploaded evidence;
- student, faculty, or teaching performance; or
- an official accreditation, approval, or rejection decision.

Semantic confidence is categorical only. It is not a percentage, severity, priority, readiness
label, quality score, or scoring weight. Existing numeric OCR and extraction confidence remain
separate technical metadata.

---

## Product Success Metrics

- Every reported finding is supported by valid evidence.
- Score calculations pass deterministic validation.
- Users can locate the evidence supporting every finding.
- Extraction failures are reported without producing unsupported academic conclusions.
- Every analysis requires both the examination PDF and the populated TP-153.
- Dimensions dependent on TP-153 evidence are correctly reported as `Not Verified` when that evidence is genuinely missing, unreadable, ambiguous, or insufficient within the uploaded TP-153.
- Revised examinations generate linked analyses without overwriting previous results.
