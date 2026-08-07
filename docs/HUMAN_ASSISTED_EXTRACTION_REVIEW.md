# Human-Assisted Question Preparation and Extraction Review

## Product principle

The Exam Quality Analyzer evaluates confirmed question evidence, not an unreviewed machine guess.
The immutable examination PDF remains the source of truth. Academic evaluation starts only after a
Faculty Member confirms the exact review revision.

## Three preparation paths

### Assisted PDF extraction

Use for clear digital exams. Native PDF extraction and the deterministic parser propose complete
question text, types, marks, options, hierarchy, and source regions. The proposal is never treated as
confirmed evidence. The reviewer corrects truncated text, boundaries, type, options, hierarchy, and
visible marks before saving.

A multiline question continues until the next explicit question marker. A table, figure, or diagram
inside the question remains visible in the source crop and does not by itself terminate the question.

### Structured question template

Use when dependable question facts are more important than automatic extraction. The Faculty Member
downloads an Excel-compatible CSV template, enters one complete source-faithful row per question,
and imports it in Extraction Review. The original PDF is still required and is used to verify every
row. Empty marks remain unknown. See `STRUCTURED_QUESTION_TEMPLATE.md`.

### Manual visual preparation

Use for irregular layouts. The reviewer selects the complete question region in the original PDF,
adds the visible question, and enters only the wording shown in the source. The backend rejects an
unanchored manual question.

## Review workflow

1. The authenticated exam PDF is rendered as protected page images.
2. The selected preparation mode supplies proposed or imported question records.
3. Each question shows its source page or cropped original region.
4. The reviewer corrects question number, complete text, supported type, visible marks, hierarchy,
   options, and region.
5. Missing questions may be added from a selected PDF region. Adjacent questions may be split or
   merged only in visual PDF modes.
6. Options appear only for multiple-choice questions. Simple blank details appear only for
   fill-in-the-blank questions.
7. The backend validates source anchoring, preserves original records, and creates immutable review
   revisions.
8. Confirmation permanently closes extraction editing for that analysis.
9. Only then may deterministic checks and an explicitly configured semantic provider run.

## Marks rule

The system reads a mark only when it is visibly written in the source. A reviewer may enter a mark
only to reproduce source content that extraction missed. No provider may invent a mark based on
question length, apparent difficulty, or question type.

## Deliberate limitations

- Complex tables, matching layouts, UML, diagrams, poor scans, and cross-page questions may need
  manual preparation.
- A visual crop preserves a table or figure without converting every cell, arrow, or missing label
  into canonical fields.
- The structured template records source pages and may omit exact geometry.
- No real Gemini request is required for question preparation, and automated tests never consume
  Gemini quota.
