from __future__ import annotations

from copy import deepcopy

from app.services.ai.gemini_schema import normalize_gemini_json_schema


def test_normalizer_projects_a_compatible_copy_without_mutating_governed_schema() -> None:
    schema = {
        "$defs": {
            "Item": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "format": "uuid",
                        "minLength": 1,
                        "maxLength": 36,
                    },
                    "status": {"type": "string", "enum": ["ok"]},
                },
                "required": ["id", "status"],
            }
        },
        "type": "object",
        "properties": {
            "provider": {"type": "string", "const": "gemini"},
            "items": {
                "type": "array",
                "items": {"$ref": "#/$defs/Item"},
                "uniqueItems": True,
            },
        },
        "required": ["provider", "items"],
    }
    original = deepcopy(schema)

    normalized = normalize_gemini_json_schema(schema)

    assert schema == original
    assert normalized["properties"]["provider"] == {
        "type": "string",
        "enum": ["gemini"],
    }
    item = normalized["$defs"]["Item"]
    assert item["properties"]["id"] == {"type": "string"}
    assert item["properties"]["status"] == {
        "type": "string",
        "enum": ["ok"],
    }
    assert item["required"] == ["id", "status"]
    assert normalized["required"] == ["provider", "items"]
    assert normalized["properties"]["items"]["items"] == {
        "$ref": "#/$defs/Item"
    }
    assert "uniqueItems" not in normalized["properties"]["items"]
