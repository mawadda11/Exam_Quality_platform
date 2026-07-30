# Controlled Pilot Acceptance Checklist

Use this checklist only with approved synthetic or non-confidential documents. Automated tests
support this review, but they do not replace the manual browser and PDF checks below.

## Test record

- Test date:
- Tester:
- Environment and build/commit:
- Browser, operating system, and display:
- Interface language(s):
- Exam fixture and SHA-256:
- Course Specification fixture and SHA-256:
- Result: Pass / Fail / Blocked
- Defect references:
- Notes:

## Prerequisite setup

- [ ] Use a pilot environment isolated from production and configured according to `.env.example`.
- [ ] Configure a strong authentication secret and SMTP for any shared pilot environment.
- [ ] Confirm PostgreSQL, the backend, and the frontend are healthy before testing.
- [ ] Confirm the database is at the current Alembic head.
- [ ] Create a new Faculty Member account; do not reuse another tester's account.
- [ ] Use only synthetic or explicitly approved, de-identified PDFs.
- [ ] Record fixture filenames and checksums. Never add confidential institutional exams or student
      information to the repository.
- [ ] Keep the browser developer console free of document content, secrets, stack traces, local
      paths, and internal storage identifiers.

For the governed digital scenario, use the checksum-pinned fixtures:

- `backend/tests/fixtures/batch4/01_Batch4_Test_Exam.pdf`
  (`8442dbd868d7261e4d8fd5eaec4002c7c0876cb672cac153c3e3e1f6758df956`)
- `backend/tests/fixtures/batch4/02_Batch4_Mixed_Course_Specification.pdf`
  (`c1fa24f887ac62424ebc69d21fb076218296742e0ada88ad248b3efd0d2c2f0f`)

## Scenario A — Digital PDF

1. [ ] Register, sign in, and create a Final analysis for the synthetic course.
2. [ ] Upload both checksum-pinned PDFs. Confirm validation succeeds and the original filenames are
       displayed without exposing storage paths.
3. [ ] Start processing. Confirm progress survives a browser refresh and pauses at Extraction
       Review.
4. [ ] Verify seven main questions and two independently scorable children under Q1.
5. [ ] Verify the structural Q1 parent is not counted as an evaluated question and no parent/child
       marks are double-counted.
6. [ ] Verify four CLOs, seven topics, four assessment methods, and six physical supporting
       materials.
7. [ ] Verify logical Arabic/mixed captions are editable while original extracted wording remains
       available for audit.
8. [ ] Save a review correction, reopen the review, and confirm the revision is preserved without
       changing the original machine record.
9. [ ] Confirm the review revision and allow governed analysis to complete.
10. [ ] Reopen the saved analysis from Analyses and inspect every results section.
11. [ ] Generate English and Arabic reports, preview both, and download both protected PDFs.
12. [ ] Confirm the analysis and both report artifacts are visible only to their owner.

Expected governed results:

- [ ] Declared total = 40 and calculated total = 40.
- [ ] RULE018 = Satisfied.
- [ ] Exactly six materials: four figures, one academic table, and one code block.
- [ ] Q2 → Figure 1 is Linked.
- [ ] Q3 → Table 1 is Linked.
- [ ] Q4 → Code 1 is Linked.
- [ ] Q5 → Figure 5 is Missing.
- [ ] Q6 → both Figure 2 candidates are retained as Ambiguous and unresolved.
- [ ] Q7 → nearby unlabeled diagram remains proximity-only, advisory, and unresolved.

## Scenario B — OCR document

Use the existing synthetic scanned fixture produced by
`backend/tests/pdf_fixtures.py::build_scanned_looking_exam_pdf`; if a browser-test PDF is generated
from it, keep it local and untracked. Pair it with an approved synthetic populated Course
Specification.

1. [ ] Upload the scanned exam and Course Specification, then start processing.
2. [ ] Confirm OCR is used for the image-only exam page and processing reaches Extraction Review.
3. [ ] Compare extracted questions, marks, wording, confidence warnings, and page provenance with
       the visible scan.
4. [ ] Correct one genuine OCR transcription issue and confirm the original machine extraction
       remains available.
5. [ ] Confirm the revision and complete governed analysis.
6. [ ] Generate, preview, and download at least one report; repeat in the second language if the
       presentation is being accepted for release.
7. [ ] Record all OCR omissions or substitutions. Do not silently reinterpret unreliable text.

Expected outcome: recoverable OCR evidence can proceed after faculty review; unreliable or missing
evidence remains Not Verified. OCR accuracy is not assumed from upload success.

## Scenario C — Incomplete evidence

Use the existing synthetic incomplete Course Specification builders in
`backend/tests/tp153_pdf_fixtures.py`. Use a valid synthetic PDF for any readable-but-incomplete
exam case; corrupt, encrypted, unsupported, or missing required uploads must be rejected before
analysis.

1. [ ] Attempt to continue with one required document missing. Confirm analysis cannot start.
2. [ ] Verify unsupported, oversized, corrupted, and inaccessible encrypted files receive concise,
       safe validation errors.
3. [ ] Run an approved synthetic case with missing Course Specification sections or unreliable exam
       evidence.
4. [ ] Confirm missing sections do not create fabricated CLOs, topics, assessment methods, mappings,
       or evidence.
5. [ ] Confirm unavailable or unreliable checks show Not Verified rather than a negative academic
       judgment.
6. [ ] Confirm a zero verified/applicable denominator displays Insufficient Evidence, never 0%.
7. [ ] Confirm the incomplete analysis remains in Analyses but is absent from the Reports Library.
8. [ ] Retry only when the interface identifies a recoverable failure.

## Cross-page and report consistency

Compare the same completed analysis across Overview, Questions, Alignment & Coverage, Marks &
Structure, Materials & References, Findings & Recommendations, Reports Library, and both PDFs:

- [ ] Declared marks total and calculated marks total match.
- [ ] Overall score and denominator match; Insufficient Evidence is preserved where applicable.
- [ ] Academic statuses and finding counts match.
- [ ] CLO and topic relationship counts and coverage match.
- [ ] Material-reference resolutions match the governed expectations above.
- [ ] Finding explanations, recommendations, identifiers, and source excerpts remain traceable.
- [ ] No page independently recalculates or relabels an authoritative result.

## English LTR and Arabic RTL visual checks

Repeat critical pages and both report languages in each configuration:

- [ ] Desktop width: sidebar, page hierarchy, cards, tabs, tables, forms, badges, and dialogs align.
- [ ] Tablet width: navigation and two-column/card layouts reflow without clipping.
- [ ] 320px width: one-column content, stacked actions, usable controls, and no page-level horizontal
      overflow.
- [ ] 200% browser zoom: no hidden controls, overlapping text, or loss of content.
- [ ] English uses LTR flow; Arabic uses RTL flow with logical navigation/icon placement.
- [ ] Arabic letters shape correctly; mixed Arabic/English captions, numbers, codes, and identifiers
      remain readable and isolated.
- [ ] Tables expose horizontal scrolling only within their own responsive container.
- [ ] Status meaning is visible as text and is not conveyed by color alone.
- [ ] PDF headings, tables, badges, excerpts, page breaks, and footers are not clipped.
- [ ] Arabic PDF page direction and shaping are correct; English source excerpts are not reversed.

## Accessibility and interaction checks

- [ ] Complete the workflow by keyboard, including skip link, sidebar/mobile navigation, tabs,
      forms, dialogs, report actions, and FAQ accordions.
- [ ] Focus is visible and follows a logical order in both directions.
- [ ] Every form control has an accessible label; validation errors are associated with the
      relevant control.
- [ ] Pages use one clear level-one heading and semantic subordinate headings.
- [ ] Dialog focus is trapped while open and returns to the invoking control when closed.
- [ ] Tables have associated captions/column headings and remain understandable to a screen reader.
- [ ] Loading, progress, success, and error states are announced.
- [ ] Mobile navigation is operable with keyboard and Escape and returns focus to its trigger.

## Failure and recovery checks

- [ ] Unsupported and oversized files are rejected without leaving a false uploaded record.
- [ ] Missing required documents prevent processing.
- [ ] OCR, extraction, analysis, and report-generation failures show safe, recoverable messages.
- [ ] Retry controls appear only for supported recovery paths and prevent duplicate submissions.
- [ ] Expired sessions return the user to authentication and clear the invalid local session.
- [ ] Unauthorized and cross-owner direct URLs return owner-safe 404 responses.
- [ ] Refresh during upload selection explains that unsaved local selections must be chosen again.
- [ ] Refresh during processing resumes authoritative progress polling.
- [ ] No response or UI exposes a traceback, secret, local path, storage key, or document content in
      client logs.

## Final acceptance

- Automated gate result:
- Manual English result: Pass / Fail / Blocked
- Manual Arabic result: Pass / Fail / Blocked
- PDF comparison result: Pass / Fail / Blocked
- Security/ownership result: Pass / Fail / Blocked
- Open critical/high defects:
- Pilot decision: Proceed / Proceed with conditions / Do not proceed
- Approver and date:

