from __future__ import annotations

from dataclasses import dataclass

from app.services.rules.versioning import (
    BATCH4_CAPABILITY_VERSION,
    CURRENT_CAPABILITY_VERSION,
    LEGACY_CAPABILITY_VERSION,
    PILOT_CORRECTNESS_CAPABILITY_VERSION,
    batch4_structured_rules_enabled,
    effective_capability_version,
)


@dataclass
class _AnalysisVersion:
    capability_version: str | None


def test_pilot_correctness_is_the_current_cumulative_capability_version() -> None:
    assert CURRENT_CAPABILITY_VERSION == PILOT_CORRECTNESS_CAPABILITY_VERSION
    assert CURRENT_CAPABILITY_VERSION == "v2-pilot-correctness"


def test_batch4_structured_rules_remain_enabled_for_cumulative_successor() -> None:
    assert batch4_structured_rules_enabled(
        _AnalysisVersion(BATCH4_CAPABILITY_VERSION)
    )
    assert batch4_structured_rules_enabled(
        _AnalysisVersion(PILOT_CORRECTNESS_CAPABILITY_VERSION)
    )


def test_historical_null_and_legacy_versions_do_not_gain_batch4_rules() -> None:
    historical = _AnalysisVersion(None)
    assert effective_capability_version(historical) == LEGACY_CAPABILITY_VERSION
    assert not batch4_structured_rules_enabled(historical)
    assert not batch4_structured_rules_enabled(
        _AnalysisVersion(LEGACY_CAPABILITY_VERSION)
    )
