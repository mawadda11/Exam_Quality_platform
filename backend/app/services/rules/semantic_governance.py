"""Exact-ID semantic rule governance loaded from the controlled KB."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.domain import AcademicStatus
from app.services.knowledge_base.loader import load_workbook
from app.services.knowledge_base.schemas import EVALUATION_RULES, REQUIREMENTS
from app.services.rules.identifiers import RuleIdentifier


@dataclass(frozen=True)
class SemanticRuleSpec:
    identifier: RuleIdentifier
    dimension: str
    allowed_statuses: frozenset[AcademicStatus]
    satisfied_condition: str
    partially_satisfied_condition: str
    not_satisfied_condition: str
    not_verified_condition: str
    not_applicable_condition: str


@lru_cache
def _rule_rows(source_dir: Path) -> dict[str, dict[str, object]]:
    workbook = load_workbook(source_dir, EVALUATION_RULES)
    return {str(row.values["Rule_ID"]): dict(row.values) for row in workbook.rows}


@lru_cache
def _requirement_rows(source_dir: Path) -> dict[str, dict[str, object]]:
    workbook = load_workbook(source_dir, REQUIREMENTS)
    return {str(row.values["Requirement_ID"]): dict(row.values) for row in workbook.rows}


def load_semantic_rule_spec(source_dir: Path, identifier: RuleIdentifier) -> SemanticRuleSpec:
    source_dir = source_dir.resolve()
    rule = _rule_rows(source_dir).get(identifier.rule_id)
    requirement = _requirement_rows(source_dir).get(identifier.requirement_id)
    if rule is None or requirement is None:
        raise RuntimeError(
            f"Controlled KB does not contain {identifier.rule_id}/{identifier.requirement_id}."
        )
    if str(rule["Requirement_ID"]) != identifier.requirement_id:
        raise RuntimeError(f"{identifier.rule_id} points to an unexpected requirement.")
    if str(rule["Rule_Name"]) != identifier.rule_name:
        raise RuntimeError(f"{identifier.rule_id} has an unexpected controlled name.")
    raw_statuses = str(rule["Output_Statuses"])
    allowed = frozenset(AcademicStatus(value.strip()) for value in raw_statuses.split(";"))
    return SemanticRuleSpec(
        identifier=identifier,
        dimension=str(requirement["Dimension"]),
        allowed_statuses=allowed,
        satisfied_condition=str(rule["Satisfied_Condition"]),
        partially_satisfied_condition=str(rule["Partially_Satisfied_Condition"]),
        not_satisfied_condition=str(rule["Not_Satisfied_Condition"]),
        not_verified_condition=str(rule["Not_Verified_Condition"]),
        not_applicable_condition=str(rule["Not_Applicable_Condition"]),
    )
