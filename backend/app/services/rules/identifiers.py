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
CLO_RELEVANCE = RuleIdentifier(
    requirement_id="REQ002", rule_id="RULE002", rule_name="CLO Relevance"
)
CLO_COVERAGE_DISTRIBUTION = RuleIdentifier(
    requirement_id="REQ006", rule_id="RULE006", rule_name="CLO Coverage Distribution"
)
OUT_OF_SCOPE_CONTENT = RuleIdentifier(
    requirement_id="REQ008", rule_id="RULE008", rule_name="Out-of-Scope Content"
)
