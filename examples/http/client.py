#!/usr/bin/env python3
"""End-to-End PCL HTTP Execution Lifecycle Demonstration.

Demonstrates the complete 6-stage PCL workflow:
1. Match: Deterministic capability matching against provider offer
2. Resolve: Map abstract Intent inputs to native HTTP JSON payload
3. Dispatch: Invoke real HTTP endpoint via HttpAdapter
4. Result: Inspect execution status, measured metrics, and artifact digests
5. Attest: Construct and sign an Evidence document using Ed25519
6. Verify: Validate cryptographic integrity, provenance, and constraint satisfaction
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure repo root and sdk/python are in sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "sdk" / "python"))

from adapters.base import HttpAdapter
from pcl.crypto import generate_ed25519_keypair
from pcl.matcher import match_intent_to_offer
from pcl.models import (
    CapabilityDeclaration,
    CapabilityOffer,
    Evidence,
    Intent,
    OutcomeStatus,
)
from pcl.verifier import verify_evidence


def run_demo() -> None:
    demo_dir = Path(__file__).resolve().parent

    decl_file = demo_dir / "cap-transport-http.json"
    offer_file = demo_dir / "offer-transport-http.json"
    intent_file = demo_dir / "intent-transport.json"

    print("================================================================================")
    print("PHYSICAL CAPABILITY LANGUAGE (PCL) -- HTTP EXECUTION LIFECYCLE DEMO")
    print("================================================================================")

    # -------------------------------------------------------------------------
    # STAGE 1: LOAD DOCUMENTS & EXECUTE DETERMINISTIC MATCHING
    # -------------------------------------------------------------------------
    print("\n[STAGE 1] Loading Intent and Provider Capability...")
    intent = Intent.from_file(intent_file)
    declaration = CapabilityDeclaration.from_file(decl_file)
    offer = CapabilityOffer.from_file(offer_file)

    print(f"  * Consumer Intent:   {intent.id} (Goal: {intent.goal.term})")
    print(f"  * Provider Entity:   {declaration.entity_id} ({declaration.id})")
    print(f"  * Bound Protocol:    {declaration.execution.protocol} -> {declaration.execution.target}")

    match_result = match_intent_to_offer(intent, offer, declaration)
    if match_result is None:
        print("[FAIL] MATCH REJECTED: Intent constraints cannot be satisfied by provider.")
        sys.exit(1)

    print(f"  [OK] MATCH SUCCESSFUL (Score: {match_result.score:.1f})")
    print(f"       Satisfied Gates: {', '.join(match_result.satisfied)}")

    # -------------------------------------------------------------------------
    # STAGE 2: INVOCATION PARAMETER RESOLUTION
    # -------------------------------------------------------------------------
    print("\n[STAGE 2] Resolving Abstract Intent to Native Invocation Payload...")
    native_payload = declaration.execution.resolve_parameters(
        inputs=intent.inputs,
        constraints=intent.constraints,
    )
    print("  * Resolved Native HTTP JSON Body:")
    print(json.dumps(native_payload, indent=4))

    # -------------------------------------------------------------------------
    # STAGE 3: HTTP ADAPTER DISPATCH
    # -------------------------------------------------------------------------
    print(f"\n[STAGE 3] Dispatching Invocation via HttpAdapter to {declaration.execution.target}...")
    adapter = HttpAdapter(default_timeout=5.0)
    exec_result = adapter.invoke(
        declaration.execution,
        inputs=intent.inputs,
        context={"constraints": intent.constraints},
    )

    if not exec_result.success:
        print(f"[FAIL] HTTP INVOCATION FAILED: {exec_result.error}")
        print("Is the local capability server running? (Run: python examples/http/server.py)")
        sys.exit(1)

    print(f"  [OK] HTTP 200 OK (Execution Success)")
    print(f"  * Returned Payload:")
    print(json.dumps(exec_result.payload, indent=4))

    # -------------------------------------------------------------------------
    # STAGE 4 & 5: EVIDENCE CONSTRUCTION & CRYPTOGRAPHIC ATTESTATION
    # -------------------------------------------------------------------------
    print("\n[STAGE 4 & 5] Constructing & Signing Outcome Evidence...")
    resp_body = exec_result.payload
    priv_key, pub_b64 = generate_ed25519_keypair()

    evidence = Evidence(
        pcl_version="0.1.0",
        id="evi-transport-http-demo-01",
        execution_id=resp_body.get("execution_id", "exec-unknown"),
        intent_id=intent.id,
        declaration_id=declaration.id,
        entity_id=declaration.entity_id,
        timestamp="2026-08-16T12:00:00Z",
        outcome=OutcomeStatus.COMPLETED,
        summary=resp_body.get("summary"),
        observed_outputs=resp_body.get("outputs", {}),
        observed_metrics=resp_body.get("metrics", {}),
        artifacts=resp_body.get("artifacts", []),
    )

    att = evidence.sign(
        private_key=priv_key,
        issuer=declaration.entity_id,
        role="provider",
        algorithm="ed25519",
        public_key=pub_b64,
        timestamp="2026-08-16T12:00:05Z",
    )

    print(f"  * Attestation Issuer:   {att.issuer} ({att.role})")
    print(f"  * Canonical SHA-256:    {evidence.digest()}")
    print(f"  * Ed25519 Signature:    {att.signature[:32]}... ({len(att.signature)} chars)")

    # -------------------------------------------------------------------------
    # STAGE 6: DETERMINISTIC EVIDENCE VERIFICATION
    # -------------------------------------------------------------------------
    print("\n[STAGE 6] Verifying Evidence Against Intent & Declaration Contracts...")
    verification = verify_evidence(
        evidence=evidence,
        intent=intent,
        declaration=declaration,
        public_keys={declaration.entity_id: pub_b64},
    )

    print(f"  * Cryptographic Integrity: {verification.integrity.upper()}")
    print(f"  * Provenance Linkage:      {verification.provenance.upper()}")
    print(f"  * Constraint Satisfaction: {verification.constraint_satisfaction.upper()}")
    print(f"  * Outcome Status:          {verification.outcome.upper()}")

    if verification.valid:
        print("\n================================================================================")
        print("[SUCCESS] PCL LIFECYCLE COMPLETED SUCCESSFULLY -- OUTCOME VERIFIED")
        print("================================================================================")
    else:
        print("\n[FAIL] EVIDENCE VERIFICATION FAILED:")
        for d in verification.diagnostics:
            if d.result == "rejected":
                print(f"  - {d.constraint}: {d.reason}")
        sys.exit(1)


if __name__ == "__main__":
    run_demo()
