# Version 2 Batch 2 Implementation Report

**Included milestones:** M2 + M3
**Branch target:** `develop/v2.0.0-arabic-pilot`

## Milestone 2 — Arabic/English extraction and OCR

Delivered:

- deterministic Arabic, English, mixed, and unknown text-language detection;
- conservative Arabic matching normalization while preserving original source text;
- Arabic-Indic and Eastern Arabic digit parsing;
- Arabic exam numbering such as `س١`, `السؤال الأول`, and Arabic sub-question letters;
- Arabic instructions, visible marks, and declared-total detection;
- direct-text quality gate before OCR fallback;
- Arabic+English Tesseract language-pack selection with safe English fallback;
- page geometry and extraction confidence preservation for direct and OCR paths;
- page-level extraction diagnostics and review recommendation;
- persisted document language, extraction method, confidence, and review flag on uploaded files;
- Docker installation of the Arabic Tesseract language pack.

The persisted question and evidence text remains the source line. Normalized text is used only for deterministic matching and number parsing.

## Milestone 3 — Adaptive Course Specification parser

Delivered:

- `AdaptiveCourseSpecificationExtractor` with backward-compatible `PdfPlumberTp153Extractor` name;
- section-heading, compact, and table-led layout families;
- reordered Arabic/English sections;
- Arabic, English, and mixed Course Specifications;
- CLO extraction with optional PLO reference;
- topic extraction with optional contact hours;
- assessment method, activity, and percentage extraction;
- Course Specification metadata extraction for course code, course name, department, program, and contact hours;
- source-faithful missing-section markers instead of invented records;
- confidence reduction for context-inferred table rows;
- persistence of extracted Course Specification fields as reviewable evidence;
- persisted parser layout on the uploaded Course Specification file.

## Database migration

Migration `0010_add_bilingual_extraction_metadata.py` adds the following nullable/diagnostic fields to `uploaded_files`:

- `detected_language`;
- `extraction_method`;
- `extraction_confidence`;
- `review_recommended`;
- `parser_layout`.

No existing Version 1 or Batch 1 source records are rewritten.

## Deliberately not included

- full Arabic/English frontend localization and RTL/LTR layout;
- Arabic PDF report generation;
- production cloud OCR provider;
- the six deferred rules;
- question-type classification;
- institution policy engine.

Those remain later milestones.
