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
contracts only. M2 implements the dormant review-revision/categorical-confidence persistence and
strict internal schemas, but does not create revisions, pause processing, expose API/UI behavior,
or change semantic evaluation.

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
| PRD-09 | Extract TP-153 CLOs, topics, methods, activities, hours, and percentages | Complete in backend | TP-153 extraction, persistence, and read endpoint tests | Present assessment records in UI and report |
| PRD-10 | Versioned KB validation and retrieval | Complete | KB validation/normalization/provenance and semantic retrieval suites | Add repeatable startup/readiness verification |
| PRD-11 | Deterministic and semantic rule evaluation | Partial; hybrid redesign Design-authorized | Nine fully supported rules and partial RULE006; current RAG-backed runtime is RULE002/004/008 | Implement the planned ten-rule semantic/hybrid target without changing deterministic aggregation or deferrals |
| PRD-12 | Exactly five academic statuses | Complete | Domain enum, persistence, scoring, and semantic-output validation tests | Extend the same validation to retained evaluators |
| PRD-13 | Missing or insufficient evidence becomes Not Verified | Complete for implemented evaluators | Rule, pipeline, and semantic governance tests | Extend evidence-conditioned behavior to retained rules |
| PRD-14 | Exact deterministic scoring and Insufficient Evidence | Complete | Scoring, API, UI, and report tests | No formula changes |
| PRD-15 | Finding and evidence traceability | Complete for current evidence; reviewed/derived distinction Planned | Persistence, API, UI drill-down, and report tests | Bind later findings to confirmed evidence and label source versus derived mappings |
| PRD-16 | Controlled actionable recommendations | Complete for current findings | Exact KB lookup and recommendation API tests | Reuse existing KB recommendation IDs for retained rules |
| PRD-17 | Background progress and safe failure states | Partial; review pause Planned | Runner, progress, rollback, and non-blocking tests | Pause after extraction, prohibit AI before confirmation, then continue from confirmed evidence |
| PRD-18 | Six-section results interface | Complete structurally | Results component suites | Add mappings, assessments, retained findings, navigation, and retry |
| PRD-19 | Explicit and derived question-to-CLO/topic relationships | Design-authorized / Planned | Existing citation rules produce evidence but no structured pair output | Preserve explicit mappings as source facts; expose separately labeled AI-derived relationships referencing confirmed IDs |
| PRD-20 | Assessment-method consistency | Retained | TP-153 assessment data is already extracted | Implement RULE003 and present assessment evidence |
| PRD-21 | Missing-evidence display and evidence drill-down | Complete for current findings | Results UI tests | Extend for retained evidence types |
| PRD-22 | Downloadable report | Complete | On-demand report generation, ownership, content, PDF, API, and UI tests | Add retained mappings and assessment content |
| PRD-23 | Analysis history | Complete with limited navigation | History API and UI tests | Add normal return-to-history and new-analysis actions |
| PRD-24 | Linked immutable reanalysis | Complete | Reanalysis API/UI tests and predecessor migration | Include retained outputs without changing immutability |
| PRD-25 | Download blank TP-153 template | Deferred pending artifact | No approved non-confidential blank template is present | Add download only after an approved artifact is supplied |
| PRD-26 | Download TP-153 completion guide | Retained | No guide artifact or route exists | Build only from approved fields and required sections |
| PRD-27 | View required TP-153 sections | Retained | Extractor already names CLO, topic, and assessment sections | Add API/UI reference |
| PRD-28 | Guidance for missing, incomplete, unreadable, or invalid TP-153 | Partial | Upload errors and missing-section evidence exist | Add pre-upload and processing guidance without inferring content |
| PRD-29 | No manual official CLO/topic/assessment/mapping entry or inferred course data | Complete for current behavior; review enforcement Planned | Extraction and governance behavior | Future review permits only correction, restoration, false-positive exclusion, and confirmation |
| PRD-30 | Reports and reanalyses never overwrite prior results | Complete | Immutable report and predecessor tests | Preserve |
| PRD-31 | Advisory scope and documented exclusions | Complete | Prompt, report, UI, and governance disclaimers | Preserve fake provider as default |

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
| FR-019 Durable extraction review before semantic analysis | Partial: M2 foundation implemented; M3-M5 behavior planned | Migration `0008`, immutable revision ORM, strict source-faithful snapshot contract, and focused schema/model/migration tests | Create revision 1, pause processing, then add review API and UI |
| FR-020 Source-faithful review operations only | Design-authorized / Planned M4-M5 | M1 governance-contract tests only | Permit correction/restoration/exclusion/confirmation; reject source authoring |
| FR-021 No AI before extraction confirmation | Design-authorized / Planned M3-M4 | M1 governance-contract tests only | Add worker/provider non-invocation and state-transition tests |
| FR-022 Separate source mappings from derived relationships | Design-authorized / Planned M6-M7 | M1 manifest/traceability tests | Add labeled typed derived details without overwriting Evidence |
| FR-023 Derived relationships reference confirmed IDs and evidence | Design-authorized / Planned M6-M7 | M1 manifest/traceability tests | Add candidate-ID and same-analysis validation |
| FR-024 Backend-derived High/Medium/Low semantic confidence | Partial: M2 enum/persistence implemented; M6 behavior planned | Shared authoritative `SemanticConfidenceLevel`, nullable Finding column, and contract tests; current runtime remains numeric | Add backend evidence-condition derivation and Low-to-Not-Verified enforcement |
| FR-025 Low confidence becomes Not Verified and is excluded | Design-authorized / Planned M6-M7 | Existing Not Verified scoring exclusion is implemented | Add Low-to-Not-Verified and coverage-exclusion tests |
| FR-026 Semantic Decision/Evidence/Reasoning/Confidence/Recommendation | Partial: M2 internal core contract implemented; M6-M10 runtime/presentation planned | Versioned `decision`/`evidence_used`/`reasoning`/`recommendation` schema; current findings still expose numeric confidence | Populate validated details, expose categorical contract, and present concise reasoning without chain-of-thought |
| FR-027 Deterministic coverage, totals, numbering, and score | Complete for current rules; planned mapping inputs | Existing rule/scoring suites | Keep deterministic while consuming validated non-Low mappings |
| FR-028 No manual/AI source facts, policies, mappings, or thresholds | Design-authorized; current no-inference behavior implemented; review enforcement Planned | Existing extraction/governance tests plus M1 contract tests | Add review/AI boundary rejection tests |

## Exam-facing Knowledge Base rule coverage

The controlled KB contains 21 derived exam-facing requirements:
REQ001-REQ009 and REQ011-REQ022. `CAPABILITY_MANIFEST` mirrors current runtime support and the
design-authorized target classification and is tested directly against `04_requirements.xlsx` and
`07_evaluation_rules.xlsx`.

| Rule | Requirement | Approved target method | Current implementation | Redesign status |
|---|---|---|---|---|
| RULE001 | Question-to-CLO Mapping | Semantic/hybrid with exact-citation fast path | Deterministic exact citation | Design-authorized / Planned M7 |
| RULE002 | CLO Relevance | Semantic/hybrid | Governed semantic evaluator with numeric confidence | Currently implemented; categorical migration Planned M6 |
| RULE003 | Assessment Method Consistency | Semantic/hybrid with deterministic exact comparison | No evaluator | Design-authorized / Planned M8 |
| RULE004 | Question Format Suitability | Semantic/hybrid | Governed semantic evaluator with numeric confidence | Currently implemented; categorical/mapping migration Planned M6-M7 |
| RULE005 | Applicable CLO Coverage | Deterministic aggregation | Deterministic evaluator | Currently implemented; confirmed semantic inputs Planned M7 |
| RULE006 | CLO Coverage Distribution | Deterministic governed branches | Zero-CLO and one-CLO branches only | Partial; two-or-more branch Deferred |
| RULE007 | Question-to-Topic Alignment | Semantic/hybrid with exact-citation fast path | Deterministic exact citation | Design-authorized / Planned M7 |
| RULE008 | Out-of-Scope Content | Semantic/hybrid | Governed semantic evaluator with numeric confidence | Currently implemented; categorical/confirmed-scope migration Planned M6-M7 |
| RULE009 | Applicable Topic Coverage | Deterministic aggregation | Deterministic evaluator | Currently implemented; confirmed semantic inputs Planned M7 |
| RULE011 | Clear Task Statement | Semantic/hybrid | No evaluator | Design-authorized / Planned M9 |
| RULE012 | Unambiguous Wording | Semantic/hybrid | No evaluator | Design-authorized / Planned M9 |
| RULE013 | Complete Question Information | Semantic/hybrid | No evaluator | Design-authorized / Planned M9 |
| RULE014 | Referenced Material Availability | Deterministic | No evaluator; structured asset evidence incomplete | Design-authorized / Planned retained implementation |
| RULE015 | Supporting Material Legibility | No authorized method | No evaluator | Deferred - no governed visual threshold/evaluator |
| RULE016 | Supporting Material Association | Deterministic | No evaluator; structured layout evidence incomplete | Design-authorized / Planned retained implementation |
| RULE017 | Visible Marks | No authorized method | No evaluator | Deferred - institutional policy/conditions undefined |
| RULE018 | Correct Total Marks | Deterministic | Deterministic evaluator | Currently implemented |
| RULE019 | Consistent Numbering | Deterministic | Deterministic evaluator | Currently implemented |
| RULE020 | Exam Identification | No authorized method | No evaluator | Deferred - required/essential field set undefined |
| RULE021 | Complete Instructions | Semantic/hybrid | No evaluator | Design-authorized / Planned M8 |
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
| DD-001 Evidence-gated hybrid architecture | PRD-11, FR-010-FR-014, FR-021, FR-027 | Semantic/hybrid RULE001/002/003/004/007/008/011/012/013/021; deterministic RULE005/006/009/014/016/018/019/022 | EV002, EV003, EV004, EV005, EV012, EV014, EV015, EV018, EV021, EV022, EV024 | M3-M10 processing, evidence preparation, rule evaluators, scoring | Pipeline order, no pre-confirm AI, rule classification, deterministic aggregation | Design-authorized / Planned; current runtime remains uninterrupted |
| DD-002 Extraction Review before AI | PRD-03, PRD-15, PRD-17, FR-019-FR-021 | RULE010, RULE023-RULE026, RULE030 | EV018, EV019, EV020, EV023 | M2 review revision; M3 pause; M4 API; M5 UI | Revision fidelity, provider non-invocation, ownership, stale revision, confirmation race | M2 persistence implemented; workflow Planned |
| DD-003 Source evidence versus derived relationships | PRD-15, PRD-19, FR-022-FR-023 | RULE001, RULE007, RULE010, RULE030 | EV002, EV012, EV015, EV018, EV021, EV024 | M6 typed details/validation; M7 derived mappings; M10 labels/report | Candidate allowlist, same-analysis evidence, source/derived label, no Evidence overwrite | Design-authorized / Planned |
| DD-004 Categorical semantic confidence | PRD-12-PRD-14, FR-024-FR-026 | RULE029, RULE030 | EV018, EV019, EV020, EV021, EV024 | M2 persistence; M6 semantic contract; M10 UI/report | Exact High/Medium/Low enum, no numeric conversion, no percentage display | M2 enum/persistence implemented; numeric runtime currently implemented |
| DD-005 Backend-derived confidence | PRD-11-PRD-13, FR-023-FR-025 | RULE010, RULE029, RULE030 | EV018, EV019, EV020, EV021, EV024 | M6 validation and persistence | Model cannot elevate confidence; server evidence gates and downgrade tests | Design-authorized / Planned |
| DD-006 Low confidence becomes Not Verified | PRD-12-PRD-14, FR-012, FR-014, FR-025 | RULE005, RULE009, RULE029, RULE030 | EV021, EV024 | M6 validation; M7 coverage; existing scoring | Low-to-Not-Verified, score-denominator exclusion, mapping coverage exclusion | Design-authorized / Planned; Not Verified scoring exclusion currently implemented |
| DD-007 Deterministic coverage and scoring | PRD-14, FR-014, FR-027 | RULE005, RULE006, RULE009, RULE018, RULE019 | EV003, EV004, EV005, EV012, EV015, EV021, EV022, EV024 | Existing pure rules/scoring; M7 validated mapping inputs | Repeatable coverage/totals/numbering/score; confidence has no weight | Currently implemented for current inputs; confirmed semantic inputs Planned |
| DD-008 No manual creation of official evidence | PRD-29, FR-020, FR-028 | RULE024-RULE026, RULE028 | EV012, EV014, EV015, EV017, EV023 | M4 review validation; M5 controlled UI | Reject new CLO/topic/assessment/mapping records; allow correction/restoration/exclusion | Design-authorized / Planned; current no-entry boundary implemented |
| DD-009 No AI-generated source facts | PRD-13, PRD-29, FR-023, FR-028 | RULE010, RULE024-RULE026, RULE028, RULE030 | EV002, EV004, EV012, EV014, EV015, EV017, EV018, EV021, EV023 | M6 schema/allowlists; M7-M9 evaluators | Unknown ID, invented page/text/mark/source record, prompt-injection rejection | Design-authorized / Planned; current validators partially enforce |
| DD-010 Unsupported rules remain deferred | PRD-11, PRD-13, FR-011-FR-012 | RULE006 two-or-more branch, RULE015, RULE017, RULE020 | EV004, EV008, EV009, EV010, EV012, EV019, EV020, EV023 | Capability manifest and traceability only until governed dependency exists | No runtime identifier/finding; reasons remain explicit | Deferred |
| DD-011 Decision-support scope | PRD-31, FR-013, FR-028 | RULE028 | EV024 | M6-M10 prompts, validation, UI, report | Reject accreditation/attainment/compliance claims; preserve disclaimer | Current advisory scope implemented; expanded-rule preservation Planned |
| DD-012 Concise reasoning, not chain-of-thought | PRD-13, PRD-15, FR-013, FR-026 | RULE027, RULE030 | EV018, EV024, EV025 | M6 output contract; M10 API/UI/report | Evidence-to-rule explanation, controlled recommendation, no private chain-of-thought | M2 internal details core implemented; runtime/presentation Planned |

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
