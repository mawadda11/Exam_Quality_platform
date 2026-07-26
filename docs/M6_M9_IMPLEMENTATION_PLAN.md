# M6-M9 Implementation Plan

## Goal

Activate the governed hybrid evaluation core after confirmed Extraction Review. The priority is not
to manufacture more positive results; it is to ensure that every supported exam-facing requirement
is actually executed and that `Not Verified` appears only for genuine evidence insufficiency.

## M6 - Governed semantic contract and evidence construction

- Build confirmed `exam_metadata` and missing-input evidence without inventing source facts.
- Replace provider-supplied numeric semantic confidence with backend-derived `High`, `Medium`, or
  `Low`.
- Validate exact rule/requirement IDs, same-analysis evidence ownership, compatible evidence types,
  controlled target IDs, prompt/KB/provider provenance, and controlled recommendations.
- Require one item judgment per required source evidence row.
- Force Low confidence to `Not Verified`.
- Migrate RULE002, RULE004, and RULE008 to the categorical contract.

## M7 - Semantic relationships and deterministic coverage

- Evaluate RULE001 Question-to-CLO Mapping and RULE007 Question-to-Topic Alignment from confirmed
  question and controlled TP-153 target evidence.
- Persist derived item-level relationships on Findings; never overwrite extracted source evidence.
- Calculate RULE005 and RULE009 deterministically from validated relationship judgments.
- Exclude Low/Not Verified mappings from positive coverage.

## M8 - Assessment and instruction consistency

- Evaluate RULE003 against confirmed exam-type metadata and TP-153 assessment records.
- Evaluate RULE021 against confirmed question/instruction evidence and the governed applicability
  conditions.
- Preserve the partial RULE006 contract: zero CLOs = Not Verified; one CLO = Not Applicable; two or
  more CLOs remain an explicit capability gap because no official concentration threshold exists.

## M9 - Question-writing semantics and complete runtime accounting

- Evaluate RULE011 Clear Task Statement, RULE012 Unambiguous Wording, and RULE013 Complete Question
  Information.
- Add an owner-scoped rule-coverage audit that accounts for all 21 exam-facing rules separately
  from academic statuses.
- Report supported rules that unexpectedly did not run as `not_run`, unsupported/deferred rules as
  capability facts, and conditional partial branches explicitly. Never disguise a system gap as
  academic `Not Verified`.

## Runtime scope after M9

Fully supported runtime rules:

- Semantic/hybrid: RULE001, RULE002, RULE003, RULE004, RULE007, RULE008, RULE011, RULE012, RULE013,
  RULE021.
- Deterministic: RULE005, RULE009, RULE018, RULE019.
- Partially supported: RULE006 governed zero/one-CLO branches.

Explicit remaining capability gaps:

- Structured extraction dependency: RULE014, RULE016, RULE022.
- No authorized method/policy: RULE015, RULE017, RULE020.
- Undefined two-or-more-CLO concentration branch: RULE006.

## Acceptance criteria

- Complete Exam + TP-153 runs all 14 unconditional supported rules.
- Every semantic result has categorical confidence, validated evidence, item judgments, concise
  reasoning, exact model/prompt/KB provenance, and controlled recommendation handling.
- Full inputs do not default semantic rules to `Not Verified`.
- Missing official source data produces genuine Low/Not Verified only for dependent rules; unrelated
  rules still execute.
- Coverage audit accounts for all 21 exam-facing rules with no silent omissions.
- Invalid semantic output fails processing and rolls back all findings.
- Existing scoring remains unchanged: Satisfied=1, Partial=.5, Not Satisfied=0, excluding Not
  Verified and Not Applicable.
