# AI Governance

1. No released finding without traceable evidence.
2. Never invent CLOs, topics, assessment records, source text, pages, marks, questions,
   requirements, institutional policies, rule thresholds, or rules.
3. Never modify the uploaded exam or TP-153.
4. Clearly distinguish official-source records from derived requirements and system policies.
5. Never issue accreditation, approval, or rejection decisions.
6. Limit every conclusion to the uploaded exam and TP-153.
7. Use Not Verified when evidence is missing, unreadable, unreliable, incomplete, or insufficient.
8. Return exactly one approved status for each executed rule.
9. Keep processing failure separate from academic status.
10. Explain how cited evidence supports the status.
11. Validate structured AI output, enum values, IDs, and evidence links before storage.
12. Treat recommendations as academic support.
13. Record model/provider/version and prompt-template version without logging private document text.
14. Permit human review and preserve the original generated result in audit history.

## Approved hybrid contract

The design-authorized Version 1 evaluation order is:

`confirmed source evidence -> deterministic checks -> constrained semantic relationships -> deterministic aggregation and scoring`

This contract is approved in M1. M2 implements review-revision and categorical-confidence
persistence plus strict internal schemas. M3 creates revision 1 and pauses at `review_ready`.
M4-M5 implement controlled review/edit/confirmation APIs, the review UI, and exact-revision guarded
continuation. M6-M9 implement categorical-confidence runtime behavior, the complete ten-rule
semantic/hybrid target, deterministic relationship coverage, and explicit capability accounting.

## Extraction Review boundary

No AI evaluator may run before extraction confirmation. M3 enforces this for new analyses by
stopping the initial worker before evidence gates, KB retrieval, or rules and by applying one
central confirmation guard to every downstream handler.

Implemented Extraction Review may only:

- correct a source-faithful transcription;
- restore the original machine extraction;
- exclude a false positive; and
- confirm the reviewed extraction.

Extraction Review may not:

- create an official CLO, course topic, or assessment record;
- create a question-to-CLO or question-to-topic mapping;
- add undocumented institutional requirements; or
- accept AI-generated source records.

Review confirms transcription of uploaded documents. It is not a course-authoring, policy-authoring,
mapping, or academic-approval workflow.

## Source evidence and derived relationships

An explicit source mapping and an AI-derived semantic relationship are different concepts.
AI-derived relationships:

- are analysis outputs, not official source evidence;
- reference only existing confirmed question and target identifiers;
- cite compatible traceable evidence;
- are labeled `AI-assisted` or `derived`;
- include concise reasoning; and
- never overwrite extracted source evidence.

When required source evidence is absent, the model must not reconstruct it. The affected implemented
rule returns Not Verified or Not Applicable according to the controlled KB.

## Semantic confidence

Semantic confidence uses only `High`, `Medium`, and `Low`:

- **High**: confirmed, source-anchored, unambiguous evidence has direct textual or deterministic
  support and no material conflict.
- **Medium**: confirmed, traceable, non-conflicting evidence requires semantic interpretation.
- **Low**: evidence is missing, unreadable, incomplete, conflicting, unconfirmed, or unvalidated.

The backend, not the model, is authoritative for the final confidence level. Low confidence must
produce the academic status Not Verified and is therefore excluded from the score denominator.

Confidence is not a percentage, academic status, severity, priority, quality score, readiness label,
or scoring weight. Numeric OCR and extraction confidence are separate technical metadata and must
not be converted into semantic confidence.

Implementation coverage is also separate from academic status. An unsupported capability or a
supported rule that failed to run is reported by the rule-coverage audit; it must never be converted
to academic `Not Verified`.

## Reasoning and recommendation

A released semantic finding exposes:

- Decision;
- Evidence Used;
- Concise Reasoning;
- categorical Confidence; and
- an optional controlled Recommendation.

Reasoning is a bounded evidence-to-rule explanation. The platform must not request, store, or
display private model chain-of-thought. Recommendation text remains controlled KB content.

## Scope limitation

The platform evaluates only the uploaded Midterm or Final exam against the uploaded TP-153 and the
controlled KB. It does not establish:

- full program accreditation;
- student attainment or learning achievement;
- student, faculty, or teaching performance;
- institutional compliance beyond uploaded evidence; or
- an official accreditation, approval, or rejection decision.

See `docs/DESIGN_DECISIONS.md` for the approved alternatives, technical justification, academic
justification, consequences, and limitations.
# Extraction AI boundary

Optional extraction-stage Gemini Vision assistance is permitted before
Extraction Review only for untrusted document structure grouping. It receives
complete selected page renderings plus normalized local evidence, must reference
persisted source-line IDs where available, cannot supply canonical transcription, and cannot
produce academic findings, mappings, scores, recommendations, statuses, or
accreditation conclusions. Academic semantic evaluators remain blocked until
the exact latest Extraction Review revision is confirmed. See
[`EXTRACTION_ARCHITECTURE.md`](EXTRACTION_ARCHITECTURE.md).

Visible candidate text without a source-line match remains non-canonical until
targeted local OCR corroborates it or a reviewer explicitly resolves the
resulting blocker. Local and Gemini candidates, fresh/cache provenance, and
critical disagreements are retained for review. No chain-of-thought is
requested, stored, or displayed.
