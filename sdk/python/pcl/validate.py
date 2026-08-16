"""JSON Schema validation for PCL documents."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from referencing import Registry as RefRegistry
from referencing.jsonschema import DRAFT202012

_SCHEMAS_DIR = Path(__file__).resolve().parents[3] / "spec" / "schemas"


@lru_cache(maxsize=1)
def _resource_registry() -> RefRegistry:
    resources: list[tuple[str, Any]] = []
    for path in sorted(_SCHEMAS_DIR.glob("*.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        schema_id = schema.get("$id", path.stem)
        resources.append((schema_id, DRAFT202012.create_resource(schema)))
    return RefRegistry().with_resources(resources)


def _validator(schema_name: str) -> Draft202012Validator:
    schema_path = _SCHEMAS_DIR / f"{schema_name}.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    resource = DRAFT202012.create_resource(schema)
    registry = _resource_registry().with_resource(schema.get("$id", schema_name), resource)
    return Draft202012Validator(schema, registry=registry)


def validate_document(document: dict[str, Any], schema_name: str) -> list[str]:
    """Validate a document against a named PCL schema. Returns error messages."""
    validator = _validator(schema_name)
    errors: list[str] = []
    for error in sorted(validator.iter_errors(document), key=lambda e: list(e.path)):
        path = ".".join(str(p) for p in error.path) or "(root)"
        errors.append(f"{path}: {error.message}")
    return errors


def assert_valid(document: dict[str, Any], schema_name: str) -> None:
    errors = validate_document(document, schema_name)
    if errors:
        raise ValidationError("; ".join(errors))
