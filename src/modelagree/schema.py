"""Shared validation for references and predictions; no label coercion."""

import json
import re


TYPES = {"categorical", "ordinal", "multi_label"}


def validate_schema(schema):
    if not isinstance(schema, dict) or not schema:
        raise ValueError("label_schema must be a nonempty mapping")
    for name, spec in schema.items():
        if not isinstance(name, str) or not name or not isinstance(spec, dict):
            raise ValueError("Each schema field needs a name and mapping")
        if spec.get("type") not in TYPES:
            raise ValueError(f"Unknown task type for {name}")
        key = "levels" if spec["type"] == "ordinal" else "labels"
        if set(spec) - {"type", key}:
            raise ValueError("Unsupported schema keys; use only type and its vocabulary")
        labels = spec.get(key)
        if (not isinstance(labels, list) or not labels
                or any(not isinstance(x, str) or not x for x in labels)
                or len(set(labels)) != len(labels)):
            raise ValueError(f"{name}.{key} must contain distinct nonempty strings")
    return schema


def allowed(spec):
    return spec["levels" if spec["type"] == "ordinal" else "labels"]


def validate_value(value, spec):
    if spec["type"] == "multi_label":
        if not isinstance(value, list):
            return "expected a list"
        if any(not isinstance(x, str) or x not in allowed(spec) for x in value):
            return "unknown label"
        if len(value) != len(set(value)):
            return "duplicate label"
        return None
    if not isinstance(value, str) or value not in allowed(spec):
        return "unknown label"
    return None


class DuplicateKey(ValueError):
    pass


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKey("duplicate JSON key")
        result[key] = value
    return result


def _constant(_):
    raise ValueError("non-finite JSON number")


def parse_response(raw, schema):
    """Extract exactly one JSON object, retaining noncanonical-format flags."""
    violations = []
    obj = None
    error = None
    text = raw.strip()
    fence = re.fullmatch(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.S | re.I)
    if fence:
        text = fence.group(1).strip()
        violations.append("markdown_fence")
    decoder = json.JSONDecoder(object_pairs_hook=_object, parse_constant=_constant)
    try:
        obj = decoder.decode(text)
        if not isinstance(obj, dict):
            error = "expected one JSON object"
            obj = None
    except (ValueError, json.JSONDecodeError) as exc:
        # Do not salvage ambiguous, malformed JSON or a nested object from it.
        # Prose around one balanced object is accepted but explicitly flagged.
        if isinstance(exc, DuplicateKey):
            error = str(exc)
        elif text.startswith("["):
            error = "malformed or multiple JSON values"
        else:
            start = text.find("{")
            try:
                candidate, end = decoder.raw_decode(text, start)
                if not isinstance(candidate, dict) or "{" in text[end:] or "}" in text[end:]:
                    raise ValueError("multiple objects")
                obj = candidate
                violations.append("surrounding_text")
            except (ValueError, json.JSONDecodeError):
                error = "missing, malformed, or multiple JSON objects"
    if obj is None:
        violations.append("invalid_json")
    elif set(obj) - set(schema):
        violations.append("extra_fields")
    fields = {}
    for name, spec in schema.items():
        reason = error if obj is None else (
            "missing field" if name not in obj else validate_value(obj[name], spec))
        fields[name] = {"valid": reason is None,
                        "value": obj[name] if reason is None else None,
                        "error": reason}
    return {"fields": fields, "format_violations": violations}
