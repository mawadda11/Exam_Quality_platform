# Marks Text Cleanup Fix — 2026-08-05

## Problem fixed
PDF reading order could place a right-aligned marks badge such as `[3 marks]` in the middle of a question sentence. The numeric mark was extracted correctly, but the same annotation remained inside the editable question text.

Example before:

`Q4(b) Write an SQL query to display each student name with the [3 marks] titles of courses...`

Example after:

`Q4(b) Write an SQL query to display each student name with the titles of courses...`

The mark remains structured as `3.0` in the Marks field and in marks evidence.

## Implemented behavior
- Removes explicit English marks annotations from editable question text regardless of where PDF reading order inserts them:
  - `[3 marks]`, `(3 marks)`, `[2 points]`, `(2 pts)`
- Removes Arabic mark annotations such as `(٣ درجات)`.
- Removes parent heading marks such as `(9 marks)` while preserving the heading.
- Preserves technical numbers that are not marks, including `GF (19)`, `Figure (3)`, `AES-256`, and similar content.
- Keeps marks as structured data and traceable marks evidence.
- Restricts legacy bare `[5]` cleanup to the end of a stem to avoid deleting code/index notation inside a question.

## Verification
- 93 targeted extraction and scoring tests passed.
- The actual synthetic Saudi database exam was extracted and verified:
  - `Q4(a)` text no longer contains `[3 marks]`; Marks = 3.
  - `Q4(b)` text no longer contains an inserted `[3 marks]`; Marks = 3.
  - `Q4(c)` text no longer contains an inserted `[3 marks]`; Marks = 3.
  - Parent `Q4` text no longer contains `(9 marks)`; Marks = 9.
- No database migration was added.
- Gemini was not used.
