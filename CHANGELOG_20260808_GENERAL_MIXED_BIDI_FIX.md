# General mixed Arabic/English display fix — 2026-08-08

## Problem
Some Arabic MCQ question text was rendered with an LTR base direction because the source-faithful text began with a Latin question identifier such as `Q 1.1`. Other Arabic/English mixed questions that began directly with Arabic rendered correctly.

## Fix
- Added a language-agnostic `displayQuestionText` helper.
- The helper removes only the already-known leading question identifier for display, tolerating whitespace differences introduced by PDF text extraction.
- Extraction Review question summaries and editors now determine bidi direction from the actual question sentence.
- Results question text uses the same display helper and bidi treatment.
- Canonical extracted text, evidence, technical terms, and analysis inputs are not rewritten by this UI fix.

## Scope
Frontend only. No database migration. No translation model. No backend extraction change.
