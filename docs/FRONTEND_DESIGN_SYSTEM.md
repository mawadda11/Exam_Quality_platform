# Frontend Design System

## Status and purpose

This document is the authoritative frontend visual and navigation contract established by
Frontend Alignment Phase 1 and extended by Phase 2. It records design decisions derived from the
approved Base44 reference screenshots without treating simulated screenshot content as product
behavior.

Phase 1 implements design tokens, shared UI primitives, focused tests, and minimal integration into
the existing single-page frontend. It does not add routing, page architecture, authentication,
dashboard metrics, a new upload lifecycle, Extraction Review behavior, or semantic evaluators.

Phase 2 implements the application shell, responsive primary navigation, refresh-safe routes, and
URL-controlled analysis/result navigation. It does not redesign the New Analysis lifecycle or
introduce Phase 3, M3, authentication, new APIs, dashboard statistics, or Extraction Review.

Phase 3 approves the Version 1 New Analysis lifecycle and implements real API-backed dashboard and
history presentation. It does not change the existing creation/upload/run sequence, add score
requests for dashboard rows, or introduce Phase 4, M3, authentication, or Extraction Review.

The design system exists so future Codex and Claude Code sessions can extend the interface without
reinterpreting screenshots, inventing business behavior, or creating inconsistent component
variants.

## Authoritative reference hierarchy

When sources disagree, use this order:

1. `CLAUDE.md`, the approved PRD/SRS, governance documents, architecture, roadmap, and traceability
   matrix define workflow, business rules, academic semantics, milestone scope, and deferrals.
2. Current backend API contracts and frontend API client types define currently available runtime
   behavior.
3. This document defines the approved reusable frontend visual language.
4. Base44 screenshots are visual and UX references only. They never authorize unsupported data,
   endpoints, rules, statuses, mappings, or authentication.

**Reason:** a visually persuasive prototype may contain simulated or superseded behavior. Keeping
behavioral authority in repository documents prevents presentation work from weakening academic
governance.

## Design goals

- Present an academic decision-support tool, not an accreditation approval system.
- Use a professional, calm, evidence-oriented visual language.
- Preserve the screenshot direction: dark navy navigation, teal brand accent, light neutral
  canvas, white cards, subtle borders, wide evidence tables, and clear contextual actions.
- Make academic statuses, evidence limitations, and processing failures distinguishable.
- Remain usable with a keyboard, screen reader, reduced motion, narrow viewport, and mixed
  Arabic/English source text.
- Reuse a small component vocabulary rather than accumulating page-specific button, alert, card,
  badge, tab, and table styles.

## Tokens

Tokens are CSS custom properties in `frontend/src/styles/tokens.css`. Components must consume
semantic token names rather than repeat raw color, spacing, radius, or shadow values.

### Brand and surfaces

| Token | Value | Intended use and reason |
|---|---:|---|
| `--color-brand-navy` | `#102a43` | Primary actions and future navigation; matches the screenshot's restrained academic identity |
| `--color-brand-navy-active` | `#1f3a57` | Hover/selected navy without introducing a second brand |
| `--color-brand-teal` | `#14b8a6` | Brand accent and completed progress, not an academic score threshold |
| `--color-brand-teal-strong` | `#0f8f83` | Accessible teal text on light surfaces |
| `--color-brand-teal-subtle` | `#ecfdfb` | Low-emphasis branded surfaces |
| `--color-canvas` | `#f8fafc` | Main application background |
| `--color-surface` | `#ffffff` | Cards, tables, and dialogs |
| `--color-surface-muted` | `#f1f5f9` | Empty states, secondary panels, and neutral tracks |
| `--color-border` | `#dbe4ee` | Default separation without heavy boxes |
| `--color-border-strong` | `#cbd5e1` | Controls and stronger structural boundaries |

### Text

| Token | Intended use |
|---|---|
| `--color-text` | Primary headings and high-emphasis content |
| `--color-text-secondary` | Descriptions and standard metadata |
| `--color-text-muted` | Supporting metadata only; never the sole indicator of a required state |
| `--color-text-inverse` | Text on navy or other approved dark surfaces |

### State colors

State colors are semantic aliases. Components must include visible text and, where appropriate, an
icon; color alone is insufficient.

| Token group | Use |
|---|---|
| `success` | Successful UI operations and the exact `Satisfied` academic status |
| `warning` | Recoverable UI warnings and the exact `Partially Satisfied` status |
| `danger` | UI errors and the exact `Not Satisfied` status |
| `info` | Informational messages and the exact `Not Applicable` status |
| `neutral-status` | The exact `Not Verified` status |

**Reason:** shared hues support scanning, but explicit text preserves meaning for color-vision
deficiency, screen readers, monochrome print, and governance review.

## Academic-status visual contract

The only academic-status labels are:

- `Satisfied`
- `Partially Satisfied`
- `Not Satisfied`
- `Not Verified`
- `Not Applicable`

`StatusBadge` renders the exact label plus a decorative icon. Do not replace these labels with
Passed, Failed, Valid, Warning, Covered, Needs Review, Represented, Limited, severity, priority, or
readiness terminology.

Processing states and API errors are separate concepts and must not use an academic-status badge.

**Reason:** alternate labels would change the controlled evaluation vocabulary and could imply an
approval or grading decision that the system does not make.

## Typography

The approved stack is:

```css
Inter, "Noto Sans Arabic", "Segoe UI", Tahoma, Arial, sans-serif
```

The stack intentionally uses installed fonts and broad Arabic fallbacks; Phase 1 adds no remote font
request or font package.

Use tokenized sizes:

- extra small: table metadata and compact badges;
- small: supporting labels and metadata;
- medium: normal body and form content;
- large: card and state titles;
- extra large: section titles;
- 2XL: page titles and score values.

Body content uses a readable 1.6 line height. Large headings use a tighter 1.2 line height.

**Reason:** the hierarchy resembles the screenshots while avoiding a font-delivery dependency and
preserving Arabic glyph coverage.

## Spacing, radii, borders, and shadows

Spacing follows a 4-pixel-compatible scale:

`4, 8, 12, 16, 24, 32, 40, 48, 64`.

Radii:

- small: compact badges and controls;
- medium: buttons and inputs;
- large: alerts and tables;
- extra large: major cards;
- pill: statuses only where the compact pill shape is meaningful.

Borders are normally one pixel. Cards use a subtle shadow; raised dialogs may use the stronger
shadow token. Avoid deep shadows, glass effects, gradients, or decorative motion.

**Reason:** consistent spacing and restrained elevation preserve the clean institutional character
of the screenshots and keep dense evidence displays readable.

## Layout and content widths

Tokens reserve three maximum content widths:

- compact: forms and focused reading;
- form: multi-column data entry;
- wide: results, evidence, and reports.

Phase 2 uses these widths inside a persistent desktop sidebar layout and a responsive mobile header
and navigation drawer. Route content selects the narrowest appropriate width rather than forcing
forms and evidence tables into one shared container.

**Reason:** content-width tokens allow the current single-card frontend and future wide workspace to
share one foundation without prematurely creating routing or page architecture.

## Shared component contracts

### `BrandMark`

- Variants: `small`, `medium`, `large`.
- May show the full product name or an accessible icon-only label.
- The shield/check graphic expresses traceable review, not institutional approval.

### `Button`

- Variants: `primary`, `secondary`, `ghost`.
- Loading replaces visible button text with an explicit loading label, sets `aria-busy`, and
  disables repeated activation.
- Disabled and loading states must remain programmatically detectable.
- Buttons default to `type="button"` to prevent accidental form submission.

No success/danger button variants are authorized merely to color an action. Destructive workflows
must be explicitly approved before they receive a specialized action contract.

### `Card`

- Variants: `default`, `muted`, `raised`.
- Semantic host may be `div`, `section`, or `article`.
- A section/article card requires a meaningful heading in its content.

### `Alert`

- Variants: `info`, `success`, `warning`, `error`.
- Always renders a visible state title and icon in addition to color.
- Warning/error use an assertive alert role; information/success use a polite status role.
- Academic findings do not become alerts merely because their status is unfavorable.

### `PageHeader`

- Provides one heading, optional eyebrow, description, and contextual actions.
- Supports heading levels 1 through 3 so pages retain a correct heading hierarchy.
- Actions wrap or stack rather than shrinking below usable touch sizes.

### `PageState`

- Variants: `loading`, `empty`, `error`, `success`.
- Includes a visible title, optional message, and optional action such as Retry.
- Loading exposes `aria-busy`; errors expose an alert role.

### `StatusBadge`

- Accepts only the frontend `AcademicStatus` union.
- Renders exact visible status text and a decorative icon.
- Never accepts arbitrary labels, semantic-confidence labels, processing states, or severity.

### `ProgressStepper`

- Step states: `complete`, `current`, `upcoming`.
- Current step uses `aria-current="step"` and visible assistive text.
- Completed state means workflow progress only; it does not mean the exam satisfied an academic
  criterion.
- Phase 1 provides the primitive but does not change the current processing workflow.

### `Tabs`

- Controlled component with a stable string ID per item.
- Uses tablist/tab semantics, one tab stop, `aria-selected`, and matching tab-panel IDs.
- Supports click, Left/Right Arrow, Home, and End with automatic activation.
- Result tabs are controlled by `/analyses/:analysisId/results/:tab` in Phase 2. Back, forward,
  refresh, and shared URLs therefore retain the selected result section.

### `ResponsiveTable`

- Renders a native table and caption inside a labelled, focusable horizontal-scroll region.
- Callers provide proper `scope="col"` and `scope="row"` headers.
- The caption may be visually hidden but remains the accessible name.
- A div-grid is not an acceptable replacement for genuinely tabular evidence.

### `ScoreRing`

- Accepts a numeric/string score or null plus the verified applicable denominator.
- A numeric score is displayed exactly with `%`.
- Null displays `Insufficient Evidence`, never zero.
- Uses one neutral brand accent regardless of value. It must not encode undocumented pass/fail,
  red/amber/green, readiness, or quality bands.
- The denominator statement remains visible and part of the accessible name.

**Reason:** the score formula is governed by the KB. Presentation may explain the result but must
not add thresholds or qualitative labels.

## Forms and upload-state conventions

Forms must:

- retain visible labels;
- associate help and errors through IDs and `aria-describedby`;
- set `aria-invalid` after validation failure;
- use fieldsets/legends for grouped choices;
- preserve entered values after recoverable failure;
- place a focused error summary before the first invalid field when a form has multiple errors.

Future visually enhanced file upload must retain a native file input. Required upload states are:

- missing;
- selected;
- uploading;
- uploaded;
- rejected with the backend's safe detail;
- retry available.

Both Exam PDF and populated TP-153 remain mandatory. The interface must not expose a blank TP-153
download until an approved artifact exists, and it must not invent completion-guide or required-
sections content.

**Reason:** a large upload card is a visual enhancement, not permission to weaken upload validation
or fabricate support artifacts.

## Score and semantic-confidence presentation

Current score behavior is unchanged:

- Satisfied = 1.0;
- Partially Satisfied = 0.5;
- Not Satisfied = 0.0;
- Not Verified and Not Applicable are excluded;
- no verified applicable findings produces `Insufficient Evidence`.

Phase 1 does not change the currently implemented numeric confidence shown for existing semantic
findings. The approved future categorical semantic-confidence contract (`High`, `Medium`, `Low`)
remains planned for M6 and must use the backend's authoritative enum when implemented.

Numeric OCR/extraction confidence must be labelled extraction confidence and must never be converted
to semantic confidence.

## Loading, empty, error, success, retry, and connectivity states

- Loading: state-specific text, `aria-busy`, and no fabricated placeholder data.
- Empty: explain the genuine absence and provide an appropriate next action when one exists.
- Error: preserve safe Problem Details text and provide Retry only for a repeatable request.
- Success: confirm the completed user action without implying academic approval.
- Partial data: show the available section and a scoped error for the unavailable section.
- Connectivity loss: state that the connection was interrupted and that polling will retry; clear
  the notice after recovery.

Phase 1 only provides primitives. Refactoring current all-or-nothing results loading and silent
history/polling failures belongs to later alignment phases.

## Accessibility and focus

- Every interactive control requires a visible `:focus-visible` indicator.
- Keyboard order follows reading order; do not use positive `tabindex`.
- Use semantic landmarks and heading hierarchy when page architecture is introduced.
- Move focus to a route/page heading after future navigation.
- Return focus to the trigger after a future modal or mobile drawer closes.
- Announce processing/upload changes through appropriate status regions.
- Use text and icons in addition to color.
- Keep interactive targets at least 44px high where practical.
- Honour `prefers-reduced-motion`; essential state changes must never depend on animation.
- Avoid auto-focusing ordinary pages. Focus errors only when it helps the user correct an action.

**Reason:** accessibility is part of the component contract, not a final styling pass.

## Responsive rules

- Wide desktop: persistent sidebar plus wide evidence workspace.
- Tablet: reduced gutters and horizontally scrollable result tabs.
- Mobile: one-column content, keyboard-operable navigation drawer, stacked actions, and later
  stacked upload cards.
- Complex tables remain native tables inside labelled horizontal-scroll regions. Short history or
  question datasets may gain an alternate card presentation only if semantic equivalence is tested.
- Progress steppers collapse to a vertical list on narrow screens.
- Page-header actions stack when horizontal space is insufficient.

Phase 2 implements the shell, sidebar, mobile header/drawer, and route content widths. Full
dashboard composition, upload-card redesign, and complete result-page alignment remain planned.

## Arabic and mixed-language content

- Extracted source text uses `dir="auto"` so Arabic, English, and mixed content follow the source.
- Identifiers and isolated mixed-direction values use `<bdi>`, including question numbers,
  filenames, course codes, rule IDs, requirement IDs, hashes, and page references where needed.
- CSS uses logical properties (`margin-inline`, `padding-inline`, `border-inline`,
  `inset-inline`, `text-align: start`) in all new shared components.
- Preserve question numbering and technical identifiers exactly; do not transliterate or translate
  them.
- Full interface translation is not part of Phase 1.

**Reason:** the system processes Arabic and English documents, but source fidelity does not
authorize silently translating the application or changing extracted identifiers.

## Prohibited visual semantics

Do not introduce:

- pass/fail, approve/reject, valid/invalid, readiness, accreditation, compliance, or attainment
  labels for academic results;
- severity, priority, rule weights, dimension weights, or qualitative score bands;
- red/amber/green score thresholds;
- hardcoded dashboard counts, result values, findings, mappings, dates, or recommendations;
- AI-derived mappings presented as official TP-153 mappings;
- numeric semantic-confidence percentages as the approved categorical contract;
- mock user identity, real sign-in, Sign Out, Profile, or role-management behavior;
- Base44 editor chrome, Preview/Publish controls, upgrade prompts, or decorative purple borders;
- unavailable global reports/help routes or unapproved TP-153 artifacts.

## Phase 2 route and shell contract

React Router is the single navigation authority. Runtime analysis data remains owned by the
existing API layer; route state must not duplicate or replace backend state.

| Route | Current purpose |
|---|---|
| `/` | Replace-redirect to `/dashboard` |
| `/dashboard` | Real history-derived summary and recent analyses; no fabricated or score metrics |
| `/analyses` | Owned analysis history from the existing list endpoint |
| `/analyses/new` | Existing analysis-creation form and persistence lifecycle |
| `/analyses/:analysisId/documents` | Existing required Exam and TP-153 uploads |
| `/analyses/:analysisId/start` | Existing run action, only when queued and ready |
| `/analyses/:analysisId/progress` | Existing polling view, only while processing or failed |
| `/analyses/:analysisId/results/:tab` | Completed-analysis results with a URL-controlled tab |

The shared `/analyses/:analysisId` route loads the analysis once. Its child routes consume that
loaded record through outlet context, so ordinary documents/start/progress/results navigation does
not issue redundant analysis-summary requests. An explicit post-upload refresh remains necessary
because the backend has changed the uploaded-file and readiness state.

Route guards use the backend's returned `state` and `ready_for_analysis` fields:

- queued and not ready routes to documents;
- queued and ready routes to start;
- active processing or failed routes to progress;
- completed routes to results overview.

An unknown results tab replace-redirects to overview. A missing, inaccessible, or malformed
analysis URL shows a safe error using the API Problem Details message where available. General
unknown routes show a neutral application fallback.

Desktop navigation is persistent. Mobile navigation is a modal drawer with initial focus, a focus
boundary, Escape dismissal, backdrop/close controls, and focus return. Active primary links use
`aria-current="page"`. The shell deliberately exposes only Dashboard, Analyses, and New Analysis;
unsupported Reports, Help, Profile, Sign Out, and authentication destinations are absent.

The development identity remains a clearly labelled workspace notice and header adapter. It is not
presented as login, profile, role, or session behavior.

The production frontend image uses Nginx and installs an SPA `try_files` fallback. Static assets
continue to resolve normally, while direct requests to nested application routes return
`index.html` so React Router can restore the URL.

## Approved Version 1 New Analysis lifecycle

Version 1 uses **Option A**:

1. The user enters Exam Information.
2. The frontend creates the analysis through the existing API.
3. Persisted course, exam-type, and term metadata becomes read-only.
4. The user uploads the Exam PDF and populated TP-153 independently.
5. The user starts the existing analysis workflow after both uploads are confirmed.

Option B (holding metadata and browser `File` objects locally until Start) is not approved for
Version 1. The existing APIs cannot make create/upload/upload/run atomic, browser-selected files
cannot survive refresh, and partial upload failures require resume behavior that the current API
does not provide safely.

Option A can leave an abandoned queued analysis when a user creates a record but does not finish
both uploads. This is an explicit Version 1 limitation. The server-persisted record and independent
uploads provide safer refresh and retry behavior than a browser-only draft. Addressing abandoned
records requires a separately approved cleanup, deletion, or transactional draft contract; the
frontend must not invent one.

## Dashboard and history data contract

Dashboard and history use one `GET /analyses` request per visited route. They may derive only:

- total analyses;
- completed analyses (`state === "completed"`);
- linked reanalyses (`predecessor_analysis_id !== null`);
- the five most recent analysis metadata records;
- each record's exact backend processing state.

They must not request per-analysis scores, findings, reports, or detail endpoints for metrics.
Processing states retain their exact backend labels and use `ProcessingStateBadge`; they must never
use `StatusBadge` or be translated into the five academic statuses.

## Currently implemented, planned, and deferred

### Currently implemented after Phase 3

- Central visual tokens and shared base/component CSS.
- Eleven shared UI primitives documented above.
- Responsive application shell, persistent desktop sidebar, and mobile navigation drawer.
- Refresh-safe route hierarchy for dashboard, history, creation, documents, start, progress, and
  results.
- One shared analysis-summary load across nested analysis routes, plus backend-state route guards.
- URL-controlled keyboard-operable result tabs with browser history.
- Real API-backed analysis history links; no score request is issued for a history row.
- Real API-backed dashboard summary cards and five-record recent-analysis table.
- Exact backend processing-state badges kept separate from academic-status badges.
- Option A recorded as the approved Version 1 New Analysis lifecycle.
- Production Nginx fallback for nested client-side routes.
- Keyboard-operable result tabs.
- `dir="auto"` for displayed question source text and `<bdi>` for question labels.
- Existing API calls, workflow states, scoring, numeric confidence behavior, upload lifecycle,
  report generation, and reanalysis behavior unchanged.

### Planned frontend-alignment work

- Three-step New Analysis presentation.
- Upload cards and complete processing presentation.
- Results header, score summary, filters, partial loading, and full responsive alignment.

### M3-M5 reserved states - not implemented

- `review_ready`;
- initial Extraction Review revision;
- review snapshot API consumption;
- dirty/saved/stale revision state;
- source anchors;
- correction, restoration, and false-positive exclusion;
- confirmation eligibility and exact-revision confirmation;
- confirmed read-only state;
- post-confirmation processing.

M3 establishes the processing pause and initial snapshot. M4 establishes review/confirmation APIs.
M5 establishes the minimal Extraction Review UI. No frontend component may simulate these contracts
before its milestone.

### Deferred or prohibited until an approved dependency exists

- Real authentication and multi-role authorization.
- Manual creation of official CLOs, topics, assessment records, mappings, policies, or thresholds.
- Blank TP-153 download without an approved artifact.
- Deferred evaluation rules or unsupported semantic mappings.
- Institutional production features outside the training-project Version 1 scope.
