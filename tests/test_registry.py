"""Tests for registry loading."""

from pathlib import Path

from pcl import Registry

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_registry_loads_entities_declarations_offers() -> None:
    registry = Registry.load(REPO_ROOT / "registry")
    assert "robot-17" in registry.entities
    assert "cap-transport-robot17" in registry.declarations
    assert len(registry.offers) >= 5


def test_get_declaration_for_offer() -> None:
    registry = Registry.load(REPO_ROOT / "registry")
    offer = next(o for o in registry.offers if o.declaration_id == "cap-transport-robot17")
    decl = registry.get_declaration_for_offer(offer)
    assert decl is not None
    assert decl.semantic_type.term == "package_transport"
