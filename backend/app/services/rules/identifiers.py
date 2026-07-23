"""Official Requirement_ID/Rule_ID pairs referenced by the deterministic
rule modules, sourced directly from the approved knowledge base:
- knowledge_base/source/04_requirements.xlsx
- knowledge_base/source/07_evaluation_rules.xlsx

Centralized here so no other module hardcodes these strings. See
tests/test_rule_identifiers_kb_alignment.py for the check that these values
still exist in, and match, the current KB workbooks.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuleIdentifier:
    requirement_id: str
    rule_id: str
    rule_name: str


MARKS_AND_TOTAL = RuleIdentifier(
    requirement_id="REQ018", rule_id="RULE018", rule_name="Correct Total Marks"
)
NUMBERING = RuleIdentifier(
    requirement_id="REQ019", rule_id="RULE019", rule_name="Consistent Numbering"
)
QUESTION_TO_CLO_MAPPING = RuleIdentifier(
    requirement_id="REQ001", rule_id="RULE001", rule_name="Question-to-CLO Mapping"
)
APPLICABLE_CLO_COVERAGE = RuleIdentifier(
    requirement_id="REQ005", rule_id="RULE005", rule_name="Applicable CLO Coverage"
)
QUESTION_TO_TOPIC_ALIGNMENT = RuleIdentifier(
    requirement_id="REQ007", rule_id="RULE007", rule_name="Question-to-Topic Alignment"
)
APPLICABLE_TOPIC_COVERAGE = RuleIdentifier(
    requirement_id="REQ009", rule_id="RULE009", rule_name="Applicable Topic Coverage"
)
CLO_COVERAGE_DISTRIBUTION = RuleIdentifier(
    requirement_id="REQ006", rule_id="RULE006", rule_name="CLO Coverage Distribution"
)
# REQ002/RULE002 (CLO Relevance) and REQ008/RULE008 (Out-of-Scope Content)
# are deliberately not defined here - the M8 correction removed them from
# the runtime rule engine entirely (they require semantic judgment this
# deterministic system does not provide). They are documented as
# unsupported in app.services.rules.capability_manifest instead.
