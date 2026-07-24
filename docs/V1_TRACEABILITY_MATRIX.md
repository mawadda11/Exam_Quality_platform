# Version 1 Traceability and Scope Freeze

Status date: 2026-07-24

This matrix freezes the approved training-project Version 1 scope before
the final implementation milestones. It does not authorize institutional
production deployment and does not change the product exclusions in the
PRD.

Status meanings:

- **Complete**: implemented and covered by existing automated tests.
- **Partial**: implemented only for the explicitly described branches.
- **Retained**: mandatory Version 1 work approved for a later milestone.
- **Deferred**: no evaluator may be implemented until the stated approved
  criterion, policy, or artifact exists.
- **Enforced by construction**: a system/governance invariant rather than
  an exam-facing Finding.

An unavailable evaluator is never represented by an unconditional `Not
Verified` Finding. `Not Verified` is reserved for an implemented evaluator
whose required evidence is missing, unreadable, unreliable, or
insufficient.

## PRD traceability

The PRD has no requirement identifiers, so the IDs below are stable
project-local traceability IDs. Acceptance, scoring, and exclusion clauses
are included with the capability they constrain.

| ID | Requirement | Status | Implementation and tests | Remaining Version 1 work |
|---|---|---|---|---|
| PRD-01 | Faculty Member is the sole Version 1 user | Complete | Development identity boundary and ownership filtering; `test_identity.py` and ownership API tests | Real authentication is production-only |
| PRD-02 | Midterm and Final computing-course analyses | Complete | Analysis schemas, API, UI validation, and `test_analyses_api.py` | No institutional course catalogue is inferred |
| PRD-03 | Exam PDF and populated TP-153 are both mandatory | Complete | Dual upload state and atomic run claim; `test_uploads_api.py`, `test_run_progress_api.py` | None |
| PRD-04 | Validate extension, MIME, signature, size, readability, and availability | Partial | Existing file and upload tests cover every item except parser readability at upload time | Add parser-readability validation and safe cleanup |
| PRD-05 | Page-aware digital PDF extraction | Complete for current text | `PdfPlumberExamExtractor`; digital extraction and persistence tests | Extend only for retained structured evidence |
| PRD-06 | OCR for scanned exams | Complete for pages with no digital text | Local Tesseract adapter and `test_ocr_extraction.py` | Preserve behavior while adding retained structured evidence |
| PRD-07 | Questions, hierarchy, marks, totals, instructions, numbering, and layout | Partial | Extraction, persistence, marks, and numbering suites | Add metadata, question-specific instructions, references, and retained layout evidence |
| PRD-08 | Tables, images, diagrams, code, and supporting assets | Retained | No runtime structured extraction yet | Add only evidence needed by retained RULE014, RULE016, and RULE022 |
| PRD-09 | Extract TP-153 CLOs, topics, methods, activities, hours, and percentages | Complete in backend | TP-153 extraction, persistence, and read endpoint tests | Present assessment records in UI and report |
| PRD-10 | Versioned KB validation and retrieval | Complete | KB validation/normalization/provenance and semantic retrieval suites | Add repeatable startup/readiness verification |
| PRD-11 | Deterministic and semantic rule evaluation | Partial | Nine fully supported rules and partial RULE006; rule and semantic suites | Implement retained rules; preserve explicit deferrals |
| PRD-12 | Exactly five academic statuses | Complete | Domain enum, persistence, scoring, and semantic-output validation tests | Extend the same validation to retained evaluators |
| PRD-13 | Missing or insufficient evidence becomes Not Verified | Complete for implemented evaluators | Rule, pipeline, and semantic governance tests | Extend evidence-conditioned behavior to retained rules |
| PRD-14 | Exact deterministic scoring and Insufficient Evidence | Complete | Scoring, API, UI, and report tests | No formula changes |
| PRD-15 | Finding and evidence traceability | Complete for current evidence | Persistence, API, UI drill-down, and report tests | Add retained asset, mapping, and rule evidence |
| PRD-16 | Controlled actionable recommendations | Complete for current findings | Exact KB lookup and recommendation API tests | Reuse existing KB recommendation IDs for retained rules |
| PRD-17 | Background progress and safe failure states | Partial | Runner, progress, rollback, and non-blocking tests | Stop creating the no-op `generating_report` transition while retaining legacy enum compatibility |
| PRD-18 | Six-section results interface | Complete structurally | Results component suites | Add mappings, assessments, retained findings, navigation, and retry |
| PRD-19 | Explicit question-to-CLO and question-to-topic mappings | Retained | Existing citation rules produce evidence but no dedicated structured API output | Persist and expose traceable explicit mappings without semantic inference |
| PRD-20 | Assessment-method consistency | Retained | TP-153 assessment data is already extracted | Implement RULE003 and present assessment evidence |
| PRD-21 | Missing-evidence display and evidence drill-down | Complete for current findings | Results UI tests | Extend for retained evidence types |
| PRD-22 | Downloadable report | Complete | On-demand report generation, ownership, content, PDF, API, and UI tests | Add retained mappings and assessment content |
| PRD-23 | Analysis history | Complete with limited navigation | History API and UI tests | Add normal return-to-history and new-analysis actions |
| PRD-24 | Linked immutable reanalysis | Complete | Reanalysis API/UI tests and predecessor migration | Include retained outputs without changing immutability |
| PRD-25 | Download blank TP-153 template | Deferred pending artifact | No approved non-confidential blank template is present | Add download only after an approved artifact is supplied |
| PRD-26 | Download TP-153 completion guide | Retained | No guide artifact or route exists | Build only from approved fields and required sections |
| PRD-27 | View required TP-153 sections | Retained | Extractor already names CLO, topic, and assessment sections | Add API/UI reference |
| PRD-28 | Guidance for missing, incomplete, unreadable, or invalid TP-153 | Partial | Upload errors and missing-section evidence exist | Add pre-upload and processing guidance without inferring content |
| PRD-29 | No manual official CLO/topic entry or inferred course data | Complete | Extraction and governance behavior | Preserve |
| PRD-30 | Reports and reanalyses never overwrite prior results | Complete | Immutable report and predecessor tests | Preserve |
| PRD-31 | Advisory scope and documented exclusions | Complete | Prompt, report, UI, and governance disclaimers | Preserve fake provider as default |

## SRS functional traceability

| Requirement | Status | Current implementation/tests | Remaining Version 1 work |
|---|---|---|---|
| FR-001 Create an analysis | Complete | Analysis API and frontend upload-flow tests | Navigation only |
| FR-002 Select Midterm or Final | Complete | Schema and frontend validation tests | None |
| FR-003 Upload one exam and one TP-153 | Complete | Upload API and dual-file state tests | Assistance controls |
| FR-004 Validate type, signature, size, readability, and availability | Partial | File/upload tests; stored-file availability pipeline check | Add parser-readability validation before acceptance |
| FR-005 Extract page-aware digital content | Complete for current text | Digital extractor and persistence tests | Retained structured evidence |
| FR-006 Invoke OCR for scanned/image pages through an adapter | Complete for exam pages with no digital text | OCR contract and live Tesseract test | Preserve and extend only where retained evidence permits |
| FR-007 Extract hierarchy, marks, declared total, instructions, assets, code, and structure | Partial | Hierarchy/marks/total/instruction extraction exists | Add retained metadata, assets, code, references, and associations |
| FR-008 Extract TP-153 CLOs, topics, methods, activities, hours, and percentages | Complete in backend | TP-153 extraction/persistence/API tests | UI/report assessment presentation |
| FR-009 Create immutable source evidence | Complete for current types | Evidence persistence and ownership tests | Extend for retained evidence |
| FR-010 Retrieve versioned KB records | Complete | KB/RAG tests | Startup/readiness verification |
| FR-011 Execute deterministic and semantic rules | Partial | Existing runtime and semantic integration tests | Retained rules and explicit deferrals |
| FR-012 Return one approved status per executed rule | Complete | Domain, persistence, and semantic validation | Apply to retained evaluators |
| FR-013 Generate evidence-based explanations and recommendations | Partial coverage | Findings and recommendation tests | Retained rules |
| FR-014 Calculate approved score | Complete | Scoring/API/report/UI tests | None |
| FR-015 Display progress, counts, score, mappings, findings, missing evidence, and recommendations | Partial | Everything except explicit mapping/assessment presentation and accurate finalizing stage | Add retained display work |
| FR-016 Generate downloadable report | Complete | Report suites | Add retained content |
| FR-017 Store history | Complete | History API/UI tests | Navigation |
| FR-018 Create linked reanalysis | Complete | Reanalysis API/UI tests | Preserve |

## Exam-facing Knowledge Base rule coverage

The controlled KB contains 21 derived exam-facing requirements:
REQ001-REQ009 and REQ011-REQ022. `CAPABILITY_MANIFEST` mirrors this table
and is tested directly against `04_requirements.xlsx` and
`07_evaluation_rules.xlsx`.

| Rule | Requirement | Frozen status | Decision |
|---|---|---|---|
| RULE001 | Question-to-CLO Mapping | Complete | Existing deterministic citation mapping |
| RULE002 | CLO Relevance | Complete | Existing governed semantic evaluator |
| RULE003 | Assessment Method Consistency | Retained | Conservative explicit document comparison; ambiguity is Not Verified |
| RULE004 | Question Format Suitability | Complete | Existing governed semantic evaluator |
| RULE005 | Applicable CLO Coverage | Complete | Existing deterministic evaluator |
| RULE006 | CLO Coverage Distribution | Partial | Zero-CLO and one-CLO branches only; two-or-more branch deferred because the KB defines no concentration threshold |
| RULE007 | Question-to-Topic Alignment | Complete | Existing deterministic citation mapping |
| RULE008 | Out-of-Scope Content | Complete | Existing governed semantic evaluator |
| RULE009 | Applicable Topic Coverage | Complete | Existing deterministic evaluator |
| RULE011 | Clear Task Statement | Retained | Governed semantic evaluator using EV002 and exact KB conditions |
| RULE012 | Unambiguous Wording | Retained | Governed semantic evaluator using EV002 and exact KB conditions |
| RULE013 | Complete Question Information | Retained | Governed semantic evaluator using question/context/instruction evidence |
| RULE014 | Referenced Material Availability | Retained | Deterministic comparison of explicit references with extracted assets |
| RULE015 | Supporting Material Legibility | Deferred | No approved visual-quality thresholds or governed vision evaluator |
| RULE016 | Supporting Material Association | Retained | Exact labels, references, page geometry, and unique associations only |
| RULE017 | Visible Marks | Deferred | Institutional applicability and overlapping status conditions are undefined |
| RULE018 | Correct Total Marks | Complete | Existing deterministic arithmetic evaluator |
| RULE019 | Consistent Numbering | Complete | Existing deterministic structural evaluator |
| RULE020 | Exam Identification | Deferred | Institutionally required/essential field policy is undefined |
| RULE021 | Complete Instructions | Retained | Conservative governed semantic evaluator; no local policy inference |
| RULE022 | Resolvable Cross-References | Retained | Deterministic resolution to explicit, unique layout targets |

## System and governance rule disposition

These KB rules validate the platform or its released outputs. They do not
belong in the exam-facing capability manifest and must not create
additional scored Findings.

| Rule | Disposition | Enforcement evidence |
|---|---|---|
| RULE010 Finding Traceability | Enforced by construction | Finding-evidence validation, persistence, API, and report tests |
| RULE023 Readable Exam Input | Partial system validation | Parser failures safely fail processing; upload-time parser validation remains |
| RULE024 Usable CLO Data | Enforced by construction | Missing-section evidence and conservative evaluators |
| RULE025 Usable Topic Data | Enforced by construction | Missing-section evidence and conservative evaluators |
| RULE026 Usable Assessment Data | Enforced by construction | Missing-section evidence and semantic preconditions |
| RULE027 Actionable Recommendation | Enforced by construction | Controlled recommendation lookup and applicability validation |
| RULE028 Exam-Level Conclusions | Enforced by construction | Scope-limited prompts, explanations, and report disclaimer |
| RULE029 Single Status per Rule | Enforced by construction | Enum/schema validation and unique `(analysis_id, rule_id)` constraint |
| RULE030 Evidence-Based Explanation | Enforced by construction | Evidence-link and structured-output validation |

## Production-only deferrals

The following remain outside the training-project Version 1:

- institutional SSO/OIDC, login, sessions, or token infrastructure;
- TLS termination and deployment certificates;
- cloud secrets management and managed hosting;
- distributed workers, autoscaling, and production SLAs;
- institutional retention/deletion automation;
- centralized metrics, tracing, alerting, and security monitoring;
- cloud OCR/vision or live AI-provider calls without an approved privacy
  decision;
- every product exclusion already listed in the PRD.

