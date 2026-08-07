# Controlled Pilot — Known Limitations

This release candidate is intended only for a controlled pilot with approved Faculty Members,
synthetic or authorized documents, and active support. It is not a production deployment.

- The Exam Quality Analyzer supports evidence-based exam-quality review only. It does not evaluate
  the full academic program or establish program accreditation.
- Results depend on the completeness, readability, layout, and language quality of the uploaded
  exam and Course Specification.
- Missing, ambiguous, or unreliable evidence can produce Not Verified. This means the requirement
  could not be evaluated reliably; it is not a negative academic judgment.
- Suggested CLO, topic, and supporting-material relationships require Faculty Member review.
- OCR can omit or substitute text and may require manual correction in Extraction Review. Upload
  acceptance does not guarantee OCR accuracy.
- Original source wording and machine extraction are retained for traceability. Faculty corrections
  create review revisions and do not replace the original audit record.
- The analyzer does not issue accreditation, institutional approval, certification, pass, or fail
  decisions.
- Not every planned or policy-dependent check is enabled. The Methodology & Help page is the
  authoritative user-facing description of available and limited checks.
- Local/offline analysis remains the controlled-pilot default. Optional Gemini semantic analysis
  requires explicit environment configuration and runs only after the exact question revision is
  confirmed. Extraction Gemini is separately controlled and remains disabled by default.
- Report-generation failures are not a substitute for analysis results and may require a retry.
- The pilot does not include institutional SSO, automated retention/deletion, malware scanning,
  production rate limiting, or an institutional audit/approval workflow.
- Production infrastructure remains separate. TLS termination, managed secrets, private object
  storage, backups/restore testing, monitoring, alerting, capacity limits, penetration testing, and
  an approved retention policy require deployment-owner decisions before production use.
- Automated tests do not replace manual bilingual visual, browser, accessibility, OCR, and PDF
  acceptance.
# Extraction limitations added in v2.0.0-rc1

- Tesseract is the only OCR adapter currently shipped. The provider boundary
  is replaceable, but no additional OCR engine is implemented.
- OCR and deterministic/Gemini structure parsing cannot guarantee perfect
  transcription. Critical source disagreements require human resolution.
- PDF highlight geometry is normalized to PDF coordinates; unusually rotated,
  cropped, or non-standard page boxes may reduce overlay precision.
- Ambiguous A/B/C/D lines remain `unknown`/needs-review when context does not
  safely distinguish options from subquestions.
- Extraction Gemini is disabled by default. When enabled, the configured page
  cap is a quota guard; exceeding it creates a critical review blocker rather
  than silently claiming complete visual inspection.
- A validated Gemini structure cache contains private extraction data and must
  receive the same storage, access, backup, and retention controls as uploads.
- Physical artifact cleanup after analysis deletion is best effort. A locked
  file may require operational cleanup even though database records are gone.
## Controlled-pilot extraction scope

- The current pilot accepts digital, readable Midterm and Final PDFs for computing courses.
- Automatic question structuring is limited to multiple choice, True/False, short answer, essay,
  and simple textual fill-in-the-blank questions.
- Supporting context is intentionally narrow: only a figure, table, or code/schema block that a
  question explicitly calls for and that has one unambiguous physical candidate is proposed for
  review. Cover metadata tables, True/False answer grids, generic layout tables, logos, and
  decorative assets are excluded. The pilot does not interpret each table cell or infer missing
  diagram labels.
- Matching questions, unusual multi-column layouts, poor scans, handwriting, and questions that
  continue across pages may require manual visual review, region adjustment, type correction, or
  exclusion before confirmation.
- The editable transcription is a proposal. The full original PDF page and its question highlight are
  the review source of truth, and downstream analysis starts only after the Faculty Member confirms
  the review revision.
- A technical loading failure is not an academic failure. When confirmed question evidence cannot
  be loaded, the interface hides the numeric score and dependent academic results instead of
  presenting Not Satisfied conclusions.


## Question-preparation limitations

- The platform does not promise automatic understanding of every examination PDF layout. Before
  processing, the Faculty Member chooses assisted extraction, structured-template import, or manual
  visual preparation.
- Assisted PDF extraction is the primary workflow. Simplified structured import and pasted questions
  are fallback paths; this release does not directly parse arbitrary Word or Excel exam-authoring files.
- Assisted extraction remains a proposal. Wrapped questions, diagrams between stem fragments,
  repeated labels, and unusual reading order still require visual confirmation.
- Manual and structured modes intentionally create no automatic question facts. At least one
  source-faithful question must be reviewed before confirmation.
- Marks are extracted or entered only when visibly present in the exam. The platform never invents
  missing marks; mark-dependent checks may therefore be Not Verified or Not Applicable.
- Imported structured questions record the source page but do not invent a precise PDF rectangle. A
  reviewer may optionally adjust a visual region.
