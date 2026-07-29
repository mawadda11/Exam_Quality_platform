from __future__ import annotations

from typing import Protocol

LEGACY_CAPABILITY_VERSION = "v2-b3"
BATCH4_CAPABILITY_VERSION = "v2-b4-structured-evidence"
PILOT_CORRECTNESS_CAPABILITY_VERSION = "v2-pilot-correctness"
CURRENT_CAPABILITY_VERSION = PILOT_CORRECTNESS_CAPABILITY_VERSION

_BATCH4_CUMULATIVE_CAPABILITY_VERSIONS = frozenset(
    {
        BATCH4_CAPABILITY_VERSION,
        PILOT_CORRECTNESS_CAPABILITY_VERSION,
    }
)


class _HasCapabilityVersion(Protocol):
    capability_version: str | None


def effective_capability_version(analysis: _HasCapabilityVersion) -> str:
    """Resolve historical NULL values without mutating or backfilling old rows."""

    return analysis.capability_version or LEGACY_CAPABILITY_VERSION


def batch4_structured_rules_enabled(analysis: _HasCapabilityVersion) -> bool:
    """Keep Batch 4 governed rules enabled in every cumulative successor."""

    return (
        effective_capability_version(analysis)
        in _BATCH4_CUMULATIVE_CAPABILITY_VERSIONS
    )
