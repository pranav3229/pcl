"""Tests for JSON Schema validation."""

import json
from pathlib import Path

from pcl.validate import validate_document

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_validate_intent_example() -> None:
    path = REPO_ROOT / "spec" / "examples" / "intent-package-transport.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_document(data, "intent")
    assert errors == []


def test_validate_entity() -> None:
    path = REPO_ROOT / "registry" / "entities" / "robot-17.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_document(data, "entity")
    assert errors == []


def test_validate_declaration() -> None:
    path = REPO_ROOT / "registry" / "declarations" / "cap-transport-robot17.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_document(data, "capability-declaration")
    assert errors == []


def test_validate_offer() -> None:
    path = REPO_ROOT / "registry" / "offers" / "offer-robot17-transport.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_document(data, "capability-offer")
    assert errors == []


def test_invalid_intent_rejected() -> None:
    errors = validate_document({"id": "x"}, "intent")
    assert len(errors) > 0


def test_validate_intent_with_all_constraint_types() -> None:
    intent_data = {
        "pcl_version": "0.1.0",
        "id": "intent-generalized-constraints",
        "goal": {
            "vocabulary": "https://pcl.dev/vocab/test",
            "term": "test_goal",
        },
        "inputs": {
            "target": {"ref": "target-1"}
        },
        "constraints": {
            "scalar_q": {"value": 10, "unit": "kg", "comparator": "lte"},
            "temp_range": {"min": 2, "max": 8, "unit": "degC"},
            "material_set": {"in": ["Al-6061", "Steel-4140"]},
            "connector_cat": {"value": "CCS2"},
            "licensed_bool": {"value": True},
        },
    }
    errors = validate_document(intent_data, "intent")
    assert errors == []


def test_validate_declaration_with_all_constraint_types() -> None:
    decl_data = {
        "pcl_version": "0.1.0",
        "id": "cap-generalized",
        "entity_id": "robot-1",
        "semantic_type": {
            "vocabulary": "https://pcl.dev/vocab/test",
            "term": "test_goal",
        },
        "inputs": [
            {"name": "target", "role": "object", "value_kind": "entity_ref"}
        ],
        "constraints": [
            {"name": "scalar_q", "quantity": {"value": 25, "unit": "kg", "comparator": "lte"}},
            {"name": "temp_range", "range": {"min": 0, "max": 50, "unit": "degC"}},
            {"name": "material_set", "in": ["Al-6061", "Steel-4140"]},
            {"name": "connector_cat", "value": "CCS2"},
            {"name": "licensed_bool", "value": True},
        ],
        "execution": {
            "protocol": "http",
            "target": "https://api.example.com",
            "operation": "POST"
        }
    }
    errors = validate_document(decl_data, "capability-declaration")
    assert errors == []


def test_validate_invalid_range_constraint_rejected() -> None:
    intent_data = {
        "pcl_version": "0.1.0",
        "id": "intent-bad-range",
        "goal": {"term": "test_goal"},
        "inputs": {},
        "constraints": {
            "bad_range": {"min": 10}  # missing required "max"
        }
    }
    errors = validate_document(intent_data, "intent")
    assert len(errors) > 0


def test_validate_invalid_set_constraint_rejected() -> None:
    intent_data = {
        "pcl_version": "0.1.0",
        "id": "intent-bad-set",
        "goal": {"term": "test_goal"},
        "inputs": {},
        "constraints": {
            "bad_set": {"in": []}  # minItems is 1
        }
    }
    errors = validate_document(intent_data, "intent")
    assert len(errors) > 0


def test_validate_all_registry_files() -> None:
    for path in (REPO_ROOT / "registry" / "entities").glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        errors = validate_document(data, "entity")
        assert errors == [], f"Validation failed for {path.name}: {errors}"

    for path in (REPO_ROOT / "registry" / "declarations").glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        errors = validate_document(data, "capability-declaration")
        assert errors == [], f"Validation failed for {path.name}: {errors}"

    for path in (REPO_ROOT / "registry" / "offers").glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        errors = validate_document(data, "capability-offer")
        assert errors == [], f"Validation failed for {path.name}: {errors}"

    for path in (REPO_ROOT / "spec" / "examples").glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if "goal" in data:
            errors = validate_document(data, "intent")
            assert errors == [], f"Validation failed for {path.name}: {errors}"
        elif "semantic_type" in data:
            errors = validate_document(data, "capability-declaration")
            assert errors == [], f"Validation failed for {path.name}: {errors}"
        elif "outcome" in data:
            errors = validate_document(data, "evidence")
            assert errors == [], f"Validation failed for {path.name}: {errors}"
