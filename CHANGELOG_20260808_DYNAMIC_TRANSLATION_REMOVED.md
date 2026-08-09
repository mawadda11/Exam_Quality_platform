# Dynamic Arabic Translation Removed — 2026-08-08

- Removed the local OPUS-MT/Transformers translation path and its heavyweight dependencies.
- Gemini is not asked to translate semantic findings or relationship reasons.
- Arabic remains available for static UI labels, statuses, controlled recommendation text, and navigation.
- Dynamic academic reasoning and relationship explanations remain in their validated source language (currently English) to avoid meaning drift.
- Existing optional Arabic fields are retained only for backward compatibility with previously stored analyses; the UI no longer prefers or displays them.
- No database migration is required.
