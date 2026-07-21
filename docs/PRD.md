# Product Requirements Document

## Product vision
Help academic users review and improve computing-course Midterm and Final exams through consistent, evidence-based analysis against the uploaded TP-153 and a controlled knowledge base.

## Primary users
Faculty Member, Course Coordinator, and Quality Officer.

## Primary journey
1. Create analysis metadata.
2. Upload exam PDF and populated TP-153.
3. Validate readability and required content.
4. Process files asynchronously.
5. Review score/statuses, mappings, findings, evidence, and recommendations.
6. Download report.
7. Upload a revised exam and create a linked reanalysis.

## Must-have capabilities
- Safe PDF upload and validation.
- Digital PDF and scanned-document extraction adapters.
- Question, marks, instruction, table, image, diagram, code, numbering, and layout records.
- TP-153 CLO, topic, assessment-method, activity, hours, and percentage records where available.
- Versioned KB ingestion and filtered retrieval.
- Deterministic and semantic rule execution.
- Five-status output and exact scoring policy.
- Evidence traceability and downloadable report.
- Analysis history and revised-exam reanalysis.

## Exclusions
No student answers, grades, difficulty estimation, Bloom classification, faculty evaluation, complete accreditation evaluation, document modification, or approval/rejection workflow.

## Product success metrics
- Every released finding passes schema and evidence-link validation.
- Deterministic score tests cover all denominator cases.
- Users can locate source evidence for every detailed finding.
- Extraction failure is visible and does not become an unsupported academic judgment.
- A revised exam produces a new linked analysis without overwriting the previous result.
