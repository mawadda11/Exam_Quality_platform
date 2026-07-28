from __future__ import annotations

from typing import Protocol

LEGACY_CAPABILITY_VERSION = "v2-b3"
BATCH4_CAPABILITY_VERSION = "v2-b4-structured-evidence"
CURRENT_CAPABILITY_VERSION = BATCH4_CAPABILITY_VERSION


class _HasCapabilityVersion(Protocol):
    capability_version: str | None


def effective_capability_version(analysis: _HasCapabilityVersion) -> str:
    """Resolve historical NULL values without mutating or backfilling old rows."""

    return analysis.capability_version or LEGACY_CAPABILITY_VERSION


def batch4_structured_rules_enabled(analysis: _HasCapabilityVersion) -> bool:
    return effective_capability_version(analysis) == BATCH4_CAPABILITY_VERSION
