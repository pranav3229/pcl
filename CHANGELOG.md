# Changelog
All notable changes to the Physical Capability Language (PCL) specification and reference SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0-alpha] - 2026-08-16

### Added
- **Core Meta-Model:** Initial formal specification of the 5-element capability abstraction: $\langle \text{Actor}, \text{Outcome}, \text{Interface}, \text{Boundary}, \text{Invocation} \rangle$.
- **Normative JSON Schemas:** Draft 2020-12 schemas for `Entity`, `CapabilityDeclaration`, `CapabilityOffer`, `Intent`, `Evidence`, and `Common` definitions.
- **Deterministic Matching Pipeline:** 8-gate fail-closed capability matching engine with mathematical ranking scores and structured `ConstraintDiagnostic` reporting.
- **Generalized Constraint Algebra:** Set-theoretic evaluation for `Quantity` (LTE, GTE, EQ), `Range` intervals, `SetPredicate` membership, and literal `ValuePredicate` flags.
- **Geodesic Spatial Semantics:** WGS84 (EPSG:4326) coordinate spatial anchors with Haversine distance proximity gating ($R = 6371.0088\text{ km}$).
- **State & Availability Decoupling:** Hardware `RuntimeState` separated from dispatcher `Availability` policy and `valid_until` TTL expiration.
- **Declarative Invocation Bindings:** `ExecutionBinding` parameter mapping from Intent fields to native protocol dispatch payloads via EBNF dot-path grammar.
- **Outcome Evidence & Attestation:** Post-execution `Evidence` manifest with external content-addressed `ArtifactRef` digests.
- **Cryptographic Suites:** RFC 8785 JSON Canonicalization Scheme (JCS), SHA-256 digests, and Ed25519 / ECDSA P-256 digital signature verification.
- **Deterministic Verifier:** 4-tier verification engine validating Schema, Integrity, Provenance linkage, and original Intent constraint satisfaction.
- **Language-Agnostic Conformance Suite:** Standalone portable JSON test vectors in `spec/conformance/` for matching, spatial distance, parameter resolution, canonicalization, and evidence verification.
- **Python Reference SDK & CLI:** `pcl-sdk` reference implementation with CLI commands (`validate`, `match`, `resolve-binding`, `invoke`, `verify`).
- **HTTP Execution Adapter (`adapters.HttpAdapter`):** Functional protocol adapter executing real HTTP requests (POST, PUT, GET, PATCH, DELETE) with JSON payload serialization, request timeout controls, and structured error handling.
- **End-to-End HTTP Demonstration:** Standalone runnable demo in `examples/http/` featuring a mock Autonomous Mobile Robot (AMR) capability server and a 6-stage lifecycle driver script.
- **Developer Documentation:** `README.md`, `docs/QUICKSTART.md`, `docs/ARCHITECTURE.md`, `docs/CLEAN_ROOM_IMPLEMENTATION.md`, `docs/BUILDING_WITH_PCL.md`, `examples/http/README.md`.

### Known Limitations & Non-Goals
- **No Distributed Registry:** Registry indexing and federation are explicitly deferred to the application/ecosystem layer.
- **No Kinematics / Motion Control:** PCL describes capability affordances, leaving real-time trajectory execution to ROS 2 / native controllers.
- **No Workflow Orchestration:** Complex multi-step task DAGs belong in external orchestration engines (Temporal, Airflow).
- **No In-Core Protocol Drivers:** Core PCL does not spawn ROS nodes or HTTP servers; dispatch is handled by external adapters (e.g. `adapters.HttpAdapter`).
- **ROS 2 & Industrial Stubs:** ROS 2, OPC-UA, and W3C WoT adapters remain declarative parameter stubs in v0.1 (native I/O is V1 roadmap).
