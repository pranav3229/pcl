"""Comprehensive tests for generalized PCL constraint matching and adversarial domain battery."""

import pytest
from pcl.matcher import (
    constraints_satisfied,
    match,
    match_intent_to_offer,
)
from pcl.models import (
    Availability,
    CapabilityDeclaration,
    CapabilityOffer,
    Comparator,
    ConstraintDiagnostic,
    ConstraintSpec,
    ExecutionBinding,
    IOContract,
    IORole,
    Intent,
    Protocol,
    Quantity,
    Range,
    RuntimeState,
    RuntimeStatus,
    SemanticRef,
    SetPredicate,
    ValueKind,
    ValuePredicate,
)
from pcl.registry import Registry


@pytest.fixture
def base_declaration() -> CapabilityDeclaration:
    return CapabilityDeclaration(
        id="cap-test",
        entity_id="entity-1",
        semantic_type=SemanticRef(vocabulary="https://pcl.dev/vocab/test", term="test_op"),
        inputs=[IOContract(name="target", role=IORole.OBJECT, value_kind=ValueKind.ENTITY_REF, required=True)],
        constraints=[],
        execution=ExecutionBinding(protocol=Protocol.HTTP, target="https://example.com/api"),
    )


@pytest.fixture
def base_offer() -> CapabilityOffer:
    return CapabilityOffer(
        id="offer-test",
        declaration_id="cap-test",
        entity_id="entity-1",
        state=RuntimeState(status=RuntimeStatus.IDLE),
        availability=Availability(accepts_work=True),
    )


@pytest.fixture
def base_intent() -> Intent:
    return Intent(
        id="intent-test",
        goal=SemanticRef(vocabulary="https://pcl.dev/vocab/test", term="test_op"),
        inputs={"target": {"ref": "target-001"}},
        constraints={},
    )


# =====================================================================
# 1. QUANTITY CONSTRAINTS (Scalar with comparators)
# =====================================================================

def test_quantity_lte_match(base_declaration, base_offer, base_intent):
    base_declaration.constraints = [
        ConstraintSpec(name="payload", quantity=Quantity(value=25, unit="kg", comparator=Comparator.LTE))
    ]
    base_intent.constraints = {
        "payload": Quantity(value=10, unit="kg", comparator=Comparator.LTE)
    }
    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is not None
    assert "constraints" in result.satisfied
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].constraint == "payload"
    assert result.diagnostics[0].result == "satisfied"


def test_quantity_lte_reject(base_declaration, base_offer, base_intent):
    base_declaration.constraints = [
        ConstraintSpec(name="payload", quantity=Quantity(value=5, unit="kg", comparator=Comparator.LTE))
    ]
    base_intent.constraints = {
        "payload": Quantity(value=10, unit="kg", comparator=Comparator.LTE)
    }
    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is None

    ok, reasons, diag = constraints_satisfied(base_intent, base_declaration)
    assert not ok
    assert any("less than required" in d.reason for d in diag if d.reason)


def test_quantity_unit_mismatch(base_declaration, base_offer, base_intent):
    base_declaration.constraints = [
        ConstraintSpec(name="payload", quantity=Quantity(value=25, unit="kg", comparator=Comparator.LTE))
    ]
    base_intent.constraints = {
        "payload": Quantity(value=10, unit="lbs", comparator=Comparator.LTE)
    }
    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is None

    ok, reasons, diag = constraints_satisfied(base_intent, base_declaration)
    assert not ok
    assert any("unit mismatch" in d.reason for d in diag if d.reason)


def test_quantity_gte_precision_match(base_declaration, base_offer, base_intent):
    # Higher precision = smaller numerical value
    base_declaration.constraints = [
        ConstraintSpec(name="precision", quantity=Quantity(value=0.01, unit="mm", comparator=Comparator.GTE))
    ]
    base_intent.constraints = {
        "precision": Quantity(value=0.05, unit="mm", comparator=Comparator.GTE)
    }
    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is not None
    assert "constraints" in result.satisfied


def test_quantity_gte_precision_reject(base_declaration, base_offer, base_intent):
    base_declaration.constraints = [
        ConstraintSpec(name="precision", quantity=Quantity(value=0.1, unit="mm", comparator=Comparator.GTE))
    ]
    base_intent.constraints = {
        "precision": Quantity(value=0.05, unit="mm", comparator=Comparator.GTE)
    }
    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is None


def test_quantity_eq_match(base_declaration, base_offer, base_intent):
    base_declaration.constraints = [
        ConstraintSpec(name="voltage", quantity=Quantity(value=24, unit="V", comparator=Comparator.EQ))
    ]
    base_intent.constraints = {
        "voltage": Quantity(value=24, unit="V", comparator=Comparator.EQ)
    }
    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is not None


def test_quantity_eq_reject(base_declaration, base_offer, base_intent):
    base_declaration.constraints = [
        ConstraintSpec(name="voltage", quantity=Quantity(value=48, unit="V", comparator=Comparator.EQ))
    ]
    base_intent.constraints = {
        "voltage": Quantity(value=24, unit="V", comparator=Comparator.EQ)
    }
    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is None


# =====================================================================
# 2. RANGE CONSTRAINTS (Continuous intervals [min, max])
# =====================================================================

def test_range_vs_range_match(base_declaration, base_offer, base_intent):
    base_declaration.constraints = [
        ConstraintSpec(name="temperature", range=Range(min=0, max=50, unit="degC"))
    ]
    base_intent.constraints = {
        "temperature": Range(min=10, max=30, unit="degC")
    }
    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is not None
    assert "constraints" in result.satisfied


def test_range_vs_range_reject_narrow_provider(base_declaration, base_offer, base_intent):
    base_declaration.constraints = [
        ConstraintSpec(name="temperature", range=Range(min=0, max=20, unit="degC"))
    ]
    base_intent.constraints = {
        "temperature": Range(min=10, max=30, unit="degC")
    }
    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is None

    ok, reasons, diag = constraints_satisfied(base_intent, base_declaration)
    assert not ok
    assert any("provider range maximum (20.0) for 'temperature' is less than intent maximum (30.0)" in d.reason for d in diag if d.reason)


def test_range_vs_range_unit_mismatch(base_declaration, base_offer, base_intent):
    base_declaration.constraints = [
        ConstraintSpec(name="temperature", range=Range(min=0, max=50, unit="degC"))
    ]
    base_intent.constraints = {
        "temperature": Range(min=10, max=30, unit="degF")
    }
    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is None


def test_scalar_quantity_against_provider_range(base_declaration, base_offer, base_intent):
    base_declaration.constraints = [
        ConstraintSpec(name="temperature", range=Range(min=0, max=50, unit="degC"))
    ]
    base_intent.constraints = {
        "temperature": Quantity(value=25, unit="degC", comparator=Comparator.EQ)
    }
    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is not None


def test_scalar_quantity_outside_provider_range(base_declaration, base_offer, base_intent):
    base_declaration.constraints = [
        ConstraintSpec(name="temperature", range=Range(min=0, max=50, unit="degC"))
    ]
    base_intent.constraints = {
        "temperature": Quantity(value=65, unit="degC", comparator=Comparator.EQ)
    }
    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is None


# =====================================================================
# 3. CATEGORICAL / VALUE CONSTRAINTS (Exact discrete strings/enums)
# =====================================================================

def test_categorical_match(base_declaration, base_offer, base_intent):
    base_declaration.constraints = [
        ConstraintSpec(name="connector_type", value="CCS2")
    ]
    base_intent.constraints = {
        "connector_type": ValuePredicate(value="CCS2")
    }
    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is not None
    assert "constraints" in result.satisfied


def test_categorical_reject(base_declaration, base_offer, base_intent):
    base_declaration.constraints = [
        ConstraintSpec(name="connector_type", value="NACS")
    ]
    base_intent.constraints = {
        "connector_type": ValuePredicate(value="CCS2")
    }
    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is None

    ok, reasons, diag = constraints_satisfied(base_intent, base_declaration)
    assert not ok
    assert any("does not match required value 'CCS2'" in d.reason for d in diag if d.reason)


def test_categorical_paint_color(base_declaration, base_offer, base_intent):
    base_declaration.constraints = [
        ConstraintSpec(name="color", value="RAL-9005")
    ]
    base_intent.constraints = {
        "color": ValuePredicate(value="RAL-9005")
    }
    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is not None


# =====================================================================
# 4. SET MEMBERSHIP CONSTRAINTS (in: [...])
# =====================================================================

def test_set_member_match(base_declaration, base_offer, base_intent):
    base_declaration.constraints = [
        ConstraintSpec(name="supported_materials", in_values=["Al-6061", "Steel-4140"])
    ]
    base_intent.constraints = {
        "supported_materials": ValuePredicate(value="Al-6061")
    }
    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is not None
    assert "constraints" in result.satisfied


def test_set_member_reject(base_declaration, base_offer, base_intent):
    base_declaration.constraints = [
        ConstraintSpec(name="supported_materials", in_values=["Steel-4140"])
    ]
    base_intent.constraints = {
        "supported_materials": ValuePredicate(value="Al-6061")
    }
    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is None

    ok, reasons, diag = constraints_satisfied(base_intent, base_declaration)
    assert not ok
    assert any("not in provider supported set" in d.reason for d in diag if d.reason)


def test_set_overlap_match(base_declaration, base_offer, base_intent):
    base_declaration.constraints = [
        ConstraintSpec(name="connector", in_values=["CCS2", "CHAdeMO"])
    ]
    base_intent.constraints = {
        "connector": SetPredicate(in_values=["CCS2", "NACS"])
    }
    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is not None


def test_set_overlap_reject(base_declaration, base_offer, base_intent):
    base_declaration.constraints = [
        ConstraintSpec(name="connector", in_values=["CHAdeMO"])
    ]
    base_intent.constraints = {
        "connector": SetPredicate(in_values=["CCS2", "NACS"])
    }
    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is None


# =====================================================================
# 5. BOOLEAN CONSTRAINTS (True / False)
# =====================================================================

def test_boolean_true_match(base_declaration, base_offer, base_intent):
    base_declaration.constraints = [
        ConstraintSpec(name="licensed_electrician", value=True)
    ]
    base_intent.constraints = {
        "licensed_electrician": ValuePredicate(value=True)
    }
    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is not None


def test_boolean_true_reject(base_declaration, base_offer, base_intent):
    base_declaration.constraints = [
        ConstraintSpec(name="licensed_electrician", value=False)
    ]
    base_intent.constraints = {
        "licensed_electrician": ValuePredicate(value=True)
    }
    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is None


def test_boolean_ada_accessible(base_declaration, base_offer, base_intent):
    base_declaration.constraints = [
        ConstraintSpec(name="ada_accessible", value=True)
    ]
    base_intent.constraints = {
        "ada_accessible": ValuePredicate(value=True)
    }
    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is not None


# =====================================================================
# 6. FAIL-CLOSED BEHAVIOR ON MISSING CONSTRAINTS
# =====================================================================

def test_fail_closed_missing_property(base_declaration, base_offer, base_intent):
    base_declaration.constraints = [
        ConstraintSpec(name="max_payload", quantity=Quantity(value=25, unit="kg", comparator=Comparator.LTE))
    ]
    base_intent.constraints = {
        "max_payload": Quantity(value=10, unit="kg", comparator=Comparator.LTE),
        "unsupported_extra_constraint": ValuePredicate(value="must_have_this"),
    }
    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is None

    ok, reasons, diag = constraints_satisfied(base_intent, base_declaration)
    assert not ok
    assert any("capability missing constraint: unsupported_extra_constraint" in d.reason for d in diag if d.reason)


# =====================================================================
# 7. ADVERSARIAL REAL-WORLD DOMAIN BATTERY
# =====================================================================

def test_adversarial_ev_charging_matching():
    """EV Charging: connector_type='CCS2', max_power >= 100 kW against station offering CCS2 and 150 kW."""
    ev_station_decl = CapabilityDeclaration(
        id="cap-charging-ev",
        entity_id="ev-station-42",
        semantic_type=SemanticRef(vocabulary="https://pcl.dev/vocab/energy/v0", term="charging"),
        inputs=[
            IOContract(name="vehicle", role=IORole.OBJECT, value_kind=ValueKind.ENTITY_REF, required=True),
            IOContract(name="target_soc", role=IORole.PARAMETER, value_kind=ValueKind.QUANTITY, required=True),
        ],
        constraints=[
            ConstraintSpec(name="max_power", quantity=Quantity(value=150, unit="kW", comparator=Comparator.LTE)),
            ConstraintSpec(name="connector_type", value="CCS2"),
        ],
        execution=ExecutionBinding(protocol=Protocol.HTTP, target="https://chargegrid.example/stations/42"),
    )
    ev_station_offer = CapabilityOffer(
        id="offer-ev-42",
        declaration_id="cap-charging-ev",
        entity_id="ev-station-42",
        state=RuntimeState(status=RuntimeStatus.IDLE),
        availability=Availability(accepts_work=True),
    )
    ev_intent = Intent(
        id="intent-charge-my-car",
        goal=SemanticRef(vocabulary="https://pcl.dev/vocab/energy/v0", term="charging"),
        inputs={
            "vehicle": {"ref": "vin-tesla-model-y"},
            "target_soc": {"quantity": Quantity(value=80, unit="%")},
        },
        constraints={
            "connector_type": ValuePredicate(value="CCS2"),
            "max_power": Quantity(value=100, unit="kW", comparator=Comparator.LTE),
        },
    )
    result = match_intent_to_offer(ev_intent, ev_station_offer, ev_station_decl)
    assert result is not None
    assert result.declaration_id == "cap-charging-ev"
    assert "constraints" in result.satisfied


def test_adversarial_cnc_material_compatibility():
    """CNC Machining: requires material in ['Al-6061', 'Steel-4140'] and tolerance <= 0.05 mm."""
    cnc_decl = CapabilityDeclaration(
        id="cap-cnc-mill",
        entity_id="cnc-mill-3",
        semantic_type=SemanticRef(vocabulary="https://pcl.dev/vocab/manufacturing/v0", term="manufacture"),
        inputs=[
            IOContract(name="cad_model", role=IORole.ARTIFACT, value_kind=ValueKind.FILE_REF, required=True),
            IOContract(name="material", role=IORole.OBJECT, value_kind=ValueKind.ENTITY_REF, required=True),
        ],
        constraints=[
            ConstraintSpec(name="tolerance", quantity=Quantity(value=0.02, unit="mm", comparator=Comparator.GTE)),
            ConstraintSpec(name="supported_materials", in_values=["Al-6061", "Steel-4140", "Brass-360"]),
        ],
        execution=ExecutionBinding(protocol=Protocol.OPCUA, target="ns=2;s=CNC.Mill3"),
    )
    cnc_offer = CapabilityOffer(
        id="offer-cnc-3",
        declaration_id="cap-cnc-mill",
        entity_id="cnc-mill-3",
        state=RuntimeState(status=RuntimeStatus.IDLE),
        availability=Availability(accepts_work=True),
    )
    intent_al6061 = Intent(
        id="intent-machine-bracket",
        goal=SemanticRef(vocabulary="https://pcl.dev/vocab/manufacturing/v0", term="manufacture"),
        inputs={
            "cad_model": {"ref": "bracket_v2.step"},
            "material": {"ref": "stock-al-6061"},
        },
        constraints={
            "supported_materials": ValuePredicate(value="Al-6061"),
            "tolerance": Quantity(value=0.05, unit="mm", comparator=Comparator.GTE),
        },
    )
    result = match_intent_to_offer(intent_al6061, cnc_offer, cnc_decl)
    assert result is not None
    assert "constraints" in result.satisfied


def test_adversarial_refrigerated_cargo_temp_range():
    """Cold Chain Transport: requires cargo temperature envelope [2, 8] degC."""
    reefer_decl = CapabilityDeclaration(
        id="cap-reefer-transport",
        entity_id="reefer-truck-9",
        semantic_type=SemanticRef(vocabulary="https://pcl.dev/vocab/logistics/v0", term="package_transport"),
        inputs=[
            IOContract(name="object", role=IORole.OBJECT, value_kind=ValueKind.ENTITY_REF, required=True),
            IOContract(name="origin", role=IORole.ORIGIN, value_kind=ValueKind.LOCATION_REF, required=True),
            IOContract(name="destination", role=IORole.DESTINATION, value_kind=ValueKind.LOCATION_REF, required=True),
        ],
        constraints=[
            ConstraintSpec(name="payload", quantity=Quantity(value=1000, unit="kg", comparator=Comparator.LTE)),
            ConstraintSpec(name="cargo_temperature", range=Range(min=-5, max=15, unit="degC")),
        ],
        execution=ExecutionBinding(protocol=Protocol.HTTP, target="https://fleet.example/truck/9"),
    )
    reefer_offer = CapabilityOffer(
        id="offer-reefer-9",
        declaration_id="cap-reefer-transport",
        entity_id="reefer-truck-9",
        state=RuntimeState(status=RuntimeStatus.IDLE),
        availability=Availability(accepts_work=True),
    )
    vaccine_intent = Intent(
        id="intent-ship-vaccines",
        goal=SemanticRef(vocabulary="https://pcl.dev/vocab/logistics/v0", term="package_transport"),
        inputs={
            "object": {"ref": "vaccine-pallet-12"},
            "origin": {"ref": "pharma-hub-A"},
            "destination": {"ref": "hospital-B"},
        },
        constraints={
            "payload": Quantity(value=200, unit="kg", comparator=Comparator.LTE),
            "cargo_temperature": Range(min=2, max=8, unit="degC"),
        },
    )
    result = match_intent_to_offer(vaccine_intent, reefer_offer, reefer_decl)
    assert result is not None
    assert "constraints" in result.satisfied


def test_adversarial_high_voltage_clamp_diameter():
    """High-voltage line robot: clamp diameter range [25, 40] mm."""
    robot_decl = CapabilityDeclaration(
        id="cap-deice-robot",
        entity_id="robot-deice-1",
        semantic_type=SemanticRef(vocabulary="https://pcl.dev/vocab/utility/v0", term="line_deicing"),
        inputs=[IOContract(name="line_span", role=IORole.OBJECT, value_kind=ValueKind.ENTITY_REF, required=True)],
        constraints=[
            ConstraintSpec(name="clamp_diameter", range=Range(min=20, max=50, unit="mm")),
            ConstraintSpec(name="live_line_rated", value=True),
        ],
        execution=ExecutionBinding(protocol=Protocol.ROS2, target="/robot_deice"),
    )
    robot_offer = CapabilityOffer(
        id="offer-deice-1",
        declaration_id="cap-deice-robot",
        entity_id="robot-deice-1",
        state=RuntimeState(status=RuntimeStatus.IDLE),
        availability=Availability(accepts_work=True),
    )
    grid_intent = Intent(
        id="intent-deice-span-4",
        goal=SemanticRef(vocabulary="https://pcl.dev/vocab/utility/v0", term="line_deicing"),
        inputs={"line_span": {"ref": "transmission-span-132kv-tower-44"}},
        constraints={
            "clamp_diameter": Range(min=25, max=40, unit="mm"),
            "live_line_rated": ValuePredicate(value=True),
        },
    )
    result = match_intent_to_offer(grid_intent, robot_offer, robot_decl)
    assert result is not None
    assert "constraints" in result.satisfied
