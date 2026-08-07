# Question Preparation and Review Plan

## Goal

Make question preparation reliable without claiming universal automatic PDF understanding.
The governed academic analysis still starts only after a faculty member confirms an exact
review revision.

## Supported preparation modes

1. `assisted_pdf`
   - Keep deterministic PDF extraction as a proposal.
   - Preserve complete wrapped question text until the next detected question.
   - Keep figures/tables inside the visual question region without flattening them into editable text.
   - Faculty review remains mandatory.
2. `manual_pdf`
   - Extract the Course Specification and retain the exam PDF for visual review.
   - Do not create automatic questions.
   - Faculty members add each question by selecting a PDF region and entering source-faithful text.
3. `structured_template`
   - Extract the Course Specification and retain the exam PDF as the immutable reference.
   - Do not create automatic questions.
   - Faculty members import a controlled CSV question template, then review every imported row.

## Reliability rules

- Question text is source evidence, never a model-authored fact.
- Marks are extracted only when visibly written. Missing marks remain empty and are never invented.
- Gemini remains optional and runs only after extraction confirmation for governed semantic
  relationships when `AI_PROVIDER=gemini` is configured.
- Extraction Gemini remains separately optional and disabled by default.
- Technical or provider failures produce processing errors or `Not Verified`, never false academic
  judgments.
- Structured and manual questions must remain editable and traceable to the uploaded exam.

## UX changes

- Select a preparation mode before starting processing.
- Explain which mode is most reliable and what each mode requires.
- Show mode-specific guidance in Extraction Review.
- Provide a downloadable CSV template and browser-side CSV import for structured mode.
- Keep advanced extraction diagnostics collapsed.

## Verification

- API accepts and validates all three preparation modes.
- Manual and structured modes reach review with zero automatic questions and valid Course
  Specification records.
- CSV import creates questions/options/evidence without inventing marks.
- Assisted extraction preserves wrapped lines across vertical gaps and figures until the next
  question marker.
- Automated tests never call Gemini.
