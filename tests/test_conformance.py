"""Conformance Test Suite: Validates reference implementation against portable spec/conformance/ JSON test vectors."""

import json
import pytest
from pathlib import Path

from pcl.canonical import canonicalize, sha256_digest
from pcl.models import (
    CapabilityDeclaration,
    CapabilityOffer,
    ExecutionBinding,
    Evidence,
    Intent,
    Location,
    haversine_distance,
)
from pcl.matcher import match_intent_to_offer
from pcl.verifier import verify_evidence

REPO_ROOT = Path(__file__).resolve().parents[1]
CONF_ROOT = REPO_ROOT / "spec" / "conformance"


def test_conformance_matching_vectors():
    """Validate matching engine against portable matching conformance vectors."""
    vectors_file = CONF_ROOT / "matching" / "matching-vectors.json"
    data = json.loads(vectors_file.read_text(encoding="utf-8"))

    for vec in data["vectors"]:
        intent = Intent.model_validate(vec["intent"])
        decl = CapabilityDeclaration.model_validate(vec["declaration"])
        offer = CapabilityOffer.model_validate(vec["offer"])

        res = match_intent_to_offer(intent, offer, decl)
        if vec["expected_match"]:
            assert res is not None, f"Vector {vec['id']} expected match but returned None"
            if "expected_score" in vec:
                assert abs(res.score - vec["expected_score"]) < 1e-4, f"Vector {vec['id']} score mismatch"
            if "expected_satisfied" in vec:
                assert set(res.satisfied) == set(vec["expected_satisfied"])
        else:
            assert res is None, f"Vector {vec['id']} expected rejection but matched"


def test_conformance_spatial_vectors():
    """Validate spatial matching and Haversine distance against portable spatial vectors."""
    vectors_file = CONF_ROOT / "spatial" / "spatial-vectors.json"
    data = json.loads(vectors_file.read_text(encoding="utf-8"))

    for vec in data["vectors"]:
        if "point_a" in vec:
            lat1, lon1 = vec["point_a"]["lat"], vec["point_a"]["lon"]
            lat2, lon2 = vec["point_b"]["lat"], vec["point_b"]["lon"]
            d = haversine_distance(lat1, lon1, lat2, lon2)
            assert abs(d - vec["expected_distance_km"]) < 0.05, f"Vector {vec['id']} distance mismatch"

            loc_a = Location(kind="coordinates", lat=lat1, lon=lon1)
            loc_b = Location(kind="coordinates", lat=lat2, lon=lon2)
            matched = loc_a.matches(loc_b, tolerance_km=vec["tolerance_km"])
            assert matched == vec["expected_match"]

        elif "location_a" in vec:
            loc_a = Location.model_validate(vec["location_a"])
            loc_b = Location.model_validate(vec["location_b"])
            matched = loc_a.matches(loc_b)
            assert matched == vec["expected_match"]


def test_conformance_parameter_map_vectors():
    """Validate ExecutionBinding parameter resolution against portable vectors."""
    vectors_file = CONF_ROOT / "parameters_map" / "parameter-map-vectors.json"
    data = json.loads(vectors_file.read_text(encoding="utf-8"))

    for vec in data["vectors"]:
        binding = ExecutionBinding(protocol="ros2", parameters_map=vec["parameters_map"])
        resolved = binding.resolve_parameters(
            inputs=vec["intent_context"].get("inputs"),
            constraints=vec["intent_context"].get("constraints"),
        )
        assert resolved == vec["expected_native_payload"], f"Vector {vec['id']} parameter resolution mismatch"


def test_conformance_canonicalization_vectors():
    """Validate RFC 8785 JCS canonicalization against portable vectors."""
    vectors_file = CONF_ROOT / "canonicalization" / "jcs-vectors.json"
    data = json.loads(vectors_file.read_text(encoding="utf-8"))

    for vec in data["vectors"]:
        raw_json = vec["input_json"]
        expected_canon = vec["expected_canonical_utf8"].encode("utf-8")
        expected_sha = vec["expected_sha256"]

        calc_canon = canonicalize(raw_json)
        assert calc_canon == expected_canon, f"Vector {vec['id']} canonical bytes mismatch"

        calc_sha = sha256_digest(calc_canon)
        assert calc_sha == expected_sha, f"Vector {vec['id']} digest mismatch"


def test_conformance_evidence_verification_vectors():
    """Validate evidence verification against portable verification vectors."""
    vectors_file = CONF_ROOT / "verification" / "evidence-verification-vectors.json"
    data = json.loads(vectors_file.read_text(encoding="utf-8"))

    for vec in data["vectors"]:
        evidence = Evidence.model_validate(vec["evidence_document"])
        res = verify_evidence(evidence)

        exp = vec["expected_verification"]
        assert res.valid == exp["valid"], f"Vector {vec['id']} validity mismatch"
        assert res.integrity == exp["integrity"], f"Vector {vec['id']} integrity mismatch"
