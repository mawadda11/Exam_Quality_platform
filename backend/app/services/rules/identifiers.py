"""Official Requirement_ID/Rule_ID pairs referenced by M6's deterministic
rules, sourced directly from the approved knowledge base:
- knowledge_base/source/04_requirements.xlsx
- knowledge_base/source/07_evaluation_rules.xlsx

Centralized here so no other module hardcodes these strings. See
tests/test_rule_identifiers_kb_alignment.py for the check that these values
still exist in, and match, the current KB workbooks. Full KB ingestion and
normalization is Milestone 7 scope - this module only names the two rows M6
needs.
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
