# PCL Architecture Reference
**The Physical Capability Language Meta-Model, Execution Lifecycle, and Protocol Boundaries**

---

## 1. Executive Overview

The **Physical Capability Language (PCL)** is an open, machine-readable protocol that bridges high-level Physical AI intent and low-level physical-world execution.

Where software tool abstractions (such as MCP or OpenAPI) describe functional digital endpoints, PCL describes **physical affordances, spatial constraints, operational readiness, and verifiable outcomes** across heterogeneous robots, CNC machines, smart tools, human specialists, and facility infrastructure.

---

## 2. The Irreducible 5-Element Meta-Model

All physical interactions in PCL are grounded in a 5-element tuple:

$$\text{PCL Core} = \langle \text{Actor}, \text{Outcome}, \text{Interface}, \text{Boundary}, \text{Invocation} \rangle$$

```
                                  ┌───────────────────────────┐
                                  │           Actor           │
                                  │         (Entity)          │
                                  └─────────────┬─────────────┘
                                                │ provides
                                                ▼
┌───────────────────────────┐     ┌───────────────────────────┐     ┌───────────────────────────┐
│         Boundary          │◄────┤          Outcome          ├────►│         Interface         │
│     (ConstraintSpec)      │     │       (SemanticRef)       │     │       (IOContract)        │
└───────────────────────────┘     └─────────────┬─────────────┘     └───────────────────────────┘
                                                │ bound by
                                                ▼
                                  ┌───────────────────────────┐
                                  │        Invocation         │
                                  │    (ExecutionBinding)     │
                                  └───────────────────────────┘
```

### The 5 Primitive Elements
1. **Actor (`Entity`)**: The physical identity (robot, machine, human) that performs the physical action.
2. **Outcome (`SemanticRef`)**: The vocabulary-grounded definition of the physical transformation or task being performed.
3. **Interface (`IOContract`)**: The inputs consumed and outputs produced by the physical process.
4. **Boundary (`ConstraintSpec`)**: The physical envelopes, environmental limits, and capability thresholds bounding execution.
5. **Invocation (`ExecutionBinding`)**: The declarative mapping translating abstract intent into native protocol dispatch parameters.

---

## 3. The 12 Core Model Concepts

| Concept | Schema | Description |
| :--- | :--- | :--- |
| **1. Entity** | [`entity.json`](../spec/schemas/entity.json) | Declares a physical device, controller identity, and hardware hierarchy (`contains`). |
| **2. SemanticRef** | [`common.json`](../spec/schemas/common.json) | Grounding reference linking tasks to domain ontology vocabularies (`vocabulary`, `term`). |
| **3. IOContract** | [`common.json`](../spec/schemas/common.json) | Explicit typing and semantics for input and output parameters (`name`, `role`, `value_kind`). |
| **4. ConstraintSpec** | [`common.json`](../spec/schemas/common.json) | Generalized predicate algebra: `Quantity` (LTE, GTE, EQ), `Range`, `SetPredicate`, `ValuePredicate`. |
| **5. ExecutionBinding** | [`common.json`](../spec/schemas/common.json) | Invocation contract specifying protocol (`ros2`, `http`, `opcua`), target, and dot-path parameter mappings. |
| **6. CapabilityDeclaration**| [`capability-declaration.json`](../spec/schemas/capability-declaration.json) | Static capability manifest advertised by a physical entity. |
| **7. CapabilityOffer** | [`capability-offer.json`](../spec/schemas/capability-offer.json) | Dynamic runtime snapshot expressing `state`, `availability`, spatial anchor, and TTL (`valid_until`). |
| **8. Intent** | [`intent.json`](../spec/schemas/intent.json) | Consumer demand specifying the requested goal, input parameters, and required constraint envelopes. |
| **9. MatchResult** | Standard output | Deterministic evaluation result containing matching score, satisfied gates, and structured diagnostics. |
| **10. Evidence** | [`evidence.json`](../spec/schemas/evidence.json) | Post-execution manifest recording observed outputs, measured metrics, and external artifact digests. |
| **11. Attestation** | [`common.json`](../spec/schemas/common.json) | Cryptographic envelope binding an Evidence document to an issuer using Ed25519 or ECDSA P-256 signatures. |
| **12. VerificationResult** | Standard output | Post-execution evaluation result validating cryptographic integrity, provenance linkage, and constraint satisfaction. |

---

## 4. End-to-End Execution Lifecycle

```
1. DECLARATION   Entity advertises CapabilityDeclaration + CapabilityOffer in Registry.
       │
2. INTENT        Consumer or AI Agent submits Intent describing desired outcome.
       │
3. MATCHING      Deterministic 8-gate matching algorithm filters and scores candidates.
       │
4. BINDING       ExecutionBinding maps Intent parameters to native payload.
       │
5. DISPATCH      External Protocol Adapter dispatches native payload to ROS 2 / HTTP / OPC-UA.
       │
6. EXECUTION     Physical robot/machine performs physical work in real world.
       │
7. EVIDENCE      Hardware records observed outputs, sensor metrics, and artifact hashes.
       │
8. ATTESTATION   Issuer cryptographically signs canonical RFC 8785 JCS digest.
       │
9. VERIFICATION  Consumer verifies signatures, provenance tuple, and constraint satisfaction.
```

---

## 5. Protocol Layering & Architectural Separation

```
┌────────────────────────────────────────────────────────────────────────┐
│ APPLICATION & ECOSYSTEM LAYER (Outside Core Protocol)                  │
│ - Distributed Discovery Registries & Indexers                          │
│ - Multi-step Workflow Orchestration DAGs (Temporal, Airflow)          │
│ - Payment, Billing, Escrow, and Court Dispute Resolution Platforms    │
├────────────────────────────────────────────────────────────────────────┤
│ PROTOCOL ADAPTERS (External Plugins)                                   │
│ - ROS 2 Action / Service Adapter                                       │
│ - HTTP / OpenAPI REST Adapter                                          │
│ - OPC-UA / MQTT Industrial Adapters                                    │
│ - W3C Web of Things (WoT) Adapter                                      │
├────────────────────────────────────────────────────────────────────────┤
│ REFERENCE SDK (Python Implementation)                                  │
│ - Document Models, JSON Schema Validators                              │
│ - Matcher Engine, Parameter Resolver, Verification Engine              │
│ - Reference Command-Line Interface (`pcl` CLI)                         │
├────────────────────────────────────────────────────────────────────────┤
│ PCL CORE PROTOCOL (Language-Agnostic Standard)                         │
│ - Normative Specification (`spec/SPEC.md`, `spec/MATCHING.md`)         │
│ - JSON Schema Draft 2020-12 Definitions (`spec/schemas/*.json`)        │
│ - RFC 8785 JSON Canonicalization Scheme + SHA-256 Hashing              │
│ - Ed25519 & ECDSA P-256 Cryptographic Attestation Standards            │
│ - Portable Conformance Test Vectors (`spec/conformance/`)              │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 6. What PCL Explicitly Does NOT Do (Non-Goals)

To preserve protocol minimalism, security, and universality, PCL **explicitly excludes**:

1. **Robot Motion Control & Kinematics:** PCL does not compute joint trajectories, inverse kinematics, or motor PID loops.
2. **Workflow DAG Orchestration:** PCL matches single capability affordances; multi-step task graphs belong in external workflow engines.
3. **Live 100 Hz Telemetry Streaming:** Real-time sensor streams belong in native ROS 2 topics, DDS, or MQTT.
4. **Native Protocol Execution:** PCL core contains no built-in ROS 2 nodes, HTTP clients, or OPC-UA drivers.
5. **Blockchain, Cryptocurrency, or Escrow:** PCL relies on standard asymmetric cryptography and content addressing; financial settlement belongs in payment layers.
6. **Dispute Arbitration:** PCL represents multi-party attestations objectively without embedding legal courts or arbitration consensus rules.
7. **Universal World Ontology:** PCL references external domain vocabularies via URI rather than embedding a rigid universal ontology.
