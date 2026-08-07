"""Gemini request-schema compatibility without weakening local validation."""

from __future__ import annotations

from typing import Any, cast

_REMOVED_KEYWORDS = frozenset(
    {
        "minLength",
        "maxLength",
        "pattern",
        "default",
        "examples",
        "uniqueItems",
        "minProperties",
        "maxProperties",
    }
)
_SUPPORTED_STRING_FORMATS = frozenset({"date", "date-time", "time"})


def normalize_gemini_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Return a Gemini-compatible deep copy of a governed JSON schema.

    Gemini receives this transport-only projection. The original Pydantic
    schema remains unchanged and is still used for authoritative local
    validation after generation.
    """

    def normalize(value: Any) -> Any:
        if isinstance(value, dict):
            normalized: dict[str, Any] = {}
            for key, item in value.items():
                if key in _REMOVED_KEYWORDS:
                    continue
                if key == "format" and item not in _SUPPORTED_STRING_FORMATS:
                    continue
                if key == "const":
                    normalized["enum"] = [normalize(item)]
                    continue
                normalized[key] = normalize(item)
            return normalized
        if isinstance(value, list):
            return [normalize(item) for item in value]
        return value

    return cast(dict[str, Any], normalize(schema))
