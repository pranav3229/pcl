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
       External Execution (Dispatched via HTTP Adapter or Native Transport)
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
    "protocol": "http",
    "target": "http://127.0.0.1:8080/api/v1/transport",
    "operation": "POST",
    "parameters_map": {
      "object": "inputs.object.ref",
      "destination": "inputs.destination.ref"
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

### 3. Match, Parameter Resolution & Real HTTP Invocation
```bash
# 1. Match intent against local capability registry
python sdk/python/pcl/cli.py match intent-transport.json

# 2. Resolve native parameters from Intent
python sdk/python/pcl/cli.py resolve-binding --declaration cap-transport.json --intent intent-transport.json

# 3. Dispatch invocation to external endpoint via HTTP adapter
python sdk/python/pcl/cli.py invoke --declaration cap-transport.json --intent intent-transport.json
```

---

## Why PCL for Physical AI Developers?

Robots, CNC workcells, and physical machines already have internal control stacks. PCL provides a standardized capability contract so AI agents and fleet dispatchers can discover, match against, and invoke capabilities without needing custom point-to-point integration code for every device.

### The Core Ontological Model
At its core, PCL separates concerns that are usually tightly coupled in robotics and automation:

| Question | PCL Primitive | Description |
| :--- | :--- | :--- |
| **Who or what provides the capability?** | `Entity` | Physical identity (robot, machine, human, AI agent, or composite cell). |
| **What can it do?** | `CapabilityDeclaration` | Declared semantic task, I/O parameters, and physical boundary constraints. |
| **What does an agent want done?** | `Intent` | Consumer demand specifying requested goal, inputs, and physical constraints. |
| **Can the capability satisfy the intent?** | `Matching` | 8-gate fail-closed deterministic evaluation (goals, I/O, limits, location, state). |
| **How is the intent translated to native APIs?**| `ExecutionBinding` | Declarative EBNF dot-path parameter mapping into HTTP, ROS 2, or OPC-UA. |
| **What actually happened in the physical world?**| `Evidence` | Observed metrics and artifact digests with RFC 8785 JCS + Ed25519 signatures. |

---

## Protocol Comparison & Layering

| Standard / Framework | Primary Focus | Layer in Stack | Relationship to PCL |
| :--- | :--- | :--- | :--- |
| **OpenAPI / REST** | Web service APIs | Transport | Target execution binding for web-connected machines |
| **Model Context Protocol (MCP)** | LLM ↔ Software Tools | Agent/Tool | Complementary standard for digital tools; PCL handles physical-world affordances |
| **ROS 2 & Nav2** | Robotics control & kinematics | Robotics Runtime | Underlying execution system for mobile robots and arms |
| **OPC-UA / MQTT** | Industrial machine telemetry & SCADA | Industrial Bus | Target execution transport for manufacturing equipment |
| **VDA 5050** | AGV/AMR fleet task dispatch | Fleet Dispatch | Lower-level transport protocol for industrial mobile robots |
| **PCL (Physical Capability Language)** | **Physical capability semantics & verification** | **Protocol Layer** | **Universal capability contract & cryptographic verification** |

For a deep architectural essay, see 📖 **[Why PCL? (The Missing Abstraction)](docs/WHY_PCL.md)**.

---

## Runnable End-to-End HTTP Demo

Run a complete 6-stage lifecycle demo against a local mock Autonomous Mobile Robot (AMR) server:

```bash
# Terminal 1: Start local capability mock server
python examples/http/server.py

# Terminal 2: Run complete PCL lifecycle (Match -> Resolve -> HTTP Invoke -> Sign -> Verify)
python examples/http/client.py
```

See [examples/http/README.md](examples/http/README.md) for full instructions and expected output.

---

## Current Status & Roadmap

- **Protocol Specification:** Version `0.1.0` (Draft)
- **Release Version:** `v0.1.0-alpha` (Public Alpha)
- **Python Reference SDK:** `pcl-sdk` `0.1.0a1`
- **Reference Adapters:** Functional `HttpAdapter` included; ROS 2, OPC-UA, and W3C Web of Things bindings specified as declarative stubs (V1 roadmap).
- **Release Stage:** **Public Alpha**
- **Test Suite:** 120/120 unit, adversarial, and conformance tests passing (100% green).
- **Decoupled Architecture:** PCL core remains independent of robot runtime engines, workflow DAGs, and blockchain/token bloat.

---

## Documentation & Standards

- 📖 **[Why PCL?](docs/WHY_PCL.md)**: Deep dive on the problem space, protocol comparisons (MCP, ROS 2, OpenAPI), and architectural rationale.
- 🚀 **[Developer Quickstart](docs/QUICKSTART.md)**: 10-minute walkthrough of declaration, matching, invocation, and verification.
- 📐 **[Architecture Reference](docs/ARCHITECTURE.md)**: Deep dive into the 5-element meta-model and protocol boundaries.
- 🛠️ **[Clean-Room Implementation Guide](docs/CLEAN_ROOM_IMPLEMENTATION.md)**: How to implement PCL in Rust, Go, TypeScript, or C++.
- 🤖 **[Robotics Integration Guide](docs/BUILDING_WITH_PCL.md)**: How Physical AI teams integrate PCL above ROS 2 and HTTP bridges.
- 📜 **[Normative Core Specification](spec/SPEC.md)**: Authoritative wire format and evaluation rules.
- 🎯 **[Normative Matching Specification](spec/MATCHING.md)**: 8-gate matching logic and ranking score formula.
- 🧪 **[Language-Agnostic Conformance Vectors](spec/conformance/)**: Portable JSON test vectors for matching, spatial distance, parameter resolution, JCS canonicalization, and signature verification.
- 📋 **[Public Release & Conformance Audit](docs/PUBLIC_RELEASE_AUDIT.md)**: Audit summary and conformance status for v0.1.0-alpha.
- 📦 **[Release Notes](docs/releases/0.1.0-alpha.md)**: Release notes for v0.1.0-alpha.

---

## Repository Structure

```
pcl/
├── README.md               # Landing documentation & protocol overview
├── LICENSE                 # Apache License 2.0
├── CONTRIBUTING.md         # Open-source contribution guidelines
├── SECURITY.md             # Security and vulnerability disclosure policy
├── CHANGELOG.md            # Release changelog (Keep a Changelog format)
├── docs/                   # Developer documentation & architecture guides
│   ├── WHY_PCL.md
│   ├── QUICKSTART.md
│   ├── ARCHITECTURE.md
│   ├── BUILDING_WITH_PCL.md
│   ├── CLEAN_ROOM_IMPLEMENTATION.md
│   ├── FUTURE_ECOSYSTEM.md
│   ├── PUBLIC_RELEASE_AUDIT.md
│   ├── PUBLIC_RELEASE_AUDIT.json
│   ├── VERSIONING.md
│   └── releases/
│       └── 0.1.0-alpha.md
├── spec/                   # Normative protocol specifications
│   ├── SPEC.md             # Wire format specification
│   ├── MATCHING.md         # Matching & ranking specification
│   ├── schemas/            # JSON Schema Draft 2020-12 schemas
│   ├── examples/           # Canonical example documents
│   └── conformance/        # Language-agnostic JSON test vectors
├── sdk/python/             # Python reference SDK & CLI tool (`pcl-sdk`)
├── adapters/               # Protocol adapters (Functional HTTP adapter; ROS 2 / OPC-UA stubs)
├── examples/               # Runnable end-to-end examples (HTTP AMR capability demo)
│   └── http/
├── registry/               # Local capability registry fixtures
└── tests/                  # Automated test suite (120 tests)
```

---

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.

Copyright (c) 2026 Pranav Tanna.
