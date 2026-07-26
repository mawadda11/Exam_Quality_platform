# Version 1 Hybrid Evaluation Design Decisions

## Purpose and status

This document records the approved Version 1.1 design contract for the hybrid evaluation
workflow. It is authoritative for future implementation milestones, but approval of a design does
not mean the corresponding runtime behavior is implemented.

The repository uses four distinct status terms:

- **Design-authorized**: approved as part of the target Version 1 architecture.
- **Currently implemented**: present in the runtime and covered by tests.
- **Planned**: design-authorized but not yet implemented.
- **Deferred**: prohibited until the missing criterion, policy, or artifact is approved.

Milestone M1 changes governance and planning contracts only. M2 implements the minimum persistence
and strict internal schemas for Extraction Review and categorical semantic confidence. M3 creates
revision 1, pauses at `review_ready`, guards post-confirmation processing, and adds minimal
frontend compatibility. Review/edit/confirmation APIs, the review workspace,
categorical-confidence evaluation, and expanded semantic evaluators remain planned for M4 and
later milestones.

## DD-001 - Evidence-gated hybrid architecture

**Decision**

Use this evaluation order:

`confirmed source evidence -> deterministic checks -> constrained semantic relationships -> deterministic aggregation and scoring`

**Problem addressed**

Deterministic-only evaluation cannot judge meaning-based relationships, while unrestricted AI
evaluation would weaken reproducibility and evidence traceability.

**Chosen approach**

Keep objective extraction, validation, arithmetic, structure, coverage aggregation, and scoring
deterministic. Use semantic AI only for design-authorized relationships that require interpretation,
after mandatory evidence has been confirmed.

**Alternatives considered**

- Deterministic-only evaluation.
- AI evaluation of every rule.
- A single unconstrained prompt for the entire exam.

**Why alternatives were rejected**

Deterministic-only evaluation leaves valid semantic questions unresolved. AI evaluation of
objective rules makes reproducible calculations unnecessarily uncertain. A single broad prompt
mixes evidence and rules and is difficult to validate.

**Technical justification**

Rule-specific inputs, schemas, evidence allowlists, and deterministic post-processing create small,
testable boundaries. Provider failures remain processing failures rather than academic statuses.

**Academic justification**

Interpretive judgments are tied to documented evidence and controlled criteria, while objective
calculations remain reproducible.

**Consequences and limitations**

Some rules legitimately remain Not Verified or unavailable. Hybrid evaluation reduces avoidable
Not Verified results but does not authorize invented evidence, policies, or thresholds.

## DD-002 - Extraction Review before AI

**Decision**

No AI evaluation may occur until the Faculty Member confirms the extracted Exam and TP-153
evidence.

**Problem addressed**

OCR and parser output can contain transcription errors. Running semantic evaluation over
unreviewed extraction can produce a well-formed but academically unsupported result.

**Chosen approach**

The planned workflow pauses after extraction. Review is limited to:

- correcting an existing source-faithful transcription;
- restoring the original machine extraction;
- excluding a false positive; and
- confirming the reviewed extraction.

**Alternatives considered**

- Run AI immediately after extraction.
- Permit unrestricted editing or creation of extracted records.
- Use AI to repair extraction automatically.

**Why alternatives were rejected**

Immediate analysis treats uncertain extraction as confirmed evidence. Unrestricted editing permits
course data to be authored in the review interface. AI repair can turn model output into apparent
source evidence.

**Technical justification**

A confirmed revision gives every later rule one stable input version and supports reproducibility,
safe retries, and audit history.

**Academic justification**

Human confirmation validates transcription, not academic alignment. It prevents parsing errors
from being mistaken for document facts.

**Consequences and limitations**

M1 itself does not implement runtime behavior. M2 supplies the persistence/internal-schema
foundation. M3 now implements revision creation and the pause, with a read-only frontend handoff;
review/edit/confirmation APIs and the review workspace remain planned for M4-M5.
Missing official TP-153 content cannot be entered during review; the user must provide a corrected
official document in a new or restarted analysis.

## DD-003 - Source evidence and derived semantic relationships are separate

**Decision**

An explicit mapping written in an uploaded document and an AI-derived semantic relationship are
different records and must be labeled differently.

**Problem addressed**

Presenting an inferred relationship as an extracted mapping would make AI output appear to be an
official document fact.

**Chosen approach**

An AI-derived relationship must:

- reference existing confirmed question and target IDs;
- cite compatible source evidence;
- be labeled `AI-assisted` or `derived`;
- include concise reasoning; and
- never overwrite or masquerade as source evidence.

**Alternatives considered**

- Store inferred mappings as Exam or TP-153 evidence.
- Modify the extracted record to include the inferred relationship.
- Permit manual mapping creation during review.

**Why alternatives were rejected**

All three alternatives erase the provenance boundary between uploaded facts and analysis.

**Technical justification**

Typed derived details can reference immutable source evidence while retaining provider, prompt, and
KB provenance. Candidate IDs can be generated server-side and validated after model output.

**Academic justification**

Mapping two supplied texts is a review judgment, not proof that the relationship was explicitly
documented or institutionally approved.

**Consequences and limitations**

Official mapping absence remains visible even when a derived semantic relationship is available.
Derived relationships are decision support and may be Not Verified.

## DD-004 - Categorical semantic confidence

**Decision**

Semantic confidence uses only `High`, `Medium`, and `Low`.

**Problem addressed**

Model-generated percentages imply statistical calibration that the project has not established.

**Chosen approach**

- **High**: confirmed, source-anchored, unambiguous evidence with direct textual or deterministic
  support and no material conflict.
- **Medium**: confirmed, traceable, non-conflicting evidence where semantic interpretation is
  necessary.
- **Low**: evidence is missing, unreadable, incomplete, conflicting, unconfirmed, or unvalidated.

Confidence is not an academic status, probability, severity, priority, readiness label, quality
score, or scoring weight.

**Alternatives considered**

- Model-generated percentages.
- Numeric-to-category thresholds.
- No confidence disclosure.

**Why alternatives were rejected**

Percentages and thresholds would be arbitrary without calibration. Omitting confidence would hide
material evidence limitations from users.

**Technical justification**

Categorical conditions can be validated as domain rules. Existing numeric OCR and extraction
confidence remains separate technical metadata and must not be converted into semantic confidence.

**Academic justification**

The categories communicate the nature of support without claiming unsupported measurement
precision.

**Consequences and limitations**

The current runtime still stores and displays numeric semantic confidence. Replacement is planned
for M6 and M10; M1 does not change runtime or frontend behavior.

## DD-005 - Backend-derived confidence

**Decision**

The backend, not the model, is authoritative for semantic confidence.

**Problem addressed**

A model's self-reported certainty is uncalibrated and can conflict with observable evidence
conditions.

**Chosen approach**

The future model contract will return evidence uses, concise reasoning, and a bounded inference
basis. The backend will validate the evidence and derive or downgrade the final confidence level.

**Alternatives considered**

- Trust the model's confidence field.
- Average model and extraction confidence.
- Convert OCR confidence to semantic confidence.

**Why alternatives were rejected**

These approaches mix different measurements and allow untrusted output to control a released
finding.

**Technical justification**

Server-side derivation can enforce evidence ownership, completeness, source compatibility, target
identity, and conflict rules consistently across providers.

**Academic justification**

The reported confidence describes verified evidence conditions rather than subjective model
certainty.

**Consequences and limitations**

The model may never upgrade confidence beyond server-observed evidence. The backend may downgrade a
model-supported decision when validation discovers a limitation.

## DD-006 - Low confidence produces Not Verified

**Decision**

Low semantic confidence must produce the academic status `Not Verified`.

**Problem addressed**

Scoring a substantive conclusion when its evidence is materially uncertain could distort the
overall score.

**Chosen approach**

Low confidence is visible with its reason, receives Not Verified, and is excluded from the score
denominator under the existing scoring policy.

**Alternatives considered**

- Release a low-confidence Satisfied, Partially Satisfied, or Not Satisfied result.
- Reduce a verified status's score according to confidence.

**Why alternatives were rejected**

The first releases an academically weak conclusion. The second invents a confidence weight and
changes the approved scoring policy.

**Technical justification**

Low-to-Not-Verified is a simple validation invariant. Scoring requires no new weights or formula.

**Academic justification**

Insufficient support warrants withholding judgment, not penalizing or rewarding the exam.

**Consequences and limitations**

Not Verified results remain visible and may still be numerous where source evidence is genuinely
insufficient.

## DD-007 - Deterministic coverage and scoring

**Decision**

AI may establish validated relationships. Deterministic logic calculates coverage, total marks,
numbering outcomes, and the overall score.

**Problem addressed**

Coverage and scoring can become non-reproducible if the model directly chooses aggregate values.

**Chosen approach**

RULE005, governed branches of RULE006, RULE009, RULE018, and RULE019 remain deterministic. A Low or
Not Verified semantic mapping does not contribute to coverage. Confidence never changes the score
value of a verified academic status.

**Alternatives considered**

- Ask AI to estimate coverage percentages.
- Weight mappings or statuses by confidence.
- Assume every course CLO or topic is applicable.

**Why alternatives were rejected**

They introduce undocumented thresholds, weights, or applicability assumptions.

**Technical justification**

Pure aggregation functions are testable, explainable, and independent of AI providers.

**Academic justification**

Once governed relationships and applicable sets are established, coverage is a set-membership
calculation rather than a semantic judgment.

**Consequences and limitations**

RULE006 remains unavailable for two or more applicable CLOs until a governed concentration
criterion exists.

## DD-008 - No manual creation of official course evidence

**Decision**

Extraction Review must not create official CLOs, topics, assessment records, question-to-CLO
mappings, or question-to-topic mappings.

**Problem addressed**

Manual authoring in the review workflow could replace the required official TP-153 evidence.

**Chosen approach**

Only source-anchored correction, restoration, false-positive exclusion, and confirmation are
allowed. Undocumented institutional requirements cannot be added.

**Alternatives considered**

- Free-form CLO/topic entry.
- Manual mapping editor.
- User-authored assessment policy.

**Why alternatives were rejected**

These actions change the evidence baseline rather than review its extraction and conflict with
PRD-29.

**Technical justification**

Future review validation will restrict record identity and permitted operations.

**Academic justification**

Course specifications and institutional policy must come from approved sources, not application
users or model inference.

**Consequences and limitations**

Missing official content stays missing and causes Not Verified or Not Applicable where governed.

## DD-009 - No AI-generated source facts

**Decision**

AI must never create questions, CLOs, topics, assessment records, marks, pages, institutional
requirements, rule thresholds, or official mappings.

**Problem addressed**

Generated values can be plausible while absent from the uploaded documents.

**Chosen approach**

Semantic prompts receive server-selected evidence and candidate IDs. Outputs are validated as
untrusted derived analysis.

**Alternatives considered**

- Ask AI to complete missing TP-153 sections.
- Use general model knowledge as course scope.
- Allow AI to repair missing marks or question text.

**Why alternatives were rejected**

They convert model generation into apparent source evidence and make conclusions unverifiable.

**Technical justification**

Allowlisted IDs, exact evidence references, strict schemas, and same-analysis checks block unknown
records.

**Academic justification**

An exam-quality review must be grounded in the documents being reviewed.

**Consequences and limitations**

The system remains conservative when the documents are incomplete.

## DD-010 - Unsupported rules remain deferred

**Decision**

Keep these deferrals:

- RULE015 - Supporting Material Legibility.
- RULE017 - Visible Marks.
- RULE020 - Exam Identification.
- RULE006 - the two-or-more-applicable-CLO distribution branch.

**Problem addressed**

Each rule or branch lacks an approved visual threshold, institutional policy, required field set,
or concentration criterion.

**Chosen approach**

Do not execute or persist a finding for unavailable evaluators. Document their dependencies and
leave them outside runtime capability.

**Alternatives considered**

- Invent local thresholds.
- Ask AI for an unguided judgment.
- Emit unconditional Not Verified findings for missing capabilities.

**Why alternatives were rejected**

The first two invent policy. The third confuses absent implementation with missing analysis
evidence.

**Technical justification**

The capability manifest distinguishes current support, design authorization, and deferral.

**Academic justification**

Transparent limitation is more defensible than an unsupported conclusion.

**Consequences and limitations**

Version 1 cannot claim complete evaluation of these dimensions.

## DD-011 - Decision-support scope

**Decision**

The platform is an evidence-based decision-support tool for uploaded Midterm and Final exams, not
an automated accreditation or compliance authority.

**Problem addressed**

Scores and AI explanations could be misinterpreted as program, student, faculty, or institutional
judgments.

**Chosen approach**

Limit conclusions to the uploaded Exam and TP-153. Prohibit claims about:

- full program accreditation;
- student attainment or learning achievement;
- student or faculty performance;
- teaching quality;
- institutional compliance beyond uploaded evidence; and
- official approval, rejection, or accreditation decisions.

**Alternatives considered**

- Readiness or accreditation labels.
- Automated approve/reject decisions.
- Program-wide conclusions from one exam.

**Why alternatives were rejected**

The evidence base and Version 1 scope cannot support those claims.

**Technical justification**

Prompts, validation, API metadata, UI labels, reports, and tests will preserve the advisory scope.

**Academic justification**

One assessment artifact cannot establish program accreditation, institutional compliance, or
student attainment.

**Consequences and limitations**

The overall score summarizes only verified applicable exam-quality rules and must be presented with
status counts and evidence limitations.

## DD-012 - Concise reasoning, not private chain-of-thought

**Decision**

Every future semantic finding exposes Decision, Evidence Used, Concise Reasoning, categorical
Confidence, and an optional controlled Recommendation.

**Problem addressed**

Users need an auditable explanation, but private model chain-of-thought is neither required nor an
appropriate product artifact.

**Chosen approach**

Store and display a bounded evidence-to-rule justification: what was compared, how the controlled
condition applies, and what limitation affected the decision.

**Alternatives considered**

- Store full prompts and model chain-of-thought.
- Display a status without reasoning.
- Allow free-form generated recommendations.

**Why alternatives were rejected**

Full internal reasoning can expose private content and is not a reliable audit mechanism. A bare
status is insufficiently explainable. Free-form recommendations bypass the controlled KB.

**Technical justification**

Structured evidence IDs, concise explanation, categorical confidence, and controlled
recommendation IDs are sufficient for traceability and report generation.

**Academic justification**

An academic reviewer needs the evidence and applied criterion, not an unverifiable narrative of
the model's internal process.

**Consequences and limitations**

Reasoning is intentionally concise. Recommendation text continues to come from the controlled KB.
