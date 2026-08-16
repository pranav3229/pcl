"""Phase 2 Adversarial Test Suite: Spatial/Location Matching and Operational Gating.

Covers:
- Semantic anchor matching and ref equality/rejection
- Coordinate Haversine proximity matching and tolerance gating
- Location kind mismatch (semantic vs coordinates) fail-closed behavior
- Location.alt altitude/depth validation and serialization
- Availability accepts_work gating
- Availability.valid_until TTL expiration and deterministic evaluation_time
- RuntimeState independence from Availability (charging + accepts_work=true)
- Blocked states (offline, fault, maintenance)
- Structured diagnostics for spatial, availability, and TTL failures
- Adversarial Cases A through J
"""

import pytest
from datetime import datetime, timezone

from pcl.models import (
    Availability,
    CapabilityDeclaration,
    CapabilityOffer,
    Comparator,
    ConstraintDiagnostic,
    ConstraintPredicate,
    ConstraintSpec,
    ExecutionBinding,
    IOContract,
    IORole,
    Intent,
    IntentInputValue,
    Location,
    Protocol,
    Quantity,
    Range,
    RuntimeState,
    RuntimeStatus,
    SemanticRef,
    SetPredicate,
    ValueKind,
    ValuePredicate,
    haversine_distance,
)
from pcl.matcher import (
    availability_allows,
    location_allows,
    match_intent_to_offer,
    state_allows,
)


@pytest.fixture
def base_declaration() -> CapabilityDeclaration:
    return CapabilityDeclaration(
        id="cap-test-spatial",
        entity_id="robot-alpha",
        semantic_type=SemanticRef(
            vocabulary="https://pcl.dev/vocab/logistics/v0",
            term="package_transport",
        ),
        inputs=[
            IOContract(name="object", role=IORole.OBJECT, value_kind=ValueKind.ENTITY_REF, required=True),
            IOContract(name="origin", role=IORole.ORIGIN, value_kind=ValueKind.LOCATION_REF, required=True),
            IOContract(name="destination", role=IORole.DESTINATION, value_kind=ValueKind.LOCATION_REF, required=True),
        ],
        execution=ExecutionBinding(protocol=Protocol.HTTP, target="https://robot.example/api"),
    )


@pytest.fixture
def base_offer() -> CapabilityOffer:
    return CapabilityOffer(
        id="offer-test-alpha",
        declaration_id="cap-test-spatial",
        entity_id="robot-alpha",
        state=RuntimeState(status=RuntimeStatus.IDLE),
        availability=Availability(accepts_work=True),
        location=Location(kind="semantic", ref="warehouse-zone-A"),
    )


@pytest.fixture
def base_intent() -> Intent:
    return Intent(
        id="intent-test-spatial",
        goal=SemanticRef(
            vocabulary="https://pcl.dev/vocab/logistics/v0",
            term="package_transport",
        ),
        inputs={
            "object": {"ref": "package-1"},
            "origin": {"ref": "warehouse-zone-A"},
            "destination": {"ref": "warehouse-zone-B"},
        },
    )


# ============================================================================
# 1. SPATIAL & LOCATION TESTS
# ============================================================================


def test_semantic_location_exact_match(base_declaration, base_offer, base_intent):
    """Case A: Offer and Intent have matching semantic locations."""
    base_offer.location = Location(kind="semantic", ref="warehouse-zone-A")
    base_intent.inputs["origin"] = IntentInputValue(ref="warehouse-zone-A")

    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is not None
    assert "location" in result.satisfied


def test_semantic_location_mismatch_reject(base_declaration, base_offer, base_intent):
    """Case B: Offer is at warehouse-zone-A but Intent origin is warehouse-zone-B."""
    base_offer.location = Location(kind="semantic", ref="warehouse-zone-A")
    base_intent.inputs["origin"] = IntentInputValue(ref="warehouse-zone-B")

    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is None


def test_haversine_distance_calculation():
    """Verify Haversine great-circle distance on known geodetic coordinates."""
    # Bangalore to Bangalore (identical points)
    dist_zero = haversine_distance(12.9716, 77.5946, 12.9716, 77.5946)
    assert dist_zero == 0.0

    # London (51.5074, -0.1278) to Paris (48.8566, 2.3522) ~ 343 km
    dist_london_paris = haversine_distance(51.5074, -0.1278, 48.8566, 2.3522)
    assert 340.0 < dist_london_paris < 346.0

    # Bangalore Central (12.9716, 77.5946) to nearby point (12.9720, 77.5950) ~ 62 meters
    dist_nearby = haversine_distance(12.9716, 77.5946, 12.9720, 77.5950)
    assert 0.05 < dist_nearby < 0.08


def test_coordinate_location_exact_match(base_declaration, base_offer, base_intent):
    """Coordinates match at identical lat/lon with 0.0 km tolerance."""
    base_offer.location = Location(kind="coordinates", lat=12.9716, lon=77.5946)
    base_intent.inputs["origin"] = IntentInputValue(
        value={"kind": "coordinates", "lat": 12.9716, "lon": 77.5946}
    )

    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is not None
    assert "location" in result.satisfied


def test_coordinate_location_within_tolerance_match(base_declaration, base_offer, base_intent):
    """Case C: Bangalore point and nearby point with 2.0 km tolerance."""
    base_declaration.constraints = [
        ConstraintSpec(name="location_tolerance", quantity=Quantity(value=5.0, unit="km", comparator=Comparator.LTE))
    ]
    base_offer.location = Location(kind="coordinates", lat=12.9716, lon=77.5946)
    base_intent.inputs["origin"] = IntentInputValue(
        value={"kind": "coordinates", "lat": 12.9750, "lon": 77.5980}
    )
    base_intent.constraints["location_tolerance"] = Quantity(value=2.0, unit="km", comparator=Comparator.LTE)

    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is not None
    assert "location" in result.satisfied


def test_coordinate_location_outside_tolerance_reject(base_declaration, base_offer, base_intent):
    """Case D: Bangalore point and Delhi point (1740 km away) with 10.0 km tolerance."""
    base_declaration.constraints = [
        ConstraintSpec(name="location_tolerance", quantity=Quantity(value=20.0, unit="km", comparator=Comparator.LTE))
    ]
    base_offer.location = Location(kind="coordinates", lat=12.9716, lon=77.5946)
    base_intent.inputs["origin"] = IntentInputValue(
        value={"kind": "coordinates", "lat": 28.6139, "lon": 77.2090}
    )
    base_intent.constraints["location_tolerance"] = Quantity(value=10.0, unit="km", comparator=Comparator.LTE)

    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is None


def test_semantic_vs_coordinate_mismatch_fails_closed(base_declaration, base_offer, base_intent):
    """Semantic offer vs Coordinate intent origin fails closed."""
    base_offer.location = Location(kind="semantic", ref="warehouse-zone-A")
    base_intent.inputs["origin"] = IntentInputValue(
        value={"kind": "coordinates", "lat": 12.9716, "lon": 77.5946}
    )

    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is None


def test_no_spatial_requirement_in_intent_passes(base_declaration, base_offer, base_intent):
    """Case J: When intent has no spatial origin requirement, offer location is not forced."""
    simple_decl = CapabilityDeclaration(
        id="cap-compute",
        entity_id="server-1",
        semantic_type=SemanticRef(vocabulary="https://pcl.dev/vocab/compute/v0", term="inference"),
        inputs=[IOContract(name="model_id", role=IORole.PARAMETER, value_kind=ValueKind.STRING, required=True)],
        execution=ExecutionBinding(protocol=Protocol.HTTP, target="https://ai.example/infer"),
    )
    simple_offer = CapabilityOffer(
        id="offer-compute-1",
        declaration_id="cap-compute",
        entity_id="server-1",
        state=RuntimeState(status=RuntimeStatus.IDLE),
        availability=Availability(accepts_work=True),
        location=None,
    )
    simple_intent = Intent(
        id="intent-compute",
        goal=SemanticRef(vocabulary="https://pcl.dev/vocab/compute/v0", term="inference"),
        inputs={"model_id": IntentInputValue(value="resnet50")},
    )

    result = match_intent_to_offer(simple_intent, simple_offer, simple_decl)
    assert result is not None
    assert "location" not in result.satisfied  # location was not evaluated, but match succeeded


def test_location_altitude_serialization_and_validation():
    """Location alt field validates and serializes properly."""
    subsea_loc = Location(kind="coordinates", lat=-22.5, lon=45.0, alt=-1500.0)
    drone_loc = Location(kind="coordinates", lat=37.7749, lon=-122.4194, alt=120.0)

    assert subsea_loc.alt == -1500.0
    assert drone_loc.alt == 120.0

    data = drone_loc.model_dump()
    assert data["alt"] == 120.0
    reconstructed = Location.model_validate(data)
    assert reconstructed.alt == 120.0


# ============================================================================
# 2. OPERATIONAL STATE & AVAILABILITY TESTS
# ============================================================================


def test_availability_accepts_work_true(base_offer):
    """accepts_work = True passes availability gate."""
    base_offer.availability = Availability(accepts_work=True)
    ok, reasons, diag = availability_allows(base_offer)
    assert ok is True
    assert reasons == []


def test_availability_accepts_work_false(base_offer, base_declaration, base_intent):
    """Case I: state = idle, accepts_work = false rejects."""
    base_offer.state = RuntimeState(status=RuntimeStatus.IDLE)
    base_offer.availability = Availability(accepts_work=False, reason="maintenance_lockout")

    ok, reasons, diag = availability_allows(base_offer)
    assert ok is False
    assert len(reasons) == 1
    assert "maintenance_lockout" in reasons[0]

    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is None


def test_charging_with_accepts_work_true_eligible(base_declaration, base_offer, base_intent):
    """Case E: state = charging, accepts_work = true is ELIGIBLE and not rejected."""
    base_offer.state = RuntimeState(status=RuntimeStatus.CHARGING)
    base_offer.availability = Availability(accepts_work=True)

    ok_state, reasons_state = state_allows(base_offer)
    assert ok_state is True

    ok_avail, reasons_avail, _ = availability_allows(base_offer)
    assert ok_avail is True

    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is not None
    assert "state" in result.satisfied
    assert "availability" in result.satisfied


def test_charging_with_accepts_work_false_rejected(base_declaration, base_offer, base_intent):
    """Case F: state = charging, accepts_work = false is rejected by availability."""
    base_offer.state = RuntimeState(status=RuntimeStatus.CHARGING)
    base_offer.availability = Availability(accepts_work=False, reason="charging_exclusive")

    result = match_intent_to_offer(base_intent, base_offer, base_declaration)
    assert result is None


def test_blocked_states_rejected(base_declaration, base_offer, base_intent):
    """offline, maintenance, fault states are blocked by state gate."""
    for blocked_status in [RuntimeStatus.OFFLINE, RuntimeStatus.MAINTENANCE, RuntimeStatus.FAULT]:
        base_offer.state = RuntimeState(status=blocked_status)
        base_offer.availability = Availability(accepts_work=True)

        ok, reasons = state_allows(base_offer)
        assert ok is False

        result = match_intent_to_offer(base_intent, base_offer, base_declaration)
        assert result is None


# ============================================================================
# 3. TEMPORAL VALIDITY & DETERMINISTIC EVALUATION_TIME
# ============================================================================


def test_future_valid_until_passes(base_declaration, base_offer, base_intent):
    """Case G: accepts_work = true, valid_until = future matches."""
    eval_time = "2026-08-16T12:00:00Z"
    future_ttl = "2026-08-16T18:00:00Z"
    base_offer.availability = Availability(accepts_work=True, valid_until=future_ttl)

    ok, reasons, diag = availability_allows(base_offer, evaluation_time=eval_time)
    assert ok is True
    assert reasons == []

    result = match_intent_to_offer(base_intent, base_offer, base_declaration, evaluation_time=eval_time)
    assert result is not None
    assert "availability" in result.satisfied


def test_past_valid_until_rejects(base_declaration, base_offer, base_intent):
    """Case H: accepts_work = true, valid_until = past is rejected."""
    eval_time = "2026-08-16T12:00:00Z"
    past_ttl = "2026-08-16T11:59:59Z"
    base_offer.availability = Availability(accepts_work=True, valid_until=past_ttl)

    ok, reasons, diag = availability_allows(base_offer, evaluation_time=eval_time)
    assert ok is False
    assert len(reasons) == 1
    assert "expired" in reasons[0]

    result = match_intent_to_offer(base_intent, base_offer, base_declaration, evaluation_time=eval_time)
    assert result is None


def test_exact_boundary_valid_until_deterministic(base_offer):
    """At exact valid_until timestamp (eval_time == valid_until), offer remains valid."""
    exact_time = "2026-08-16T15:30:00Z"
    base_offer.availability = Availability(accepts_work=True, valid_until=exact_time)

    ok, reasons, _ = availability_allows(base_offer, evaluation_time=exact_time)
    assert ok is True

    # 1 second later -> expired
    ok_later, reasons_later, _ = availability_allows(base_offer, evaluation_time="2026-08-16T15:30:01Z")
    assert ok_later is False


# ============================================================================
# 4. STRUCTURED DIAGNOSTICS FOR PHASE 2
# ============================================================================


def test_spatial_rejection_diagnostic(base_declaration, base_offer, base_intent):
    """Spatial mismatch produces structured diagnostic with explanation."""
    base_offer.location = Location(kind="semantic", ref="warehouse-zone-A")
    base_intent.inputs["origin"] = IntentInputValue(ref="warehouse-zone-B")

    ok, reasons, diagnostics = location_allows(base_offer, base_declaration, base_intent)
    assert ok is False
    assert len(diagnostics) == 1
    diag = diagnostics[0]
    assert diag.constraint == "location"
    assert diag.result == "rejected"
    assert "warehouse-zone-A" in diag.reason
    assert "warehouse-zone-B" in diag.reason


def test_coordinate_distance_diagnostic(base_declaration, base_offer, base_intent):
    """Coordinate distance failure produces diagnostic with measured distance and tolerance."""
    base_offer.location = Location(kind="coordinates", lat=12.9716, lon=77.5946)
    base_intent.inputs["origin"] = IntentInputValue(
        value={"kind": "coordinates", "lat": 13.1000, "lon": 77.6000}
    )
    base_intent.constraints["location_tolerance"] = Quantity(value=5.0, unit="km")

    ok, reasons, diagnostics = location_allows(base_offer, base_declaration, base_intent)
    assert ok is False
    assert len(diagnostics) == 1
    diag = diagnostics[0]
    assert diag.constraint == "location"
    assert diag.result == "rejected"
    assert "km from requested origin" in diag.reason
    assert "tolerance is 5.0 km" in diag.reason


def test_ttl_rejection_diagnostic(base_offer):
    """Expired valid_until produces structured diagnostic."""
    eval_time = "2026-08-16T12:00:00Z"
    base_offer.availability = Availability(accepts_work=True, valid_until="2026-08-16T10:00:00Z")

    ok, reasons, diagnostics = availability_allows(base_offer, evaluation_time=eval_time)
    assert ok is False
    assert len(diagnostics) == 1
    diag = diagnostics[0]
    assert diag.constraint == "availability.valid_until"
    assert diag.result == "rejected"
    assert "expired at 2026-08-16T10:00:00Z" in diag.reason


def test_availability_rejection_diagnostic(base_offer):
    """accepts_work=false produces structured diagnostic."""
    base_offer.availability = Availability(accepts_work=False, reason="bay_occupied")

    ok, reasons, diagnostics = availability_allows(base_offer)
    assert ok is False
    assert len(diagnostics) == 1
    diag = diagnostics[0]
    assert diag.constraint == "availability.accepts_work"
    assert diag.result == "rejected"
    assert diag.reason == "bay_occupied"
