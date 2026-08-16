# The Future PCL Ecosystem
**Strategic Layering: Core Protocol vs. Ecosystem Infrastructure**

---

## 1. The Core Protocol Invariant

The **Physical Capability Language (PCL)** is designed as a minimal, decentralized protocol standard.

Like HTTP, SMTP, or SQL, PCL defines **wire formats, evaluation rules, and verification semantics**. PCL does **not** mandate a single centralized server, hosted cloud platform, or global database.

---

## 2. Layering: Protocol vs. Future Ecosystem Services

```
┌────────────────────────────────────────────────────────────────────────┐
│ FUTURE APPLICATION & ECOSYSTEM LAYER (Explicitly Decoupled)            │
│ - Distributed Capability Discovery Registries & Search Indexers        │
│ - Multi-Robot Task Orchestration Engines (Temporal, Airflow DAGs)      │
│ - Payment Settlement, Escrow, and SLA Arbitration Services             │
│ - Web-based Fleet Dashboards & Telemetry Visualizers                   │
├────────────────────────────────────────────────────────────────────────┤
│ PROTOCOL ADAPTERS (Transport Layer)                                    │
│ - ROS 2 Action / Service Bridges, OPC-UA, HTTP REST, MQTT Adapters     │
├────────────────────────────────────────────────────────────────────────┤
│ PCL CORE PROTOCOL (The Open Standard)                                  │
│ - Normative JSON Schemas, Matching Algebra, Parameter Grammar          │
│ - RFC 8785 JCS Canonicalization & Ed25519 Cryptographic Verification   │
│ - Language-Agnostic Conformance Test Suites                            │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. The Future Registry Model (High-Level Concept)

In future development phases, community and enterprise registries may be deployed to index capabilities across organizations.

### How Future Registries Will Interact with PCL:
1. **Capabilities Stored as Standard PCL Documents:** Registries store immutable `CapabilityDeclaration` manifests and periodic `CapabilityOffer` availability snapshots.
2. **Standard Query Interface:** Consumers query registries using standard `Intent` documents.
3. **Federation without Lock-In:** Organizations can run private internal registries (e.g. within an air-gapped manufacturing plant) or federate with public capability networks.
4. **Decoupled Settlement:** Commercial transactions, billing, and escrow belong in dedicated marketplace gateways built on top of PCL verification evidence.

---

## 4. Summary

By keeping the registry and application services outside PCL core, the standard remains permanent, secure, and vendor-neutral.
