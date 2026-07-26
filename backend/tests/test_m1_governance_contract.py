"""Guards the M1 hybrid-evaluation governance and traceability freeze.

These tests intentionally validate stable contract terms and exact controlled rule
sets. M2 persistence/internal contracts are implemented; they do not claim
that planned M3-M10 runtime behavior is implemented.
"""

from __future__ import annotations

from pathlib import Path

from app.services.rules.capability_manifest import (
    CAPABILITY_MANIFEST,
    SYSTEM_GOVERNANCE_RULE_IDS,
    DesignDisposition,
    EvaluationMode,
    SupportStatus,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS = REPO_ROOT / "docs"

SEMANTIC_TARGET = {
    "RULE001",
    "RULE002",
    "RULE003",
    "RULE004",
    "RULE007",
    "RULE008",
    "RULE011",
    "RULE012",
    "RULE013",
    "RULE021",
}
DETERMINISTIC_TARGET = {
    "RULE005",
    "RULE006",
    "RULE009",
    "RULE014",
    "RULE016",
    "RULE018",
    "RULE019",
    "RULE022",
}
DEFERRED_TARGET = {"RULE015", "RULE017", "RULE020"}
CURRENT_SEMANTIC_RUNTIME = {"RULE002", "RULE004", "RULE008"}


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _normalized(content: str) -> str:
    return " ".join(content.split())


def test_design_decisions_record_every_required_m1_decision() -> None:
    decisions = _read("docs/DESIGN_DECISIONS.md")
    for decision_number in range(1, 13):
        assert f"## DD-{decision_number:03d}" in decisions

    for required_section in (
        "**Decision**",
        "**Problem addressed**",
        "**Chosen approach**",
        "**Alternatives considered**",
        "**Why alternatives were rejected**",
        "**Technical justification**",
        "**Academic justification**",
        "**Consequences and limitations**",
    ):
        assert decisions.count(required_section) == 12


def test_authoritative_docs_distinguish_design_and_runtime_status() -> None:
    for relative_path in (
        "docs/DESIGN_DECISIONS.md",
        "docs/RAG_AND_AI_DESIGN.md",
        "docs/IMPLEMENTATION_ROADMAP.md",
        "docs/V1_TRACEABILITY_MATRIX.md",
    ):
        content = _read(relative_path)
        assert "Design-authorized" in content
        assert "Currently implemented" in content or "currently implemented" in content
        assert "Planned" in content or "planned" in content
        assert "Deferred" in content or "deferred" in content


def test_old_three_rule_approval_wording_is_removed_from_authoritative_docs() -> None:
    for relative_path in (
        "docs/RAG_AND_AI_DESIGN.md",
        "docs/IMPLEMENTATION_ROADMAP.md",
    ):
        content = _read(relative_path).lower()
        assert "approved semantic scope is exactly" not in content
        assert "explicitly approved semantic scope" not in content


def test_manifest_separates_target_method_from_current_runtime_support() -> None:
    semantic_target = {
        entry.rule_id
        for entry in CAPABILITY_MANIFEST
        if entry.target_evaluation_mode is EvaluationMode.SEMANTIC_OR_HYBRID
    }
    deterministic_target = {
        entry.rule_id
        for entry in CAPABILITY_MANIFEST
        if entry.target_evaluation_mode is EvaluationMode.DETERMINISTIC
    }
    deferred_target = {
        entry.rule_id
        for entry in CAPABILITY_MANIFEST
        if entry.design_disposition is DesignDisposition.DEFERRED
    }

    assert semantic_target == SEMANTIC_TARGET
    assert deterministic_target == DETERMINISTIC_TARGET
    assert deferred_target == DEFERRED_TARGET

    currently_supported = {
        entry.rule_id
        for entry in CAPABILITY_MANIFEST
        if entry.support_status is SupportStatus.SUPPORTED
    }
    assert CURRENT_SEMANTIC_RUNTIME.issubset(currently_supported)
    assert {"RULE003", "RULE011", "RULE012", "RULE013", "RULE021"}.isdisjoint(currently_supported)


def test_system_governance_gates_are_unscored_and_separate() -> None:
    assert SYSTEM_GOVERNANCE_RULE_IDS == {
        "RULE010",
        "RULE023",
        "RULE024",
        "RULE025",
        "RULE026",
        "RULE027",
        "RULE028",
        "RULE029",
        "RULE030",
    }
    assert SYSTEM_GOVERNANCE_RULE_IDS.isdisjoint({entry.rule_id for entry in CAPABILITY_MANIFEST})

    rag_design = _read("docs/RAG_AND_AI_DESIGN.md")
    traceability = _read("docs/V1_TRACEABILITY_MATRIX.md")
    assert "They do not create additional scored exam-facing Findings" in _normalized(rag_design)
    assert "must not create additional scored Findings" in _normalized(traceability)


def test_review_boundary_and_no_ai_before_confirmation_are_authoritative() -> None:
    governance = _read("docs/AI_GOVERNANCE.md")
    prd = _read("docs/PRD.md")
    srs = _read("docs/SRS.md")
    architecture = _read("docs/ARCHITECTURE.md")

    assert "No AI evaluator may run before extraction confirmation." in governance
    assert "correct a source-faithful transcription" in governance
    assert "create an official CLO, course topic, or assessment record" in governance
    assert "No semantic AI evaluator runs before extraction confirmation." in prd
    assert "FR-021 Prohibit AI analysis before extraction confirmation." in srs
    assert "No AI call occurs before step 5." in architecture


def test_source_and_derived_relationships_are_distinguished() -> None:
    for relative_path in (
        "docs/AI_GOVERNANCE.md",
        "docs/RAG_AND_AI_DESIGN.md",
        "docs/PRD.md",
        "docs/API_SPECIFICATION.md",
    ):
        content = _read(relative_path)
        assert "source mapping" in content.lower()
        assert "derived" in content.lower()
        normalized = _normalized(content).lower()
        assert "never overwrite" in normalized or "never overwritten" in normalized


def test_categorical_confidence_and_scoring_invariants_are_authoritative() -> None:
    governance = _read("docs/AI_GOVERNANCE.md")
    scoring = _read("docs/SCORING_POLICY.md")
    claude = _read("CLAUDE.md")

    for level in ("High", "Medium", "Low"):
        assert level in governance
        assert level in scoring

    assert "The backend, not the model, is authoritative" in governance
    normalized_scoring = _normalized(scoring)
    assert (
        "Low semantic confidence requires the academic status `Not Verified`" in normalized_scoring
    )
    assert "Confidence never changes the approved value" in normalized_scoring
    assert "must not be converted into semantic confidence" in normalized_scoring
    assert "permitted only as categorical semantic-confidence" in claude


def test_reasoning_contract_excludes_private_chain_of_thought() -> None:
    governance = _read("docs/AI_GOVERNANCE.md")
    rag_design = _read("docs/RAG_AND_AI_DESIGN.md")

    for label in (
        "Decision",
        "Evidence Used",
        "Concise Reasoning",
        "Confidence",
        "Recommendation",
    ):
        assert label in governance

    assert "must not request, store, or\ndisplay private model chain-of-thought" in governance
    assert "private chain-of-thought must not be requested, stored, or displayed" in rag_design


def test_traceability_maps_every_design_decision_and_planned_requirement() -> None:
    traceability = _read("docs/V1_TRACEABILITY_MATRIX.md")
    for decision_number in range(1, 13):
        assert f"DD-{decision_number:03d}" in traceability
    for requirement_number in range(19, 29):
        assert f"FR-{requirement_number:03d}" in traceability

    assert "Planned component" in traceability
    assert "Planned test" in traceability
    assert "EV021" in traceability


def test_current_numeric_semantic_runtime_is_documented_as_a_planned_gap() -> None:
    rag_design = _read("docs/RAG_AND_AI_DESIGN.md")
    architecture = _read("docs/ARCHITECTURE.md")
    api = _read("docs/API_SPECIFICATION.md")

    assert "current semantic provider schema still uses numeric confidence" in rag_design
    assert "Numeric semantic confidence is still stored and displayed." in architecture
    assert "current API still returns numeric finding confidence" in api


def test_m1_governance_and_m2_m3_implementation_status_are_explicit() -> None:
    schema = _read("docs/DATABASE_SCHEMA.md")
    roadmap = _read("docs/IMPLEMENTATION_ROADMAP.md")

    assert "migration `0008`" in schema
    assert "placeholder" in schema
    assert "SemanticConfidenceLevel" in schema
    assert "`decision`" in schema
    assert "does not implement\n  runtime behavior" in roadmap
    assert "M2 - Minimal persistence foundation: currently implemented." in roadmap
    assert "M3 - Pipeline pause and initial snapshot: currently implemented." in roadmap
