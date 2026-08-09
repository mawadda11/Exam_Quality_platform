# Exam Quality Analyzer

**Current candidate: v2.0.0-rc1** — under verification for a controlled pilot.

Evidence-based Midterm and Final exam quality-analysis platform for Faculty Members. Deterministic aggregation and ten governed advisory semantic/hybrid evaluators produce traceable
findings; the faculty member retains final academic responsibility.


## Controlled pilot status

The current implementation provides the authenticated bilingual workflow, three governed
question-preparation paths, Extraction Review, governed results, Arabic/English PDF reports,
Reports Library, and Methodology & Help experience intended for the controlled pilot. The original
exam PDF remains the visual source of truth and every path pauses for exact-revision confirmation.
A revised exam is evaluated
by creating a New Analysis; there is no separate reanalysis workflow.

Before any pilot use, read:

- [Pilot acceptance checklist](docs/PILOT_ACCEPTANCE_CHECKLIST.md)
- [Known limitations](docs/KNOWN_LIMITATIONS.md)
- [v2.0.0-rc1 release-note draft](docs/RELEASE_V2_RC1.md)

This candidate is not a production deployment and does not issue accreditation, approval,
certification, or pass/fail decisions.

## Local development

With Docker (entire stack - frontend, backend, PostgreSQL, ChromaDB):
```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

Create a Faculty Member account from the registration page. In local development, password-reset
requests show a development reset link. Staging/production require SMTP settings from `.env.example`.

Without Docker (native backend dev server): PostgreSQL must still run somewhere reachable at
`localhost:5432` (via `docker compose up -d postgres`, or a native install) - see "Running
PostgreSQL locally" and the backend commands in `CLAUDE.md`.

Native development uses the deterministic in-memory vector store and governed local/offline
analysis behavior by default, so normal verification does not send document evidence to an external
language model. Docker Compose selects ChromaDB at `chromadb:8000`; its host-published
native-development endpoint is `localhost:8001`. A separately configured Gemini academic provider
may be used only after confirmed question evidence exists. Extraction Gemini remains independently
controlled and disabled by default.

## Repository map
- `frontend/`: React/TypeScript application.
- `backend/`: FastAPI application and tests.
- `knowledge_base/`: approved Excel sources, manifest, and validation guidance.
- `docs/`: PRD, SRS, architecture, API, AI/RAG, database, security, and tests.
- [`docs/EXTRACTION_ARCHITECTURE.md`](docs/EXTRACTION_ARCHITECTURE.md): OCR,
  structure parsing, provenance, reconciliation, and review-gate contracts.
- `scripts/`: validation and developer utilities.
- `infrastructure/`: deployment-related configuration.

## Important
This remains a controlled pilot under development, not a production accreditation or approval platform. Do not add
real exam files or secrets to Git.


## Reliable question preparation

Before processing, the Faculty Member chooses one path:

1. **Assisted PDF extraction — recommended starting point.** Local extraction proposes questions and
   the reviewer corrects only incomplete text, wrong boundaries, types, options, or visible marks.
2. **Paste or import a question list.** Questions may be pasted directly from Word/PDF or imported
   through a simple Excel-compatible CSV. Only question number, complete text, and visible marks are
   required; type and options are optional.
3. **Manual PDF entry.** Use only when automatic extraction misses a question or the page layout is
   highly irregular. The reviewer adds the missing question from the original PDF.

The review screen uses the full PDF page on the left as the source reference. It no longer renders a
separate automatically cropped question image, because an incorrect crop can be more misleading than
helpful.

See [the visual review scope](docs/HUMAN_ASSISTED_EXTRACTION_REVIEW.md) and
[the structured-template guide](docs/STRUCTURED_QUESTION_TEMPLATE.md).

## Controlled-pilot extraction boundary

The pilot supports readable Midterm and Final PDFs for computing courses and the basic question
types: multiple choice, True/False, short answer, essay, and simple textual fill-in-the-blank.
Tables, figures, and UML/other diagrams remain part of the original visual question region and are
not decomposed cell-by-cell. The platform extracts only marks visibly written in the source; it never
invents a mark. Faculty confirmation of the exact question revision is mandatory before academic
analysis.

