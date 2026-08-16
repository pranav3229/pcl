# Physical Capability Language (PCL)

> **PCL is an open protocol for expressing physical intent, advertising physical capabilities, deterministically matching demand to capability, mapping matched intent to native execution interfaces, and verifying physical outcomes.**

---

## The Problem

Modern AI agents and software systems can plan complex tasks, but connecting digital intelligence to the physical world remains fragmented:

- **ROS 2 & DDS** handle real-time robotics messaging, kinematics, and control.
- **OPC-UA & MQTT** handle industrial machine telemetry and device connectivity.
- **MCP & OpenAPI** describe digital tool interfaces and software APIs.
- **Workflow Engines (Temporal, Airflow)** orchestrate multi-step task graphs.

**What is missing is a common, machine-readable protocol for describing what physical systems can do, what tasks humans or AI agents need done, and whether an executed task actually satisfied physical constraints.**

PCL sits above native execution protocols. It describes **what** a physical provider can do, deterministically matches consumer **intents** to provider **capabilities**, translates intent into **native execution parameters**, and cryptographically **verifies outcome evidence**.

---

## The PCL Lifecycle

```
    Capability Declaration (Advertised by Robot / Machine / Specialist)
                 │
                 ▼
          Consumer Intent (Submitted by Physical AI / Software Agent)
                 │
                 ▼
       Deterministic Matching (8-Gate Constraint & Spatial Evaluation)
                 │
                 ▼
       Invocation Binding (Maps Intent parameters to Native Payload)
                 │
                 ▼
       External Execution (Dispatched via ROS 2 / HTTP / OPC-UA / MQTT)
                 │
                 ▼
          Outcome Evidence (Observed Metrics & Sensor Artifact Hashes)
                 │
                 ▼
       Cryptographic Attestation (Signed via RFC 8785 JCS + Ed25519)
                 │
                 ▼
       Deterministic Verification (Validates Integrity, Provenance & Constraints)
```

---

## Minimal Example

### 1. Capability Declaration (`cap-transport.json`)
```json
{
  "pcl_version": "0.1.0",
  "id": "cap-transport-robot17",
  "entity_id": "robot-17",
  "semantic_type": { "vocabulary": "https://pcl.dev/vocab/logistics/v0", "term": "package_transport" },
  "inputs": [
    { "name": "object", "role": "object", "value_kind": "entity_ref", "required": true },
    { "name": "destination", "role": "destination", "value_kind": "location_ref", "required": true }
  ],
  "constraints": [
    { "name": "max_payload", "quantity": { "value": 25, "unit": "kg", "comparator": "lte" } }
  ],
  "execution": {
    "protocol": "ros2",
    "target": "/robot17/deliver",
    "operation": "send_goal",
    "parameters_map": {
      "goal.package_id": "inputs.object.ref",
      "goal.target_bay": "inputs.destination.ref"
    }
  }
}
```

### 2. Consumer Intent (`intent-transport.json`)
```json
{
  "pcl_version": "0.1.0",
  "id": "intent-package-01",
  "goal": { "vocabulary": "https://pcl.dev/vocab/logistics/v0", "term": "package_transport" },
  "inputs": {
    "object": { "ref": "package-123" },
    "destination": { "ref": "bay-12" }
  },
  "constraints": {
    "max_payload": { "value": 10, "unit": "kg", "comparator": "lte" }
  }
}
```

### 3. Match & Parameter Resolution
```bash
# Match intent against local registry
python sdk/python/pcl/cli.py match intent-transport.json

# Resolve native ROS 2 parameters
python sdk/python/pcl/cli.py resolve-binding --declaration cap-transport.json --intent intent-transport.json
```

**Resolved Native Payload:**
```json
{
  "goal": {
    "package_id": "package-123",
    "target_bay": "bay-12"
  }
}
```

---

## Why PCL for Physical AI Developers?

> *"My robot already works. PCL gives me a standardized way to describe what it can do so an external AI agent or fleet dispatcher can discover and invoke that capability without knowing my internal ROS 2 topics or kinematics stack."*

- **Protocol Agnostic:** Works across ROS 2, HTTP REST, OPC-UA, W3C Web of Things, and custom protocols.
- **Deterministic & Fail-Closed:** No non-deterministic LLM hallucinations during matching or verification.
- **Spatial & Temporal Grounding:** Standardized WGS84 geodesic proximity and TTL availability gating.
- **Cryptographic Trust:** Post-execution verification using RFC 8785 JSON Canonicalization Scheme (JCS) and Ed25519 signatures.

---

## Current Status & Roadmap

- **Protocol Version:** `0.1.0-draft`
- **Release Stage:** **Public Alpha Preparation**
- **Test Suite:** 111/111 unit, adversarial, and conformance tests passing (100% green).
- **Decoupled Architecture:** PCL core remains independent of robot runtime engines, workflow DAGs, and blockchain/token bloat.

---

## Documentation & Standards

- 🚀 **[Developer Quickstart](docs/QUICKSTART.md)**: 10-minute walkthrough of declaration, matching, invocation, and verification.
- 📐 **[Architecture Reference](docs/ARCHITECTURE.md)**: Deep dive into the 5-element meta-model and protocol boundaries.
- 🛠️ **[Clean-Room Implementation Guide](docs/CLEAN_ROOM_IMPLEMENTATION.md)**: How to implement PCL in Rust, Go, TypeScript, or C++.
- 📜 **[Normative Core Specification](spec/SPEC.md)**: Authoritative wire format and evaluation rules.
- 🎯 **[Normative Matching Specification](spec/MATCHING.md)**: 8-gate matching logic and ranking score formula.
- 🧪 **[Language-Agnostic Conformance Vectors](spec/conformance/)**: Portable JSON test vectors for matching, spatial distance, parameter resolution, JCS canonicalization, and signature verification.
- 📋 **[Open-Source Governance & Legal Checklist](docs/OPEN_SOURCE_TODO.md)**: Director checklist for public licensing and governance.

---

## Repository Structure

```
pcl/
├── README.md               # Landing documentation
├── docs/                   # Developer documentation & architecture guides
│   ├── QUICKSTART.md
│   ├── ARCHITECTURE.md
│   ├── CLEAN_ROOM_IMPLEMENTATION.md
│   └── OPEN_SOURCE_TODO.md
├── spec/                   # Normative protocol specifications
│   ├── SPEC.md             # Wire format specification
│   ├── MATCHING.md         # Matching & ranking specification
│   ├── schemas/            # JSON Schema Draft 2020-12 schemas
│   ├── examples/           # Canonical example documents
│   └── conformance/        # Language-agnostic JSON test vectors
├── sdk/python/             # Python reference SDK & CLI tool
├── adapters/               # Optional protocol adapters (ROS 2, HTTP, OPC-UA)
├── registry/               # Local capability registry fixture
└── tests/                  # Automated test suite
```

---

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.

Copyright (c) 2026 Pranav Tanna.
