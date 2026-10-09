"""Dependency-free JSON Schema (draft 2020-12 subset) validator.

The Stage-2 venv (``ScienceClawHackathon/.venv``) has no ``jsonschema``
installed, and the program forbids adding third-party dependencies without
proven necessity. This module implements exactly the keyword subset used by
the schemas in ``schemas/`` — no more:

    type (single or list), required, properties, additionalProperties
    (false / object), pattern, propertyNames, minLength, minimum,
    minProperties, const, enum, allOf, if/then/else, $schema, $id,
    title, description (ignored), and boolean schemas (true/false).

Semantics follow draft 2020-12: unknown keywords are ignored, `if` with a
failing schema is valid on its own, and `additionalProperties` applies only
to members not covered by `properties`.

If ``jsonschema`` IS installed (e.g. in a different environment), prefer it
via :func:`has_jsonschema`; the two agree on this keyword subset except that
``const``/``enum`` compare with strict Python type identity, so ``1 != 1.0``
(stricter than ``jsonschema``, which accepts ``1.0`` for ``const 1``).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List

from repliclaw.canonical import canonical_json, sha256_hex

_SCHEMAS_DIR = Path(__file__).resolve().parent / "schemas"

# Map of record kind -> (schema file, canonical schema string).
SCHEMA_FILES = {
    "run_record": ("run_record.schema.json", "repliclaw.run_record/v1"),
    "case_manifest": ("case_manifest.schema.json", "repliclaw.benchmark_case_manifest/v1"),
    "provenance": ("provenance.schema.json", "repliclaw.provenance/v1"),
    "scorer_output": ("scorer_output.schema.json", "repliclaw.scorer_output/v1"),
}

_TYPE_MAP = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}


@dataclass
class ValidationError:
    """One schema violation: JSON-path location + message."""

    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


@dataclass
class ValidationReport:
    errors: List[ValidationError] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _type_matches(instance: Any, expected: str) -> bool:
    py = _TYPE_MAP[expected]
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if expected == "boolean":
        return isinstance(instance, bool)
    return isinstance(instance, py) and not (
        expected in ("integer", "number", "boolean") and isinstance(instance, bool)
    )


def _check(instance: Any, schema: Any, path: str, report: ValidationReport, depth: int = 0) -> None:
    if depth > 64:
        report.errors.append(ValidationError(path, "schema nesting depth exceeded"))
        return
    if schema is True:
        return
    if schema is False:
        report.errors.append(ValidationError(path, "schema is false (value forbidden)"))
        return
    if not isinstance(schema, dict):
        raise ValueError(f"invalid schema at {path}: expected object or boolean")

    if "const" in schema:
        if not _equal(instance, schema["const"]):
            report.errors.append(
                ValidationError(path, f"must equal const {schema['const']!r}, got {instance!r}")
            )

    if "enum" in schema:
        if not any(_equal(instance, v) for v in schema["enum"]):
            report.errors.append(ValidationError(path, f"must be one of {schema['enum']!r}"))

    if "type" in schema:
        types = schema["type"]
        types = [types] if isinstance(types, str) else list(types)
        if not any(_type_matches(instance, t) for t in types):
            report.errors.append(ValidationError(path, f"type must be one of {types!r}, got {type(instance).__name__}"))

    if isinstance(instance, str):
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            report.errors.append(ValidationError(path, f"{instance!r} does not match pattern {schema['pattern']!r}"))
        if "minLength" in schema and len(instance) < schema["minLength"]:
            report.errors.append(ValidationError(path, f"string shorter than minLength {schema['minLength']}"))

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            report.errors.append(ValidationError(path, f"{instance} < minimum {schema['minimum']}"))

    if isinstance(instance, dict):
        if "required" in schema:
            for key in schema["required"]:
                if key not in instance:
                    report.errors.append(ValidationError(path, f"missing required property {key!r}"))
        if "minProperties" in schema and len(instance) < schema["minProperties"]:
            report.errors.append(
                ValidationError(
                    path,
                    f"object has {len(instance)} properties, "
                    f"minProperties is {schema['minProperties']}",
                )
            )
        props = schema.get("properties", {})
        pnames = schema.get("propertyNames")
        addl = schema.get("additionalProperties", True)
        for key, value in instance.items():
            if pnames is not None and not _name_ok(key, pnames):
                report.errors.append(ValidationError(path, f"property name {key!r} violates propertyNames"))
            if key in props:
                _check(value, props[key], f"{path}.{key}", report, depth + 1)
            else:
                if addl is False:
                    report.errors.append(ValidationError(path, f"additional property {key!r} not allowed"))
                elif isinstance(addl, (dict, bool)):
                    _check(value, addl, f"{path}.{key}", report, depth + 1)

    if isinstance(instance, list):
        items = schema.get("items")
        if isinstance(items, dict):
            for i, element in enumerate(instance):
                _check(element, items, f"{path}[{i}]", report, depth + 1)

    if "allOf" in schema:
        for sub in schema["allOf"]:
            _check(instance, sub, path, report, depth + 1)

    if "if" in schema:
        if_report = ValidationReport()
        _check(instance, schema["if"], path, if_report, depth + 1)
        if if_report.ok:
            if "then" in schema:
                _check(instance, schema["then"], path, report, depth + 1)
        elif "else" in schema:
            _check(instance, schema["else"], path, report, depth + 1)


def _name_ok(name: str, pnames: Any) -> bool:
    if not isinstance(name, str):
        return False
    if "pattern" in pnames and re.search(pnames["pattern"], name) is None:
        return False
    if "minLength" in pnames and len(name) < pnames["minLength"]:
        return False
    return True


def _equal(a: Any, b: Any) -> bool:
    return a == b and type(a) is type(b)


def validate(instance: Any, schema: Any, *, path: str = "$") -> ValidationReport:
    """Validate ``instance`` against ``schema``; returns a :class:`ValidationReport`."""
    report = ValidationReport()
    _check(instance, schema, path, report)
    return report


def _load_schema(kind: str) -> dict:
    filename, _ = SCHEMA_FILES[kind]
    return json.loads((_SCHEMAS_DIR / filename).read_text(encoding="utf-8"))


def validate_record(kind: str, instance: dict) -> ValidationReport:
    """Validate one record dict against its named schema file.

    ``kind`` is one of ``run_record | case_manifest | provenance | scorer_output``.
    """
    if kind not in SCHEMA_FILES:
        raise KeyError(f"unknown record kind {kind!r}; expected one of {sorted(SCHEMA_FILES)}")
    return validate(instance, _load_schema(kind))


def has_jsonschema() -> bool:
    """True if the (authoritative) ``jsonschema`` package is importable."""
    try:
        import jsonschema  # noqa: F401

        return True
    except ImportError:
        return False


def canonical_payload_sha256(instance: Any) -> str:
    """SHA-256 of the record's canonical bytes (see repliclaw.canonical)."""
    return sha256_hex(canonical_json(instance))


__all__ = [
    "SCHEMA_FILES",
    "ValidationError",
    "ValidationReport",
    "validate",
    "validate_record",
    "has_jsonschema",
    "canonical_payload_sha256",
]
