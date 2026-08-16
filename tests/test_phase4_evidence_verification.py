"""Phase 4 Test Suite: Outcome Evidence, Verification & Cryptographic Attestation.

Covers:
- RFC 8785 JCS Canonicalization and SHA-256 digest generation
- Ed25519 and ECDSA P-256 signing and verification
- Tamper detection and fail-closed cryptographic verification
- Provenance linkage checking (intent_id, declaration_id, entity_id, execution_id)
- Observed metric verification against Intent constraints (Quantity, Range, Set, Categoricals)
- Partial, failed, cancelled, and multi-party attestation scenarios
- Conformance test vector validation
- Normative JSON Schema validation of Evidence documents
"""

import json
import pytest
from pathlib import Path

from pcl.canonical import canonicalize, sha256_digest
from pcl.crypto import (
    generate_ecdsa_p256_keypair,
    generate_ed25519_keypair,
    sign_digest,
    verify_signature,
)
from pcl.models import (
    ArtifactRef,
    Attestation,
    CapabilityDeclaration,
    Comparator,
    ConstraintSpec,
    Entity,
    Evidence,
    ExecutionBinding,
    IOContract,
    IORole,
    Intent,
    IntentInputValue,
    OutcomeStatus,
    Protocol,
    Quantity,
    Range,
    SemanticRef,
    SetPredicate,
    ValueKind,
    ValuePredicate,
    VerificationResult,
)
from pcl.validate import validate_document
from pcl.verifier import (
    verify_constraints,
    verify_evidence,
    verify_integrity,
    verify_provenance,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


# ============================================================================
# 1. CANONICALIZATION & DIGEST DETERMINISM
# ============================================================================


def test_canonicalize_rfc8785_key_sorting_and_formatting():
    """RFC 8785 canonicalization sorts keys lexicographically and strips whitespace."""
    doc = {
        "z": 10,
        "a": "hello",
        "m": {"nested_b": True, "nested_a": None},
        "list": [3, 2, 1],
    }
    canon = canonicalize(doc)
    assert canon == b'{"a":"hello","list":[3,2,1],"m":{"nested_a":null,"nested_b":true},"z":10}'


def test_deterministic_repeated_digest():
    """Digest calculation is strictly deterministic across repeated runs."""
    doc = {"entity": "robot-17", "count": 42, "ratio": 3.1415}
    d1 = sha256_digest(doc)
    d2 = sha256_digest(doc)
    assert d1 == d2
    assert d1.startswith("sha256:")


# ============================================================================
# 2. CRYPTOGRAPHIC SIGNING & INTEGRITY (Ed25519 & ECDSA P-256)
# ============================================================================


def test_ed25519_signing_and_verification():
    """Generate Ed25519 key, sign evidence canonical bytes, and verify."""
    priv, pub_b64 = generate_ed25519_keypair()
    evi = Evidence(
        id="evi-001",
        execution_id="exec-101",
        intent_id="intent-001",
        declaration_id="cap-001",
        entity_id="robot-17",
        timestamp="2026-08-16T12:00:00Z",
        outcome=OutcomeStatus.COMPLETED,
        observed_outputs={"part": {"ref": "part-99"}},
        observed_metrics={"tolerance_mm": 0.02},
    )

    att = evi.sign(priv, issuer="robot-17", role="provider", algorithm="ed25519", public_key=pub_b64)
    assert att.signature is not None
    assert att.algorithm == "ed25519"
    assert att.verify(evi.canonical_bytes()) is True


def test_ecdsa_p256_signing_and_verification():
    """Generate ECDSA P-256 key, sign evidence canonical bytes, and verify."""
    priv, pub_b64 = generate_ecdsa_p256_keypair()
    evi = Evidence(
        id="evi-p256",
        execution_id="exec-p256",
        intent_id="intent-001",
        declaration_id="cap-001",
        entity_id="cell-4",
        timestamp="2026-08-16T12:00:00Z",
        outcome=OutcomeStatus.COMPLETED,
    )

    att = evi.sign(priv, issuer="cell-4", role="provider", algorithm="ecdsa-p256-sha256", public_key=pub_b64)
    assert att.verify(evi.canonical_bytes()) is True


def test_tampered_evidence_fails_verification():
    """Tampering with any field in Evidence invalidates the cryptographic signature."""
    priv, pub_b64 = generate_ed25519_keypair()
    evi = Evidence(
        id="evi-tamper",
        execution_id="exec-101",
        intent_id="intent-001",
        declaration_id="cap-001",
        entity_id="robot-17",
        timestamp="2026-08-16T12:00:00Z",
        outcome=OutcomeStatus.COMPLETED,
        observed_metrics={"tolerance": 0.02},
    )
    evi.sign(priv, issuer="robot-17", public_key=pub_b64)

    # Tamper with the metric after signing
    evi.observed_metrics["tolerance"] = 0.09

    # Verification must fail
    res, diags = verify_integrity(evi, public_keys={"robot-17": pub_b64})
    assert res is False
    assert any(d.result == "rejected" for d in diags)


def test_invalid_signature_string_fails_closed():
    """Corrupted signature string fails closed safely without crashing."""
    _, pub_b64 = generate_ed25519_keypair()
    att = Attestation(
        issuer="robot-17",
        role="provider",
        algorithm="ed25519",
        public_key=pub_b64,
        timestamp="2026-08-16T12:00:00Z",
        signature="invalid_garbage_base64!",
    )
    assert att.verify(b"some_bytes") is False


def test_unsupported_algorithm_fails_closed():
    """Unsupported algorithm fails closed."""
    att = Attestation(
        issuer="robot-17",
        role="provider",
        algorithm="rsa-md5-unsupported",
        timestamp="2026-08-16T12:00:00Z",
        signature="AAAA",
    )
    assert att.verify(b"data") is False


# ============================================================================
# 3. PROVENANCE VERIFICATION
# ============================================================================


def test_provenance_valid_linkage():
    """Valid provenance matching intent, declaration, and entity passes."""
    evi = Evidence(
        id="evi-prov-1",
        execution_id="exec-prov-1",
        intent_id="intent-100",
        declaration_id="cap-transport",
        entity_id="robot-17",
        timestamp="2026-08-16T12:00:00Z",
        outcome=OutcomeStatus.COMPLETED,
        observed_outputs={"delivered_cargo": {"ref": "pkg-1"}},
    )
    intent = Intent(
        id="intent-100",
        goal=SemanticRef(vocabulary="https://pcl.dev/vocab/test", term="transport"),
    )
    decl = CapabilityDeclaration(
        id="cap-transport",
        entity_id="robot-17",
        semantic_type=SemanticRef(vocabulary="https://pcl.dev/vocab/test", term="transport"),
        inputs=[],
        outputs=[IOContract(name="delivered_cargo", role=IORole.OBJECT, value_kind=ValueKind.ENTITY_REF, required=True)],
        execution=ExecutionBinding(protocol="http", target="https://example.com"),
    )

    passed, diags = verify_provenance(evi, intent=intent, declaration=decl)
    assert passed is True
    assert diags == []


def test_provenance_mismatched_intent_fails():
    """Evidence with mismatched intent_id fails provenance verification."""
    evi = Evidence(
        id="evi-prov-2",
        execution_id="exec-prov-2",
        intent_id="intent-WRONG",
        declaration_id="cap-transport",
        entity_id="robot-17",
        timestamp="2026-08-16T12:00:00Z",
        outcome=OutcomeStatus.COMPLETED,
    )
    intent = Intent(id="intent-EXPECTED", goal=SemanticRef(vocabulary="https://pcl.dev/vocab/test", term="transport"))

    passed, diags = verify_provenance(evi, intent=intent)
    assert passed is False
    assert any("does not match expected 'intent-EXPECTED'" in d.reason for d in diags)


def test_provenance_missing_execution_id_fails():
    """Evidence missing execution_id fails provenance check."""
    evi = Evidence(
        id="evi-no-exec",
        execution_id="",
        intent_id="intent-1",
        declaration_id="cap-1",
        entity_id="robot-1",
        timestamp="2026-08-16T12:00:00Z",
        outcome=OutcomeStatus.COMPLETED,
    )
    passed, diags = verify_provenance(evi)
    assert passed is False
    assert any("missing execution_id" in d.reason for d in diags)


def test_provenance_missing_required_output_fails():
    """Evidence omitting mandatory declared output fails provenance check."""
    evi = Evidence(
        id="evi-prov-3",
        execution_id="exec-prov-3",
        intent_id="intent-1",
        declaration_id="cap-1",
        entity_id="robot-1",
        timestamp="2026-08-16T12:00:00Z",
        outcome=OutcomeStatus.COMPLETED,
        observed_outputs={},  # missing required 'final_part'
    )
    decl = CapabilityDeclaration(
        id="cap-1",
        entity_id="robot-1",
        semantic_type=SemanticRef(vocabulary="https://pcl.dev/vocab/test", term="task"),
        inputs=[],
        outputs=[IOContract(name="final_part", role=IORole.OBJECT, value_kind=ValueKind.ENTITY_REF, required=True)],
        execution=ExecutionBinding(protocol="http", target="https://example.com"),
    )
    passed, diags = verify_provenance(evi, declaration=decl)
    assert passed is False
    assert any("required output 'final_part' missing" in d.reason for d in diags)


# ============================================================================
# 4. CONSTRAINT SATISFACTION VERIFICATION
# ============================================================================


def test_constraint_verification_quantities_and_ranges():
    """Observed evidence metrics satisfy numeric quantities, ranges, and set constraints."""
    intent = Intent(
        id="intent-eval",
        goal=SemanticRef(vocabulary="https://pcl.dev/vocab/test", term="machining"),
        constraints={
            "max_tolerance": Quantity(value=0.05, unit="mm", comparator=Comparator.LTE),
            "temp_range": Range(min=2, max=8, unit="degC"),
            "material": SetPredicate(in_values=["Al-6061", "Steel-4140"]),
            "certified": ValuePredicate(value=True),
        },
    )

    evi = Evidence(
        id="evi-c-1",
        execution_id="exec-c-1",
        intent_id="intent-eval",
        declaration_id="cap-cnc",
        entity_id="mill-3",
        timestamp="2026-08-16T12:00:00Z",
        outcome=OutcomeStatus.COMPLETED,
        observed_metrics={
            "max_tolerance": {"value": 0.03, "unit": "mm"},
            "temp_range": 5.0,
            "material": "Al-6061",
            "certified": True,
        },
    )

    passed, diags = verify_constraints(evi, intent)
    assert passed is True
    assert all(d.result == "satisfied" for d in diags)


def test_constraint_verification_tolerance_exceeded_fails():
    """Evidence metric exceeding requested maximum tolerance fails verification."""
    intent = Intent(
        id="intent-eval",
        goal=SemanticRef(vocabulary="https://pcl.dev/vocab/test", term="machining"),
        constraints={
            "tolerance": Quantity(value=0.05, unit="mm", comparator=Comparator.LTE),
        },
    )
    evi = Evidence(
        id="evi-c-2",
        execution_id="exec-c-2",
        intent_id="intent-eval",
        declaration_id="cap-cnc",
        entity_id="mill-3",
        timestamp="2026-08-16T12:00:00Z",
        outcome=OutcomeStatus.COMPLETED,
        observed_metrics={"tolerance": {"value": 0.08, "unit": "mm"}},
    )

    passed, diags = verify_constraints(evi, intent)
    assert passed is False
    assert any("exceeds required maximum 0.05 mm" in d.reason for d in diags)


def test_constraint_verification_missing_metric_fails_closed():
    """Missing constraint metric in evidence fails closed."""
    intent = Intent(
        id="intent-eval",
        goal=SemanticRef(vocabulary="https://pcl.dev/vocab/test", term="machining"),
        constraints={"required_metric": Quantity(value=10, unit="kg", comparator=Comparator.GTE)},
    )
    evi = Evidence(
        id="evi-c-3",
        execution_id="exec-c-3",
        intent_id="intent-eval",
        declaration_id="cap-cnc",
        entity_id="mill-3",
        timestamp="2026-08-16T12:00:00Z",
        outcome=OutcomeStatus.COMPLETED,
        observed_metrics={},
    )
    passed, diags = verify_constraints(evi, intent)
    assert passed is False
    assert any("required constraint metric 'required_metric' not reported" in d.reason for d in diags)


# ============================================================================
# 5. OUTCOME STATUSES (Partial, Failed, Cancelled) & MULTI-PARTY ATTESTATION
# ============================================================================


def test_partial_outcome_verification():
    """Partial outcome reports quantitative completion while passing structural verification."""
    priv, pub_b64 = generate_ed25519_keypair()
    evi = Evidence(
        id="evi-part",
        execution_id="exec-part",
        intent_id="intent-1",
        declaration_id="cap-1",
        entity_id="robot-1",
        timestamp="2026-08-16T12:00:00Z",
        outcome=OutcomeStatus.PARTIAL,
        summary="Delivered 80 of 100 units due to battery limit",
        observed_metrics={"units_delivered": 80, "units_requested": 100},
    )
    evi.sign(priv, issuer="robot-1", public_key=pub_b64)

    intent = Intent(id="intent-1", goal=SemanticRef(vocabulary="https://pcl.dev/vocab/test", term="task"))
    res = verify_evidence(evi, intent=intent, public_keys={"robot-1": pub_b64})

    assert res.valid is True
    assert res.outcome == "partial"
    assert res.integrity == "verified"


def test_failed_outcome_reports_invalid():
    """Failed execution outcome marks overall verification invalid with diagnostic reason."""
    priv, pub_b64 = generate_ed25519_keypair()
    evi = Evidence(
        id="evi-fail",
        execution_id="exec-fail",
        intent_id="intent-1",
        declaration_id="cap-1",
        entity_id="robot-1",
        timestamp="2026-08-16T12:00:00Z",
        outcome=OutcomeStatus.FAILED,
        summary="Spindle motor stall at 45% completion",
    )
    evi.sign(priv, issuer="robot-1", public_key=pub_b64)

    res = verify_evidence(evi, public_keys={"robot-1": pub_b64})
    assert res.valid is False
    assert res.outcome == "failed"
    assert any("execution reported failed outcome" in d.reason for d in res.diagnostics)


def test_multi_party_attestations_provider_and_consumer():
    """Evidence with multiple attestations (provider + consumer) verifies all signatures."""
    p_priv, p_pub = generate_ed25519_keypair()
    c_priv, c_pub = generate_ed25519_keypair()

    evi = Evidence(
        id="evi-multi",
        execution_id="exec-multi",
        intent_id="intent-1",
        declaration_id="cap-1",
        entity_id="robot-1",
        timestamp="2026-08-16T12:00:00Z",
        outcome=OutcomeStatus.COMPLETED,
    )

    evi.sign(p_priv, issuer="robot-1", role="provider", public_key=p_pub)
    evi.sign(c_priv, issuer="consumer-alpha", role="consumer", public_key=c_pub)

    assert len(evi.attestations) == 2

    res = verify_evidence(
        evi,
        public_keys={"robot-1": p_pub, "consumer-alpha": c_pub},
    )
    assert res.valid is True
    assert res.integrity == "verified"


# ============================================================================
# 6. CONFORMANCE TEST VECTOR VALIDATION & SCHEMA
# ============================================================================


def test_conformance_test_vector():
    """Verify evidence vector against RFC 8785 canonical bytes and signature."""
    vec_path = REPO_ROOT / "spec" / "test-vectors" / "evidence-vectors.json"
    data = json.loads(vec_path.read_text(encoding="utf-8"))

    vec = data["vectors"][0]
    raw_payload = vec["unsigned_evidence_payload"]
    expected_canon = vec["canonical_json_utf8"].encode("utf-8")
    expected_digest = vec["sha256_digest"]
    sig_b64 = vec["signature_b64"]
    pub_b64 = vec["public_key_b64"]

    # 1. Test canonicalization matches
    calc_canon = canonicalize(raw_payload)
    assert calc_canon == expected_canon

    # 2. Test digest matches
    calc_digest = sha256_digest(calc_canon)
    assert calc_digest == expected_digest

    # 3. Test signature verification
    valid = verify_signature(pub_b64, sig_b64, calc_canon, algorithm="ed25519")
    assert valid is True


def test_evidence_schema_validation():
    """Validate constructed evidence document against normative JSON Schema."""
    priv, pub_b64 = generate_ed25519_keypair()
    evi = Evidence(
        id="evi-schema-test",
        execution_id="exec-999",
        intent_id="intent-1",
        declaration_id="cap-1",
        entity_id="robot-1",
        timestamp="2026-08-16T12:00:00Z",
        outcome=OutcomeStatus.COMPLETED,
        artifacts=[
            ArtifactRef(
                type="inspection_report",
                uri="https://reports.pcl.dev/r999.pdf",
                digest="sha256:abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234",
            )
        ],
    )
    evi.sign(priv, issuer="robot-1", public_key=pub_b64)

    errors = validate_document(evi.to_dict(), "evidence")
    assert errors == []


def test_wrong_issuer_key_lookup_failure():
    """Verification fails closed when issuer public key cannot be found."""
    priv, pub_b64 = generate_ed25519_keypair()
    evi = Evidence(
        id="evi-nokey",
        execution_id="exec-1",
        intent_id="intent-1",
        declaration_id="cap-1",
        entity_id="robot-1",
        timestamp="2026-08-16T12:00:00Z",
        outcome=OutcomeStatus.COMPLETED,
    )
    # Sign with issuer 'unknown-entity' and no embedded key
    evi.sign(priv, issuer="unknown-entity", public_key_ref="https://keys.pcl.dev/unknown")
    res, diags = verify_integrity(evi, public_keys={"known-entity": pub_b64})
    assert res is False
    assert any("public key for issuer 'unknown-entity' not found" in d.reason for d in diags)


def test_cancelled_outcome_reports_invalid():
    """Cancelled execution outcome produces invalid verification with cancellation reason."""
    priv, pub_b64 = generate_ed25519_keypair()
    evi = Evidence(
        id="evi-cancel",
        execution_id="exec-cancel",
        intent_id="intent-1",
        declaration_id="cap-1",
        entity_id="robot-1",
        timestamp="2026-08-16T12:00:00Z",
        outcome=OutcomeStatus.CANCELLED,
        summary="Emergency stop pressed by operator",
    )
    evi.sign(priv, issuer="robot-1", public_key=pub_b64)
    res = verify_evidence(evi, public_keys={"robot-1": pub_b64})
    assert res.valid is False
    assert res.outcome == "cancelled"
    assert any("execution was cancelled" in d.reason for d in res.diagnostics)


def test_conflicting_attestations_represented_without_arbitration():
    """Evidence with contradictory attestations (provider vs inspector) verifies all signatures without arbitration."""
    p_priv, p_pub = generate_ed25519_keypair()
    i_priv, i_pub = generate_ed25519_keypair()

    evi = Evidence(
        id="evi-conflict",
        execution_id="exec-conflict",
        intent_id="intent-1",
        declaration_id="cap-1",
        entity_id="robot-1",
        timestamp="2026-08-16T12:00:00Z",
        outcome=OutcomeStatus.PARTIAL,
        summary="Provider claims 100 parts; inspector certifies only 75 parts",
    )
    evi.sign(p_priv, issuer="robot-1", role="provider", public_key=p_pub)
    evi.sign(i_priv, issuer="inspector-agency", role="inspector", public_key=i_pub)

    res = verify_evidence(evi, public_keys={"robot-1": p_pub, "inspector-agency": i_pub})
    # Signatures are valid (integrity verified), but PCL does not pick sides in dispute
    assert res.integrity == "verified"
    assert len(evi.attestations) == 2


def test_unit_mismatch_in_evidence_metric_fails():
    """Observed metric with incompatible unit (e.g. lbs vs kg) fails constraint check."""
    intent = Intent(
        id="intent-unit",
        goal=SemanticRef(vocabulary="https://pcl.dev/vocab/test", term="transport"),
        constraints={"weight": Quantity(value=20, unit="kg", comparator=Comparator.LTE)},
    )
    evi = Evidence(
        id="evi-unit",
        execution_id="exec-unit",
        intent_id="intent-unit",
        declaration_id="cap-1",
        entity_id="robot-1",
        timestamp="2026-08-16T12:00:00Z",
        outcome=OutcomeStatus.COMPLETED,
        observed_metrics={"weight": {"value": 15, "unit": "lbs"}},  # Incompatible unit
    )
    passed, diags = verify_constraints(evi, intent)
    assert passed is False
    assert any("unit mismatch" in d.reason for d in diags)
