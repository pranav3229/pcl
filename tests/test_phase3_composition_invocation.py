"""Phase 3 Test Suite: Capability Composition and Native Protocol Invocation Bindings.

Covers:
- CapabilityDeclaration composed_of declarative composition
- ExecutionBinding parameter resolution (flat, nested, locations, quantities, constraints)
- Nested native payload construction from dot-delimited parameter maps
- Fail-closed parameter resolution on missing/malformed source paths
- Structural ExecutionBinding validation
- Protocol adapter interface and payload preparation (ROS 2, HTTP, OPC-UA, WoT)
- Schema validation of composite declarations
"""

import json
import pytest
from pathlib import Path

from pcl.models import (
    CapabilityDeclaration,
    Comparator,
    ExecutionBinding,
    IOContract,
    IORole,
    Intent,
    IntentInputValue,
    Location,
    Protocol,
    Quantity,
    Range,
    SemanticRef,
    ValueKind,
    ValuePredicate,
)
from pcl.validate import validate_document
from adapters.base import (
    BaseAdapter,
    ExecutionResult,
    HttpAdapter,
    OpcUaAdapter,
    Ros2Adapter,
    StubAdapter,
    WotAdapter,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


# ============================================================================
# 1. CAPABILITY COMPOSITION (composed_of)
# ============================================================================


def test_composition_valid_composed_of_list():
    """CapabilityDeclaration correctly stores and serializes composed_of sub-capabilities."""
    decl = CapabilityDeclaration(
        id="cap-composite-1",
        entity_id="cell-4",
        semantic_type=SemanticRef(vocabulary="https://pcl.dev/vocab/test", term="composite_task"),
        inputs=[IOContract(name="input_part", role=IORole.OBJECT, value_kind=ValueKind.ENTITY_REF, required=True)],
        composed_of=["cap-cnc-mill", "cap-quality-inspect", "cap-package-box"],
        execution=ExecutionBinding(protocol=Protocol.HTTP, target="https://cell4.example/jobs", operation="POST"),
    )

    assert decl.composed_of == ["cap-cnc-mill", "cap-quality-inspect", "cap-package-box"]
    dumped = decl.model_dump()
    assert dumped["composed_of"] == ["cap-cnc-mill", "cap-quality-inspect", "cap-package-box"]

    reloaded = CapabilityDeclaration.model_validate(dumped)
    assert reloaded.composed_of == ["cap-cnc-mill", "cap-quality-inspect", "cap-package-box"]


def test_composition_empty_composed_of_allowed():
    """Atomic declarations default to empty composed_of."""
    decl = CapabilityDeclaration(
        id="cap-atomic-1",
        entity_id="robot-1",
        semantic_type=SemanticRef(vocabulary="https://pcl.dev/vocab/test", term="atomic_task"),
        inputs=[],
        execution=ExecutionBinding(protocol=Protocol.ROS2, target="/robot1/task", operation="send_goal"),
    )
    assert decl.composed_of == []


def test_composite_example_schema_validation():
    """Validate example composite capability declaration against normative JSON Schema."""
    example_path = REPO_ROOT / "spec" / "examples" / "composite-manufacturing-transport.json"
    data = json.loads(example_path.read_text(encoding="utf-8"))
    errors = validate_document(data, "capability-declaration")
    assert errors == []


# ============================================================================
# 2. PARAMETER RESOLUTION
# ============================================================================


def test_resolve_parameters_flat_and_ref_inputs():
    """Resolve flat inputs and ref attributes into nested native payload."""
    binding = ExecutionBinding(
        protocol="ros2",
        target="/amr/transport_action",
        operation="send_goal",
        parameters_map={
            "goal.package_id": "inputs.package.ref",
            "goal.destination": "inputs.destination.ref",
        },
    )

    intent = Intent(
        id="intent-1",
        goal=SemanticRef(vocabulary="https://pcl.dev/vocab/test", term="transport"),
        inputs={
            "package": IntentInputValue(ref="pkg-999"),
            "destination": IntentInputValue(ref="bay-12"),
        },
    )

    payload = binding.resolve_parameters(intent=intent)
    assert payload == {
        "goal": {
            "package_id": "pkg-999",
            "destination": "bay-12",
        }
    }


def test_resolve_parameters_coordinates_and_locations():
    """Resolve location attributes (lat, lon, alt) into nested payload."""
    binding = ExecutionBinding(
        protocol="http",
        target="https://drone.example/api/v1/survey",
        operation="POST",
        parameters_map={
            "target.coordinates.latitude": "inputs.site.lat",
            "target.coordinates.longitude": "inputs.site.lon",
            "target.coordinates.altitude": "inputs.site.alt",
        },
    )

    intent = Intent(
        id="intent-survey",
        goal=SemanticRef(vocabulary="https://pcl.dev/vocab/test", term="survey"),
        inputs={
            "site": IntentInputValue(
                value=Location(kind="coordinates", lat=12.9716, lon=77.5946, alt=920.0)
            )
        },
    )

    payload = binding.resolve_parameters(intent=intent)
    assert payload == {
        "target": {
            "coordinates": {
                "latitude": 12.9716,
                "longitude": 77.5946,
                "altitude": 920.0,
            }
        }
    }


def test_resolve_parameters_constraints_values():
    """Resolve constraint values (quantity, range, categorical) into payload."""
    binding = ExecutionBinding(
        protocol="opcua",
        target="opc.tcp://192.168.1.50:4840",
        operation="CallMethod",
        parameters_map={
            "feed_rate": "inputs.speed",
            "tolerance_limit": "constraints.max_tolerance.value",
            "material_name": "constraints.material.value",
        },
    )

    intent = Intent(
        id="intent-cnc",
        goal=SemanticRef(vocabulary="https://pcl.dev/vocab/test", term="machining"),
        inputs={"speed": IntentInputValue(value=250)},
        constraints={
            "max_tolerance": Quantity(value=0.02, unit="mm", comparator=Comparator.LTE),
            "material": ValuePredicate(value="Al-6061"),
        },
    )

    payload = binding.resolve_parameters(intent=intent)
    assert payload == {
        "feed_rate": 250,
        "tolerance_limit": 0.02,
        "material_name": "Al-6061",
    }


def test_resolve_parameters_missing_source_fails_closed():
    """Resolution fails closed with ValueError when a required source path is missing."""
    binding = ExecutionBinding(
        protocol="http",
        target="https://api.example/task",
        parameters_map={"job_id": "inputs.missing_input.ref"},
    )
    intent = Intent(
        id="intent-empty",
        goal=SemanticRef(vocabulary="https://pcl.dev/vocab/test", term="task"),
        inputs={},
    )

    with pytest.raises(ValueError, match="Cannot resolve 'inputs.missing_input.ref': 'missing_input' not found in inputs"):
        binding.resolve_parameters(intent=intent)


def test_resolve_parameters_malformed_path_fails_closed():
    """Resolution fails closed on invalid root or malformed path string."""
    binding = ExecutionBinding(
        protocol="http",
        target="https://api.example/task",
        parameters_map={"data": "invalid_root.something"},
    )
    intent = Intent(
        id="intent-test",
        goal=SemanticRef(vocabulary="https://pcl.dev/vocab/test", term="task"),
        inputs={},
    )

    with pytest.raises(ValueError, match="Invalid source path root 'invalid_root'"):
        binding.resolve_parameters(intent=intent)


def test_resolve_parameters_deterministic_repeated():
    """Repeated resolution produces identical output structures."""
    binding = ExecutionBinding(
        protocol="ros2",
        target="/robot/move",
        operation="send_goal",
        parameters_map={
            "target.point.x": "inputs.coord.lat",
            "target.point.y": "inputs.coord.lon",
        },
    )
    inputs = {"coord": IntentInputValue(value={"lat": 10.5, "lon": 20.5})}

    res1 = binding.resolve_parameters(inputs=inputs)
    res2 = binding.resolve_parameters(inputs=inputs)
    assert res1 == res2 == {"target": {"point": {"x": 10.5, "y": 20.5}}}


# ============================================================================
# 3. EXECUTION BINDING VALIDATION
# ============================================================================


def test_validate_binding_valid_structure():
    """Valid ExecutionBinding returns no validation errors."""
    binding = ExecutionBinding(
        protocol=Protocol.HTTP,
        target="https://api.factory.example/v1/jobs",
        operation="POST",
        parameters_map={"job_id": "inputs.object.ref"},
    )
    errors = binding.validate_binding()
    assert errors == []


def test_validate_binding_missing_protocol():
    """Empty protocol string fails validation."""
    binding = ExecutionBinding(protocol="", target="https://api.example", operation="POST")
    errors = binding.validate_binding()
    assert len(errors) == 1
    assert "protocol is required" in errors[0]


def test_validate_binding_malformed_parameters_map():
    """Malformed parameters_map source paths are rejected."""
    binding = ExecutionBinding(
        protocol="ros2",
        target="/robot",
        operation="send",
        parameters_map={
            "": "inputs.valid",
            "param1": "not_inputs_or_constraints",
            "param2": "inputs.",
        },
    )
    errors = binding.validate_binding()
    assert len(errors) >= 3
    assert any("parameters_map key must be a non-empty string" in e for e in errors)
    assert any("must start with 'inputs.' or 'constraints.'" in e for e in errors)
    assert any("malformed parameters_map source path" in e for e in errors)


# ============================================================================
# 4. ADAPTER ABSTRACTION & NATIVE INTERFACE
# ============================================================================


def test_adapter_prepare_payload_and_validation():
    """BaseAdapter prepares payload using parameter resolution and validates protocol."""
    adapter = HttpAdapter()
    binding = ExecutionBinding(
        protocol="http",
        target="https://api.example/tasks",
        operation="POST",
        parameters_map={"payload.task_id": "inputs.task.ref"},
    )

    errors = adapter.validate_binding(binding)
    assert errors == []

    payload = adapter.prepare_payload(binding, inputs={"task": IntentInputValue(ref="task-001")})
    assert payload == {"payload": {"task_id": "task-001"}}


def test_adapter_protocol_mismatch_validation():
    """Ros2Adapter rejects HTTP binding during validation."""
    ros_adapter = Ros2Adapter()
    http_binding = ExecutionBinding(
        protocol="http",
        target="https://api.example",
        operation="POST",
    )
    errors = ros_adapter.validate_binding(http_binding)
    assert len(errors) >= 1
    assert "expected protocol ros2, got http" in errors[0]


def test_adapter_invocation_stub_fails_safely():
    """Adapter invoke produces structured error on invalid binding or raises NotImplementedError on stub."""
    adapter = Ros2Adapter()
    invalid_binding = ExecutionBinding(protocol="ros2", target="")  # missing target

    result = adapter.invoke(invalid_binding, inputs={})
    assert isinstance(result, ExecutionResult)
    assert result.success is False
    assert "Binding validation failed" in result.error

    valid_binding = ExecutionBinding(protocol="ros2", target="/robot/goal", operation="send_goal")
    with pytest.raises(NotImplementedError, match="declarative stub"):
        adapter.invoke(valid_binding, inputs={})
