# Version 1 Traceability and Scope Freeze

Status date: 2026-07-25

This matrix freezes the approved training-project Version 1 scope before
the final implementation milestones. It does not authorize institutional
production deployment and does not change the product exclusions in the
PRD.

Implementation status meanings:

- **Complete**: implemented and covered by existing automated tests.
- **Partial**: implemented only for the explicitly described branches.
- **Retained**: mandatory Version 1 work approved for a later milestone.
- **Deferred**: no evaluator may be implemented until the stated approved
  criterion, policy, or artifact exists.
- **Enforced by construction**: a system/governance invariant rather than
  an exam-facing Finding.

Hybrid-redesign status meanings:

- **Design-authorized**: approved as part of the target architecture.
- **Currently implemented**: present in runtime and covered by tests.
- **Planned**: design-authorized but not yet implemented.
- **Deferred**: prohibited until the stated criterion, policy, or artifact is approved.

Design authorization never changes an implementation status by itself. M1 implements governance
contracts only. M2 implements review-revision/categorical-confidence persistence and strict
internal schemas. M3 creates revision 1, pauses processing at `review_ready`, guards downstream
stages, and adds minimal frontend compatibility; it does not add review actions, confirmation,
post-confirmation continuation, or semantic changes.

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
| PRD-04 | Validate extension, MIME, signature, size, readability, and availability | Complete | Upload-time parser readability, encrypted/corrupt PDF rejection, valid scanned-PDF acceptance, and cleanup are covered by file/upload tests | Preserve |
| PRD-05 | Page-aware digital PDF extraction | Complete for current text | `PdfPlumberExamExtractor`; digital extraction and persistence tests | Extend only for retained structured evidence |
| PRD-06 | OCR for scanned exams | Complete for pages with no digital text | Local Tesseract adapter and `test_ocr_extraction.py` | Preserve behavior while adding retained structured evidence |
| PRD-07 | Questions, hierarchy, marks, totals, instructions, numbering, and layout | Partial | Extraction, persistence, marks, and numbering suites | Add metadata, question-specific instructions, references, and retained layout evidence |
| PRD-08 | Tables, images, diagrams, code, and supporting assets | Retained | No runtime structured extraction yet | Add only evidence needed by retained RULE014, RULE016, and RULE022 |
| PRD-09 | Extract TP-153 CLOs, topics, methods, activities, hours, and percentages | Complete | TP-153 extraction, persistence, API, results UI, and report source-record presentation tests | Preserve source-versus-conclusion distinction |
| PRD-10 | Versioned KB validation and retrieval | Complete | KB validation/normalization/provenance and semantic retrieval suites | Add repeatable startup/readiness verification |
| PRD-11 | Deterministic and semantic rule evaluation | Complete for the authorized M6-M11 scope | Fourteen unconditional supported runtime rules, ten semantic/hybrid evaluators, deterministic coverage, M10 presentation, M11 acceptance, and partial RULE006 | Preserve explicit deferrals |
| PRD-12 | Exactly five academic statuses | Complete | Domain enum, persistence, scoring, and semantic-output validation tests | Extend the same validation to retained evaluators |
| PRD-13 | Missing or insufficient evidence becomes Not Verified | Complete for implemented evaluators | Rule, pipeline, and semantic governance tests | Extend evidence-conditioned behavior to retained rules |
| PRD-14 | Exact deterministic scoring and Insufficient Evidence | Complete | Scoring, API, UI, and report tests | No formula changes |
| PRD-15 | Finding and evidence traceability | Complete for current supported evidence | Persistence, API, UI drill-down, semantic item details, derived relationship labels, and report tests | Extend only for authorized retained evidence |
| PRD-16 | Controlled actionable recommendations | Complete for current findings | Exact KB lookup and recommendation API tests | Reuse existing KB recommendation IDs for retained rules |
| PRD-17 | Background progress and safe failure states | Complete for current supported flow | Runner, progress, rollback, revision-idempotency, exact-confirmation continuation, duplicate-task guard, safe-failure tests, and M11 integrated acceptance | Preserve |
| PRD-18 | Six-section results interface | Complete for current supported scope | Results component suites including mappings, assessments, confidence, coverage, denominator, independent loading, and retry | Extend only for authorized retained findings |
| PRD-19 | Explicit and derived question-to-CLO/topic relationships | Complete for current supported scope | RULE001/RULE007 persist governed item-level relationships and M10 presents them as advisory derived relationships against confirmed evidence | Preserve source/derived distinction |
| PRD-20 | Assessment-method consistency | Complete for current supported scope | RULE003 evaluates confirmed exam metadata against TP-153 assessment evidence; M10 presents the structured judgment and source records | Preserve |
| PRD-21 | Missing-evidence display and evidence drill-down | Complete for current findings | Results UI tests | Extend for retained evidence types |
| PRD-22 | Downloadable report | Complete for current supported scope | On-demand immutable report generation, ownership, mappings, confidence, assessment records, rule coverage, denominator, content, PDF, API, and UI tests | Extend only for authorized retained evidence |
| PRD-23 | Analysis history | Complete with limited navigation | History API and UI tests | Add normal return-to-history and new-analysis actions |
| PRD-24 | Linked immutable reanalysis | Complete | Reanalysis API/UI tests and predecessor migration | Include retained outputs without changing immutability |
| PRD-25 | Download blank TP-153 template | Deferred pending artifact | No approved non-confidential blank template is present | Add download only after an approved artifact is supplied |
| PRD-26 | Download TP-153 completion guide | Retained | No guide artifact or route exists | Build only from approved fields and required sections |
| PRD-27 | View required TP-153 sections | Retained | Extractor already names CLO, topic, and assessment sections | Add API/UI reference |
| PRD-28 | Guidance for missing, incomplete, unreadable, or invalid TP-153 | Partial | Upload errors and missing-section evidence exist | Add pre-upload and processing guidance without inferring content |
| PRD-29 | No manual official CLO/topic/assessment/mapping entry or inferred course data | Complete through M9 supported scope | Review source-set controls plus semantic allowlists, same-analysis provenance, controlled-target validation, and invention-rejection tests | Preserve through M10-M11 presentation and release validation |
| PRD-30 | Reports and reanalyses never overwrite prior results | Complete | Immutable report and predecessor tests | Preserve |
| PRD-31 | Advisory scope and documented exclusions | Complete | Prompt, report, UI, provider-production guards, and governance disclaimers | Preserve local/fake development restrictions and approved-provider requirements |

## SRS functional traceability

| Requirement | Status | Current implementation/tests | Remaining Version 1 work |
|---|---|---|---|
| FR-001 Create an analysis | Complete | Analysis API and frontend upload-flow tests | Navigation only |
| FR-002 Select Midterm or Final | Complete | Schema and frontend validation tests | None |
| FR-003 Upload one exam and one TP-153 | Complete | Upload API and dual-file state tests | Assistance controls |
| FR-004 Validate type, signature, size, readability, and availability | Complete | Upload-time parser validation plus file/upload and stored-availability tests | Preserve |
| FR-005 Extract page-aware digital content | Complete for current text | Digital extractor and persistence tests | Retained structured evidence |
| FR-006 Invoke OCR for scanned/image pages through an adapter | Complete for exam pages with no digital text | OCR contract and live Tesseract test | Preserve and extend only where retained evidence permits |
| FR-007 Extract hierarchy, marks, declared total, instructions, assets, code, and structure | Partial | Hierarchy/marks/total/instruction extraction exists | Add retained metadata, assets, code, references, and associations |
| FR-008 Extract TP-153 CLOs, topics, methods, activities, hours, and percentages | Complete | TP-153 extraction/persistence/API plus UI/report assessment presentation | Preserve |
| FR-009 Create immutable source evidence | Complete for current types | Evidence persistence and ownership tests | Extend for retained evidence |
| FR-010 Retrieve versioned KB records | Complete | KB/RAG tests | Startup/readiness verification |
| FR-011 Execute deterministic and semantic rules | Partial | Existing runtime and semantic integration tests | Retained rules and explicit deferrals |
| FR-012 Return one approved status per executed rule | Complete | Domain, persistence, and semantic validation | Apply to retained evaluators |
| FR-013 Generate evidence-based explanations and recommendations | Partial coverage | Findings and recommendation tests | Retained rules |
| FR-014 Calculate approved score | Complete | Scoring/API/report/UI tests | None |
| FR-015 Display progress, counts, score, mappings, findings, missing evidence, and recommendations | Complete for current supported scope | Progress, counts, denominator, score, mapping labels, confidence, assessments, runtime coverage, findings, missing evidence, recommendations, and retries | Extend only for authorized retained evidence |
| FR-016 Generate downloadable report | Complete for current supported scope | Report content/PDF/API/UI suites include mappings, confidence, assessments, runtime coverage, denominator, evidence, provenance, and recommendations | Extend only for authorized retained evidence |
| FR-017 Store history | Complete | History API/UI tests | Navigation |
| FR-018 Create linked reanalysis | Complete | Reanalysis API/UI tests | Preserve |
| FR-019 Durable extraction review before semantic analysis | Complete | Migration `0008`, immutable revisions, revision 1, `review_ready`, GET/PUT/confirm API, controlled workspace, focused tests, and M11 end-to-end acceptance | Preserve |
| FR-020 Source-faithful review operations only | Complete for M4-M5 | Complete-snapshot validation, immutable anchors, stale/fabricated-row rejection, controlled UI, restoration/exclusion, and audit tests | No source-authoring controls are authorized |
| FR-021 No AI before extraction confirmation | Complete for M3-M5 | Provider non-invocation, centralized guards, exact confirmation claim, continuation-stage, duplicate-task, and no-pre-confirmation-Finding tests | Preserve through M6-M11 |
| FR-022 Separate source mappings from derived relationships | Complete M6-M10 | Item-level derived details reference controlled evidence, never overwrite Evidence, and are explicitly labelled in UI/report | Preserve |
| FR-023 Derived relationships reference confirmed IDs and evidence | Complete M6-M7 | Candidate allowlists, same-analysis ownership, source-type and confirmed-row provenance validation | Preserve in M10-M11 |
| FR-024 Backend-derived High/Medium/Low semantic confidence | Complete M6-M10 | Backend derives exact categorical confidence; M10 presents only the category and explicit non-scoring meaning | Preserve |
| FR-025 Low confidence becomes Not Verified and is excluded | Complete M6-M7 | Low-to-Not-Verified validation, score exclusion, and mapping-coverage exclusion tests | Preserve in M10-M11 |
| FR-026 Semantic Decision/Evidence/Reasoning/Confidence/Recommendation | Complete M6-M10 | Versioned details plus UI/report presentation include decision, evidence, concise reasoning, controlled recommendation, item judgments, confidence basis, and retrieved KB IDs | Preserve |
| FR-027 Deterministic coverage, totals, numbering, and score | Complete for current rules; planned mapping inputs | Existing rule/scoring suites | Keep deterministic while consuming validated non-Low mappings |
| FR-028 No manual/AI source facts, policies, mappings, or thresholds | Complete M4-M9 | Review source-set controls plus AI allowlist, invented-ID, cross-analysis, wrong-source, and prompt-injection rejection tests | Preserve in M10-M11 |

## Exam-facing Knowledge Base rule coverage

The controlled KB contains 21 derived exam-facing requirements:
REQ001-REQ009 and REQ011-REQ022. `CAPABILITY_MANIFEST` mirrors current runtime support and the
design-authorized target classification and is tested directly against `04_requirements.xlsx` and
`07_evaluation_rules.xlsx`.

| Rule | Requirement | Approved target method | Current implementation | Redesign status |
|---|---|---|---|---|
| RULE001 | Question-to-CLO Mapping | Semantic/hybrid | Governed item-level semantic relationship evaluator | Currently implemented M7 |
| RULE002 | CLO Relevance | Semantic/hybrid | Governed item-level evaluator with backend categorical confidence | Currently implemented M6 |
| RULE003 | Assessment Method Consistency | Semantic/hybrid with exact comparison support | Governed semantic evaluator over exam metadata and TP-153 assessment evidence | Currently implemented M8 |
| RULE004 | Question Format Suitability | Semantic/hybrid | Governed item-level evaluator with controlled CLO targets and categorical confidence | Currently implemented M6 |
| RULE005 | Applicable CLO Coverage | Deterministic aggregation | Aggregates validated RULE001 item relationships | Currently implemented M7 |
| RULE006 | CLO Coverage Distribution | Deterministic governed branches | Zero-CLO and one-CLO branches only | Partial; two-or-more branch Deferred |
| RULE007 | Question-to-Topic Alignment | Semantic/hybrid | Governed item-level semantic relationship evaluator | Currently implemented M7 |
| RULE008 | Out-of-Scope Content | Semantic/hybrid | Governed evaluator against controlled documented topics with categorical confidence | Currently implemented M6 |
| RULE009 | Applicable Topic Coverage | Deterministic aggregation | Aggregates validated RULE007 item relationships | Currently implemented M7 |
| RULE011 | Clear Task Statement | Semantic/hybrid | Governed question-level semantic evaluator | Currently implemented M9 |
| RULE012 | Unambiguous Wording | Semantic/hybrid | Governed question-level semantic evaluator | Currently implemented M9 |
| RULE013 | Complete Question Information | Semantic/hybrid | Governed question/context evaluator | Currently implemented M9 |
| RULE014 | Referenced Material Availability | Deterministic | No evaluator; structured asset evidence incomplete | Design-authorized / Planned retained implementation |
| RULE015 | Supporting Material Legibility | No authorized method | No evaluator | Deferred - no governed visual threshold/evaluator |
| RULE016 | Supporting Material Association | Deterministic | No evaluator; structured layout evidence incomplete | Design-authorized / Planned retained implementation |
| RULE017 | Visible Marks | No authorized method | No evaluator | Deferred - institutional policy/conditions undefined |
| RULE018 | Correct Total Marks | Deterministic | Deterministic evaluator | Currently implemented |
| RULE019 | Consistent Numbering | Deterministic | Deterministic evaluator | Currently implemented |
| RULE020 | Exam Identification | No authorized method | No evaluator | Deferred - required/essential field set undefined |
| RULE021 | Complete Instructions | Semantic/hybrid | Governed instruction/applicability evaluator | Currently implemented M8 |
| RULE022 | Resolvable Cross-References | Deterministic | No evaluator; structured reference evidence incomplete | Design-authorized / Planned retained implementation |

## System and governance rule disposition

These KB rules validate the platform or its released outputs. They do not
belong in the exam-facing capability manifest and must not create
additional scored Findings.

| Rule | Disposition | Enforcement evidence |
|---|---|---|
| RULE010 Finding Traceability | Enforced by construction | Finding-evidence validation, persistence, API, and report tests |
| RULE023 Readable Exam Input | Enforced for upload/parser readability | Upload validation rejects corrupt, truncated, and unreadable/encrypted PDFs while accepting valid scanned PDFs; processing still records safe failures |
| RULE024 Usable CLO Data | Enforced by construction | Missing-section evidence and conservative evaluators |
| RULE025 Usable Topic Data | Enforced by construction | Missing-section evidence and conservative evaluators |
| RULE026 Usable Assessment Data | Enforced by construction | Missing-section evidence and semantic preconditions |
| RULE027 Actionable Recommendation | Enforced by construction | Controlled recommendation lookup and applicability validation |
| RULE028 Exam-Level Conclusions | Enforced by construction | Scope-limited prompts, explanations, and report disclaimer |
| RULE029 Single Status per Rule | Enforced by construction | Enum/schema validation and unique `(analysis_id, rule_id)` constraint |
| RULE030 Evidence-Based Explanation | Enforced by construction | Evidence-link and structured-output validation |

## Hybrid redesign decision traceability

This table maps every M1 design decision to requirements, controlled rules/evidence, planned
components, planned tests, and implementation status. Evidence IDs refer to controlled KB evidence
types. Listing a planned component does not claim runtime support.

| Decision | Requirement mapping | Rule mapping | Evidence mapping | Planned component | Planned test | Status |
|---|---|---|---|---|---|---|
| DD-001 Evidence-gated hybrid architecture | PRD-11, FR-010-FR-014, FR-021, FR-027 | Semantic/hybrid RULE001/002/003/004/007/008/011/012/013/021; deterministic RULE005/006/009/014/016/018/019/022 | EV002, EV003, EV004, EV005, EV012, EV014, EV015, EV018, EV021, EV022, EV024 | M3-M10 processing, evidence preparation, rule evaluators, scoring | Pipeline order, no pre-confirm AI, rule classification, deterministic aggregation | M3-M9 implemented for fourteen unconditional rules plus the governed RULE006 branches; retained structured-extraction gaps remain explicit |
| DD-002 Extraction Review before AI | PRD-03, PRD-15, PRD-17, FR-019-FR-021 | RULE010, RULE023-RULE026, RULE030 | EV018, EV019, EV020, EV023 | M2 review revision; M3 pause; M4 API; M5 UI | Revision fidelity, provider non-invocation, ownership, stale revision, confirmation race | M2-M5 currently implemented |
| DD-003 Source evidence versus derived relationships | PRD-15, PRD-19, FR-022-FR-023 | RULE001, RULE007, RULE010, RULE030 | EV002, EV012, EV015, EV018, EV021, EV024 | M6 typed details/validation; M7 derived mappings; M10 labels/report | Candidate allowlist, same-analysis evidence, source/derived label, no Evidence overwrite | Runtime and M10 presentation complete |
| DD-004 Categorical semantic confidence | PRD-12-PRD-14, FR-024-FR-026 | RULE029, RULE030 | EV018, EV019, EV020, EV021, EV024 | M2 persistence; M6 semantic contract; M10 UI/report | Exact High/Medium/Low enum, backend derivation, no percentage display | Runtime complete M6; legacy numeric field is compatibility-only and non-authoritative |
| DD-005 Backend-derived confidence | PRD-11-PRD-13, FR-023-FR-025 | RULE010, RULE029, RULE030 | EV018, EV019, EV020, EV021, EV024 | M6 validation and persistence | Model cannot elevate confidence; server evidence gates and downgrade tests | Runtime complete M6 |
| DD-006 Low confidence becomes Not Verified | PRD-12-PRD-14, FR-012, FR-014, FR-025 | RULE005, RULE009, RULE029, RULE030 | EV021, EV024 | M6 validation; M7 coverage; existing scoring | Low-to-Not-Verified, score-denominator exclusion, mapping coverage exclusion | Runtime complete M6-M7 |
| DD-007 Deterministic coverage and scoring | PRD-14, FR-014, FR-027 | RULE005, RULE006, RULE009, RULE018, RULE019 | EV003, EV004, EV005, EV012, EV015, EV021, EV022, EV024 | Existing pure rules/scoring; M7 validated mapping inputs | Repeatable coverage/totals/numbering/score; confidence has no weight | Runtime complete for RULE005/009/018/019 and the governed zero/one-CLO RULE006 branches |
| DD-008 No manual creation of official evidence | PRD-29, FR-020, FR-028 | RULE024-RULE026, RULE028 | EV012, EV014, EV015, EV017, EV023 | M4 review validation; M5 controlled UI | Reject new CLO/topic/assessment/mapping records; allow correction/restoration/exclusion | M4-M5 currently implemented |
| DD-009 No AI-generated source facts | PRD-13, PRD-29, FR-023, FR-028 | RULE010, RULE024-RULE026, RULE028, RULE030 | EV002, EV004, EV012, EV014, EV015, EV017, EV018, EV021, EV023 | M6 schema/allowlists; M7-M9 evaluators | Unknown ID, invented page/text/mark/source record, prompt-injection rejection | Runtime complete through M9 supported scope |
| DD-010 Unsupported rules remain deferred | PRD-11, PRD-13, FR-011-FR-012 | RULE006 two-or-more branch, RULE015, RULE017, RULE020 | EV004, EV008, EV009, EV010, EV012, EV019, EV020, EV023 | Capability manifest and traceability only until governed dependency exists | No runtime identifier/finding; reasons remain explicit | Deferred |
| DD-011 Decision-support scope | PRD-31, FR-013, FR-028 | RULE028 | EV024 | M6-M10 prompts, validation, UI, report | Reject accreditation/attainment/compliance claims; preserve disclaimer | Runtime and M10 report presentation complete; preserve provider guards |
| DD-012 Concise reasoning, not chain-of-thought | PRD-13, PRD-15, FR-013, FR-026 | RULE027, RULE030 | EV018, EV024, EV025 | M6 output contract; M10 API/UI/report | Evidence-to-rule explanation, controlled recommendation, no private chain-of-thought | Runtime and M10 presentation complete |

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
