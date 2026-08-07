from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.domain import ExamType, ProcessingStage
from app.models.analysis import Analysis
from app.models.course import Course
from app.models.user import User
from app.services.ai.analysis_routing import analysis_ai_route, record_analysis_ai_route
from app.services.ai.provider import AiFailureKind, AiProviderError, AiRouteTier
from app.services.ai.sticky_failover import StickyFailoverAiProvider
from app.services.extraction.exam_structure import (
    ExamStructureParserError,
    ExamStructureProviderUnavailableError,
    StickyFailoverExamStructureParser,
    StructureParseResult,
)


class ScriptedProvider:
    def __init__(self, name: str, model: str, outcomes: list[str | Exception]) -> None:
        self._name = name
        self._model = model
        self.outcomes = list(outcomes)
        self.calls: list[dict[str, Any]] = []

    @property
    def provider_name(self) -> str:
        return self._name

    @property
    def model_name(self) -> str:
        return self._model

    def generate_structured(self, *, system: str, prompt: str, schema: dict[str, Any]) -> str:
        self.calls.append({"system": system, "prompt": prompt, "schema": schema})
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def unavailable(message: str = "temporarily unavailable") -> AiProviderError:
    return AiProviderError(message, kind=AiFailureKind.AVAILABILITY)


def test_primary_availability_failure_pins_analysis_to_fallback() -> None:
    primary = ScriptedProvider("gemini", "gemini-3.6-flash", [unavailable()])
    fallback = ScriptedProvider("gemini", "gemini-3.5-flash-lite", ['{"ok":true}', '{"ok":true}'])
    local = ScriptedProvider("local", "local-governed-baseline-v1", ['{"ok":true}'])
    changes: list[AiRouteTier] = []
    provider = StickyFailoverAiProvider(
        primary=primary,
        fallback=fallback,
        local=local,
        on_route_changed=changes.append,
    )

    result = provider.generate_structured(
        system="system",
        prompt="prompt",
        schema={
            "type": "object",
            "properties": {
                "provider": {"type": "string", "const": "gemini"},
                "model": {"type": "string", "const": "gemini-3.6-flash"},
            },
        },
    )
    provider.generate_structured(system="system", prompt="prompt-2", schema={"type": "object"})

    assert result == '{"ok":true}'
    assert provider.active_tier is AiRouteTier.FALLBACK
    assert changes == [AiRouteTier.FALLBACK]
    assert len(primary.calls) == 1
    assert len(fallback.calls) == 2
    assert fallback.calls[0]["schema"]["properties"]["model"]["const"] == "gemini-3.5-flash-lite"


def test_fallback_availability_failure_pins_analysis_to_local() -> None:
    primary = ScriptedProvider("gemini", "gemini-3.6-flash", [unavailable()])
    fallback = ScriptedProvider("gemini", "gemini-3.5-flash-lite", [unavailable()])
    local = ScriptedProvider("local", "local-governed-baseline-v1", ['{"ok":true}', '{"ok":true}'])
    changes: list[AiRouteTier] = []
    provider = StickyFailoverAiProvider(
        primary=primary,
        fallback=fallback,
        local=local,
        on_route_changed=changes.append,
    )

    provider.generate_structured(system="system", prompt="prompt", schema={"type": "object"})
    provider.generate_structured(system="system", prompt="prompt-2", schema={"type": "object"})

    assert provider.active_tier is AiRouteTier.LOCAL
    assert changes == [AiRouteTier.FALLBACK, AiRouteTier.LOCAL]
    assert len(primary.calls) == 1
    assert len(fallback.calls) == 1
    assert len(local.calls) == 2


def test_non_availability_failure_is_not_hidden_by_failover() -> None:
    primary = ScriptedProvider(
        "gemini",
        "gemini-3.6-flash",
        [AiProviderError("schema bug", kind=AiFailureKind.RESPONSE)],
    )
    fallback = ScriptedProvider("gemini", "gemini-3.5-flash-lite", ['{"ok":true}'])
    local = ScriptedProvider("local", "local-governed-baseline-v1", ['{"ok":true}'])
    provider = StickyFailoverAiProvider(primary=primary, fallback=fallback, local=local)

    with pytest.raises(AiProviderError, match="schema bug"):
        provider.generate_structured(system="system", prompt="prompt", schema={"type": "object"})

    assert provider.active_tier is AiRouteTier.PRIMARY
    assert len(fallback.calls) == 0
    assert len(local.calls) == 0


def test_new_analysis_provider_starts_from_primary_again() -> None:
    first = StickyFailoverAiProvider(
        primary=ScriptedProvider("gemini", "gemini-3.6-flash", [unavailable()]),
        fallback=ScriptedProvider("gemini", "gemini-3.5-flash-lite", ['{"ok":true}']),
        local=ScriptedProvider("local", "local-governed-baseline-v1", ['{"ok":true}']),
    )
    first.generate_structured(system="system", prompt="prompt", schema={"type": "object"})
    assert first.active_tier is AiRouteTier.FALLBACK

    second_primary = ScriptedProvider("gemini", "gemini-3.6-flash", ['{"ok":true}'])
    second = StickyFailoverAiProvider(
        primary=second_primary,
        fallback=ScriptedProvider("gemini", "gemini-3.5-flash-lite", ['{"ok":true}']),
        local=ScriptedProvider("local", "local-governed-baseline-v1", ['{"ok":true}']),
    )
    second.generate_structured(system="system", prompt="prompt", schema={"type": "object"})

    assert second.active_tier is AiRouteTier.PRIMARY
    assert len(second_primary.calls) == 1

class ScriptedStructureParser:
    def __init__(self, outcomes: list[StructureParseResult | Exception]) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    def parse(self, **kwargs: object) -> StructureParseResult:
        del kwargs
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_extraction_primary_availability_failure_uses_fallback_and_pins_it() -> None:
    primary = ScriptedStructureParser([ExamStructureProviderUnavailableError("quota")])
    fallback = ScriptedStructureParser([StructureParseResult(())])
    changes: list[AiRouteTier] = []
    parser = StickyFailoverExamStructureParser(
        primary=primary,
        fallback=fallback,
        initial_tier=AiRouteTier.PRIMARY,
        on_route_changed=changes.append,
    )

    result = parser.parse(
        source_lines=[],
        fallback_questions=[],
        reconciliation_warnings=[],
    )

    assert result.questions == ()
    assert changes == [AiRouteTier.FALLBACK]
    assert primary.calls == 1
    assert fallback.calls == 1


def test_extraction_both_models_unavailable_pins_local() -> None:
    primary = ScriptedStructureParser([ExamStructureProviderUnavailableError("quota")])
    fallback = ScriptedStructureParser([ExamStructureProviderUnavailableError("quota")])
    changes: list[AiRouteTier] = []
    parser = StickyFailoverExamStructureParser(
        primary=primary,
        fallback=fallback,
        on_route_changed=changes.append,
    )

    result = parser.parse(
        source_lines=[],
        fallback_questions=[],
        reconciliation_warnings=[],
    )

    assert changes == [AiRouteTier.FALLBACK, AiRouteTier.LOCAL]
    assert any(warning.code == "STRUCTURE_PARSER_FAILED" for warning in result.warnings)


def test_extraction_non_availability_failure_does_not_switch_to_secondary_model() -> None:
    primary = ScriptedStructureParser([ExamStructureParserError("invalid structured output")])
    fallback = ScriptedStructureParser([StructureParseResult(())])
    changes: list[AiRouteTier] = []
    parser = StickyFailoverExamStructureParser(
        primary=primary,
        fallback=fallback,
        on_route_changed=changes.append,
    )

    result = parser.parse(
        source_lines=[],
        fallback_questions=[],
        reconciliation_warnings=[],
    )

    assert changes == []
    assert fallback.calls == 0
    assert any(warning.code == "STRUCTURE_PARSER_FAILED" for warning in result.warnings)


def test_route_marker_is_sticky_per_analysis_and_new_analysis_starts_primary(
    db_engine: Engine,
) -> None:
    with Session(db_engine) as session:
        user = User(email="route@example.test", display_name="Route Test")
        course = Course(code="ROUTE101", name="Routing")
        session.add_all([user, course])
        session.flush()
        first = Analysis(
            user_id=user.id,
            course_id=course.id,
            exam_type=ExamType.FINAL,
            term="T1",
            state=ProcessingStage.EXTRACTING_EXAM,
        )
        second = Analysis(
            user_id=user.id,
            course_id=course.id,
            exam_type=ExamType.FINAL,
            term="T2",
            state=ProcessingStage.QUEUED,
        )
        session.add_all([first, second])
        session.flush()

        assert analysis_ai_route(session, first.id) is AiRouteTier.PRIMARY
        record_analysis_ai_route(
            session,
            analysis_id=first.id,
            stage=ProcessingStage.EXTRACTING_EXAM,
            tier=AiRouteTier.FALLBACK,
        )
        session.flush()
        assert analysis_ai_route(session, first.id) is AiRouteTier.FALLBACK

        record_analysis_ai_route(
            session,
            analysis_id=first.id,
            stage=ProcessingStage.APPLYING_RULES,
            tier=AiRouteTier.LOCAL,
        )
        session.flush()
        assert analysis_ai_route(session, first.id) is AiRouteTier.LOCAL
        assert analysis_ai_route(session, second.id) is AiRouteTier.PRIMARY
