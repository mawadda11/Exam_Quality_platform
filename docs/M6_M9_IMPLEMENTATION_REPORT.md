# M6-M9 Implementation Report

## Delivered hybrid core

M6-M9 now execute the confirmed-evidence, governed-KB, semantic-relationship, and deterministic
aggregation workflow. The implementation expands the semantic runtime from three rules to the
complete ten-rule design-authorized set and makes the distinction between missing academic evidence
and missing system capability explicit.

## Key changes

### Evidence and knowledge retrieval

- Added confirmed exam-type metadata evidence for assessment consistency.
- Preserved question, CLO, topic, assessment, instruction, page, and source-document provenance.
- Retrieval queries are constrained by the exact governed rule ID, requirement, dimension, and KB
  version.
- Chroma remains optional/lazy; deterministic in-memory retrieval supports tests and native demos.

### Governed semantic output

The provider returns item judgments only. The backend validates and derives:

- exact aggregate academic status;
- categorical confidence (`High`, `Medium`, `Low`);
- exact evidence union;
- same-analysis and source-type provenance;
- controlled target references;
- controlled recommendation applicability; and
- prompt, provider/model, and KB version provenance.

Low confidence is forcibly released as `Not Verified`. Numeric OCR/extraction confidence is never
converted to semantic confidence. The existing numeric finding field remains only as a derived
compatibility value (High=1, Medium=.5, Low=0) and is not authoritative.

### Semantic and hybrid rules

- RULE001 / RULE007 persist derived question-to-CLO/topic relationships.
- RULE002 / RULE004 / RULE008 use the new categorical contract.
- RULE003 evaluates documented assessment-method consistency.
- RULE011 / RULE012 / RULE013 evaluate bounded question-writing properties.
- RULE021 evaluates instruction completeness/applicability.
- RULE005 / RULE009 aggregate validated mappings deterministically.
- RULE018 / RULE019 remain deterministic.
- RULE006 retains only its officially governed zero/one-CLO branches.

### Offline development provider

`AI_PROVIDER=local` is a transparent, evidence-grounded development baseline that makes no network
calls and is blocked in production. It uses explicit controlled identifiers and auditable shared
normalized concepts; it is not an approved institutional semantic model and must not be represented
as calibrated academic validity. `AI_PROVIDER=fake` remains reserved for scripted schema/failure
tests. Anthropic remains an optional adapter when privacy approval and an exact approved model/API
key are configured.

### Runtime coverage audit

`GET /api/v1/analyses/{id}/rule-coverage` accounts for all 21 exam-facing rules. It reports:

- `evaluated` when a Finding exists;
- `conditional_capability_gap` for the unsupported branch of a partially supported rule;
- `unsupported` for explicitly retained/deferred capabilities; and
- `not_run` if a rule declared supported failed to persist a Finding.

These operational dispositions are not academic statuses. In particular, `not_run` is never
converted to `Not Verified`.

## Remaining work

M10 owns presentation/report refinement for categorical confidence, item mappings, coverage audit,
and denominator transparency. M11 owns integrated release validation. RULE014/016/022 still require
structured referenced-material/layout extraction; RULE015/017/020 remain deferred for missing
authorized methods/policies.
