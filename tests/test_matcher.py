"""Tests for PCL matching."""

from pathlib import Path

import pytest

from pcl import Registry, match
from pcl.models import (
    CapabilityDeclaration,
    CapabilityOffer,
    Availability,
    Intent,
    Quantity,
    RuntimeState,
    SemanticRef,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "registry"


@pytest.fixture
def registry() -> Registry:
    return Registry.load(REGISTRY_PATH)


@pytest.fixture
def transport_intent() -> Intent:
    return Intent.from_file(REPO_ROOT / "spec" / "examples" / "intent-package-transport.json")


def test_match_transport_intent(registry: Registry, transport_intent: Intent) -> None:
    results = match(transport_intent, registry)
    assert len(results) >= 1
    top = results[0]
    assert top.declaration_id == "cap-transport-robot17"
    assert top.entity_id == "robot-17"
    assert "constraints" in top.satisfied


def test_light_transport_rejected_for_10kg(registry: Registry, transport_intent: Intent) -> None:
    results = match(transport_intent, registry)
    matched_ids = {r.declaration_id for r in results}
    assert "cap-transport-robot17-light" not in matched_ids


def test_drone_rejected_when_unavailable(registry: Registry) -> None:
    intent = Intent(
        id="inspect-1",
        goal=SemanticRef(
            vocabulary="https://pcl.dev/vocab/inspection/v0",
            term="aerial_inspection",
        ),
        inputs={
            "target_area": {"ref": "field-north"},
            "checklist": {"ref": "checklist-v1.json"},
        },
        constraints={"max_wind_speed": Quantity(value=10, unit="m/s", comparator="lte")},
    )
    results = match(intent, registry)
    assert all(r.declaration_id != "cap-aerial-inspection-drone" for r in results)


def test_fail_closed_missing_constraint(registry: Registry) -> None:
    intent = Intent(
        id="transport-no-budget",
        goal=SemanticRef(
            vocabulary="https://pcl.dev/vocab/logistics/v0",
            term="package_transport",
        ),
        inputs={
            "object": {"ref": "pkg-1"},
            "origin": {"ref": "A"},
            "destination": {"ref": "B"},
        },
        constraints={
            "max_payload": Quantity(value=5, unit="kg", comparator="lte"),
            "unknown_constraint": Quantity(value=1, unit="x", comparator="lte"),
        },
    )
    results = match(intent, registry)
    assert len(results) == 0


def test_blocked_state_rejected(registry: Registry) -> None:
    registry.register_offer(
        CapabilityOffer(
            id="offer-offline",
            declaration_id="cap-transport-robot17",
            entity_id="robot-offline",
            state=RuntimeState(status="offline"),
            availability=Availability(accepts_work=True),
        )
    )
    intent = Intent(
        id="t1",
        goal=SemanticRef(
            vocabulary="https://pcl.dev/vocab/logistics/v0",
            term="package_transport",
        ),
        inputs={
            "object": {"ref": "p"},
            "origin": {"ref": "A"},
            "destination": {"ref": "B"},
        },
        constraints={"max_payload": Quantity(value=5, unit="kg", comparator="lte")},
    )
    decl = registry.declarations["cap-transport-robot17"]
    intent.constraints["deadline"] = Quantity(value=10, unit="min", comparator="lte")
    intent.constraints["budget"] = Quantity(value=50, unit="INR", comparator="lte")
    results = match(intent, registry)
    offer_ids = [r.offer_id for r in results]
    assert "offer-offline" not in offer_ids


def test_preference_boosts_score(registry: Registry, transport_intent: Intent) -> None:
    from pcl.models import IntentPreferences

    transport_intent.preferences = IntentPreferences(provider_id="robot-17")
    results = match(transport_intent, registry)
    assert results[0].entity_id == "robot-17"
    assert results[0].score >= 1100
