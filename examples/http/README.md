# PCL HTTP Execution Adapter — End-to-End Demo

This example demonstrates the complete 6-stage lifecycle of the Physical Capability Language (PCL) executing an Autonomous Mobile Robot (AMR) transport task over a real HTTP connection.

---

## What Happens in this Demo

```
  1. Intent Match ──► 2. Parameter Resolve ──► 3. Real HTTP Request ──► 4. Robot Server Executes
                                                                                   │
  6. Cryptographic Verify ◄── 5. Ed25519 Signed Evidence ◄─────────────────────────┘
```

1. **Deterministic Matching**: Evaluates consumer `Intent` against `CapabilityDeclaration` across goal, input, and physical constraint gates (`max_payload <= 25 kg`, `deadline <= 30 min`).
2. **Parameter Resolution**: Translates abstract intent fields into native HTTP JSON body parameters according to the declaration's `parameters_map`.
3. **HTTP Dispatch**: `HttpAdapter` opens an HTTP connection and sends a `POST /api/v1/transport` request to the local mock robot capability server.
4. **Physical Execution Simulation**: The server receives the payload and returns an execution report containing observed metrics (`distance_km: 1.1`, `max_payload: 10.0 kg`) and artifact digests (`delivery_photo`).
5. **Cryptographic Attestation**: The client serializes the execution record into RFC 8785 canonical JSON, calculates the SHA-256 digest, and signs it with an Ed25519 private key.
6. **Deterministic Verification**: `verify_evidence` validates cryptographic signature integrity, provenance linkage, and confirms observed metrics satisfied original intent constraints.

---

## How to Run (Takes 1 minute)

### Terminal 1: Start Local Robot Capability Server

```bash
python examples/http/server.py
```

Output:
```
==================================================
PCL Capability HTTP Server (Mock Robot-17 AMR)
Listening on: http://127.0.0.1:8080
Endpoint:     http://127.0.0.1:8080/api/v1/transport
Health Check: http://127.0.0.1:8080/health
==================================================
```

---

### Terminal 2: Run End-to-End PCL Lifecycle

```bash
python examples/http/client.py
```

Alternatively, test invoking via the PCL CLI directly:

```bash
python -m pcl.cli invoke --declaration examples/http/cap-transport-http.json --intent examples/http/intent-transport.json
```

---

## Expected Output

```
================================================================================
PHYSICAL CAPABILITY LANGUAGE (PCL) — HTTP EXECUTION LIFECYCLE DEMO
================================================================================

[STAGE 1] Loading Intent and Provider Capability...
  • Consumer Intent:   intent-http-transport-001 (Goal: package_transport)
  • Provider Entity:   robot-17 (cap-transport-http-amr)
  • Bound Protocol:    http -> http://127.0.0.1:8080/api/v1/transport
  ✅ MATCH SUCCESSFUL (Score: 100.5)
     Satisfied Gates: goal, inputs, constraints, state, availability

[STAGE 2] Resolving Abstract Intent to Native Invocation Payload...
  • Resolved Native HTTP JSON Body:
{
    "object": "package-123",
    "from": "warehouse-floor-2",
    "to": "zone-B"
}

[STAGE 3] Dispatching Invocation via HttpAdapter to http://127.0.0.1:8080/api/v1/transport...
  ✅ HTTP 200 OK (Execution Success)
  • Returned Payload:
{
    "status": "completed",
    "execution_id": "exec-http-8801",
    "summary": "Package package-123 successfully transported from warehouse-floor-2 to zone-B",
    "outputs": {
        "delivered_object": {
            "ref": "package-123"
        }
    },
    "metrics": {
        "max_payload": 10.0,
        "deadline": 12.5,
        "distance_km": 1.1
    },
    "artifacts": [
        {
            "type": "delivery_photo",
            "uri": "https://storage.pcl.dev/blobs/robot17-dropoff-8801.jpg",
            "digest": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "description": "Optical confirmation of package dropoff"
        }
    ]
}

[STAGE 4 & 5] Constructing & Signing Outcome Evidence...
  • Attestation Issuer:   robot-17 (provider)
  • Canonical SHA-256:    sha256:...
  • Ed25519 Signature:    ...

[STAGE 6] Verifying Evidence Against Intent & Declaration Contracts...
  • Cryptographic Integrity: VERIFIED
  • Provenance Linkage:      VERIFIED
  • Constraint Satisfaction: SATISFIED
  • Outcome Status:          COMPLETED

================================================================================
✅ PCL LIFECYCLE COMPLETED SUCCESSFULLY — OUTCOME VERIFIED
================================================================================
```

---

## Files in this Directory

- [`server.py`](server.py): Zero-dependency local mock AMR capability server.
- [`client.py`](client.py): End-to-end PCL lifecycle driver demonstrating matching, parameter resolution, HTTP invocation, and verification.
- [`cap-transport-http.json`](cap-transport-http.json): Capability declaration exposing HTTP execution binding.
- [`offer-transport-http.json`](offer-transport-http.json): Capability runtime offer declaring availability state.
- [`intent-transport.json`](intent-transport.json): Consumer intent requesting package transport.
