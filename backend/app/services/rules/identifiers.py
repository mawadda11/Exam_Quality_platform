"""Controlled Requirement_ID/Rule_ID pairs from the versioned knowledge base."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuleIdentifier:
    requirement_id: str
    rule_id: str
    rule_name: str


QUESTION_TO_CLO_MAPPING = RuleIdentifier("REQ001", "RULE001", "Question-to-CLO Mapping")
CLO_RELEVANCE = RuleIdentifier("REQ002", "RULE002", "CLO Relevance")
ASSESSMENT_METHOD_CONSISTENCY = RuleIdentifier("REQ003", "RULE003", "Assessment Method Consistency")
QUESTION_FORMAT_SUITABILITY = RuleIdentifier("REQ004", "RULE004", "Question Format Suitability")
APPLICABLE_CLO_COVERAGE = RuleIdentifier("REQ005", "RULE005", "Applicable CLO Coverage")
CLO_COVERAGE_DISTRIBUTION = RuleIdentifier("REQ006", "RULE006", "CLO Coverage Distribution")
QUESTION_TO_TOPIC_ALIGNMENT = RuleIdentifier("REQ007", "RULE007", "Question-to-Topic Alignment")
OUT_OF_SCOPE_CONTENT = RuleIdentifier("REQ008", "RULE008", "Out-of-Scope Content")
APPLICABLE_TOPIC_COVERAGE = RuleIdentifier("REQ009", "RULE009", "Applicable Topic Coverage")
CLEAR_TASK_STATEMENT = RuleIdentifier("REQ011", "RULE011", "Clear Task Statement")
UNAMBIGUOUS_WORDING = RuleIdentifier("REQ012", "RULE012", "Unambiguous Wording")
COMPLETE_QUESTION_INFORMATION = RuleIdentifier("REQ013", "RULE013", "Complete Question Information")
MARKS_AND_TOTAL = RuleIdentifier("REQ018", "RULE018", "Correct Total Marks")
NUMBERING = RuleIdentifier("REQ019", "RULE019", "Consistent Numbering")
COMPLETE_INSTRUCTIONS = RuleIdentifier("REQ021", "RULE021", "Complete Instructions")
