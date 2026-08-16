"""Tests for PCL models."""

from pcl.models import Comparator, Quantity, SemanticRef


def test_semantic_ref_matches() -> None:
    a = SemanticRef(vocabulary="https://example/v0", term="transport")
    b = SemanticRef(vocabulary="https://example/v0", term="transport")
    c = SemanticRef(vocabulary="https://example/v0", term="move")
    assert a.matches(b)
    assert not a.matches(c)


def test_quantity_comparator_default() -> None:
    q = Quantity(value=10, unit="kg")
    assert q.comparator == Comparator.EQ
