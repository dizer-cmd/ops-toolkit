"""Output contracts.

Every tool ships a JSON Schema. The schema is doing two jobs:

  1. it is sent to the API as `output_config.format`, so the model is
     constrained at generation time rather than corrected afterwards;
  2. it is re-checked locally on the way back, because "the platform promised"
     is not evidence -- a governance team wants to see the check.

If `jsonschema` is installed we use it. If not we fall back to the subset
validator below, so the demo runs on a clean Python install. The subset covers
what the tool schemas here actually use; `opsq verify` fails loudly if a schema
reaches for a keyword the fallback does not implement.
"""

from __future__ import annotations

SUPPORTED = {
    "type", "properties", "required", "additionalProperties", "items",
    "enum", "minimum", "maximum", "maxLength", "minItems", "description",
    "title", "$schema", "format", "maxItems",
}

_TYPES = {
    "object": dict, "array": list, "string": str,
    "integer": int, "number": (int, float), "boolean": bool, "null": type(None),
}

try:  # pragma: no cover - depends on environment
    import jsonschema as _js
except ImportError:  # pragma: no cover
    _js = None


class ContractError(Exception):
    pass


def unsupported_keywords(schema: dict, path: str = "$") -> list[str]:
    """Keywords the fallback validator cannot honour. Used by `opsq verify`."""
    found = []
    for key, value in schema.items():
        if key not in SUPPORTED:
            found.append(f"{path}.{key}")
        if key == "properties" and isinstance(value, dict):
            for name, sub in value.items():
                found += unsupported_keywords(sub, f"{path}.properties.{name}")
        if key == "items" and isinstance(value, dict):
            found += unsupported_keywords(value, f"{path}.items")
    return found


def _check(node, schema: dict, path: str, errors: list[str]) -> None:
    expected = schema.get("type")
    if expected:
        # `"type": ["string", "null"]` is how a nullable field is written
        options = expected if isinstance(expected, list) else [expected]
        # bool is an int subclass in Python; an integer field must not accept True
        numeric_only = all(o in ("integer", "number") for o in options)
        if numeric_only and isinstance(node, bool):
            errors.append(f"{path}: expected {expected}, got boolean")
            return
        accepted = tuple(t for o in options for t in
                         (_TYPES[o] if isinstance(_TYPES.get(o), tuple) else (_TYPES.get(o),))
                         if t is not None)
        if accepted and not isinstance(node, accepted):
            errors.append(f"{path}: expected {expected}, got {type(node).__name__}")
            return
        if node is None:
            return  # nothing further to check on a null
        expected = next((o for o in options if isinstance(node, _TYPES.get(o, ()))), options[0])

    if "enum" in schema and node not in schema["enum"]:
        errors.append(f"{path}: {node!r} not one of {schema['enum']}")

    if expected == "object":
        props = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in node:
                errors.append(f"{path}: missing required field {name!r}")
        if schema.get("additionalProperties") is False:
            for name in node:
                if name not in props:
                    errors.append(f"{path}: unexpected field {name!r}")
        for name, sub in props.items():
            if name in node:
                _check(node[name], sub, f"{path}.{name}", errors)

    elif expected == "array":
        if "minItems" in schema and len(node) < schema["minItems"]:
            errors.append(f"{path}: needs at least {schema['minItems']} items")
        if "maxItems" in schema and len(node) > schema["maxItems"]:
            errors.append(f"{path}: at most {schema['maxItems']} items")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for i, item in enumerate(node):
                _check(item, item_schema, f"{path}[{i}]", errors)

    elif expected == "string":
        if "maxLength" in schema and len(node) > schema["maxLength"]:
            errors.append(f"{path}: {len(node)} chars, max {schema['maxLength']}")

    elif expected in ("integer", "number"):
        if "minimum" in schema and node < schema["minimum"]:
            errors.append(f"{path}: {node} below minimum {schema['minimum']}")
        if "maximum" in schema and node > schema["maximum"]:
            errors.append(f"{path}: {node} above maximum {schema['maximum']}")


def validate(payload, schema: dict) -> list[str]:
    """Return a list of human-readable problems. Empty list means valid."""
    if _js is not None:
        validator = _js.Draft202012Validator(schema)
        return [
            f"${''.join(f'.{p}' if isinstance(p, str) else f'[{p}]' for p in e.absolute_path)}: {e.message}"
            for e in sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
        ]
    errors: list[str] = []
    _check(payload, schema, "$", errors)
    return errors


def backend() -> str:
    return "jsonschema" if _js is not None else "builtin-subset"
