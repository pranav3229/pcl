# PCL v0.1.0-alpha Release & Conformance Audit

**Specification:** Physical Capability Language (PCL)
**Wire Version:** `0.1.0`
**Release Tag:** `v0.1.0-alpha`
**Package Version:** `pcl-sdk==0.1.0a1`
**License:** Apache License 2.0
**Copyright:** Copyright (c) 2026 Pranav Tanna

---

## 1. Executive Summary

This document summarizes the release readiness, specification conformance, and security posture of the **Physical Capability Language (PCL)** repository for the **v0.1.0-alpha** release.

PCL is an open, vendor-neutral protocol for declaring, discovering, binding, and verifying physical capabilities and intents across robots, machines, and Physical AI agents.

---

## 2. Protocol & Specification State

- **Normative Specification:** Authored in [`spec/SPEC.md`](../spec/SPEC.md) and [`spec/MATCHING.md`](../spec/MATCHING.md).
- **JSON Schemas:** Normative Draft 2020-12 schemas published under [`spec/schemas/`](../spec/schemas/) (`entity.json`, `capability-declaration.json`, `capability-offer.json`, `intent.json`, `evidence.json`, `common.json`).
- **Deterministic 8-Gate Matcher:** Implements exact, fail-closed matching across goal semantics, inputs, outputs, generalized constraints (Quantity, Range, Set, Value), spatial proximity (WGS84 Haversine), runtime state, and availability TTL.
- **Language-Agnostic Conformance Vectors:** Portable JSON fixtures located in [`spec/conformance/`](../spec/conformance/) validating matching, spatial math, parameter mapping, RFC 8785 JCS canonicalization, and cryptographic signature verification across independent implementations.

---

## 3. Reference Implementation & Testing

- **Reference SDK:** Python reference implementation located in [`sdk/python/`](../sdk/python/).
- **CLI Commands:** `pcl validate`, `pcl match`, `pcl resolve-binding`, `pcl verify`.
- **Test Suite Results:**
  - **112 / 112 automated tests passing** (100% green).
  - Multi-tier coverage spanning unit tests, adversarial constraint boundaries, composition, cryptographic verification, and language-agnostic conformance vectors.
- **Continuous Integration:** GitHub Actions workflow ([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)) testing across Ubuntu and Windows on Python 3.11, 3.12, and 3.13 with least-privilege permissions (`contents: read`).

---

## 4. Security & Cryptography Posture

- **Cryptographic Verification:** Ed25519 and ECDSA P-256 digital signatures over RFC 8785 JSON Canonicalization Scheme (JCS) payloads.
- **Fail-Closed Verification:** Unsupported algorithms, tampered manifests, and mismatched keys fail closed unconditionally.
- **Content Addressing:** External physical artifacts (e.g. photos, scans) referenced by cryptographic digests (`sha256:...`).
- **Security Policy:** Coordinated vulnerability disclosure policy detailed in [`SECURITY.md`](../SECURITY.md).

---

## 5. Scope Boundaries & Known Limitations

To maintain a clean architectural boundary, the following are intentionally decoupled from the core protocol:

1. **Decoupled Registry & Discovery Layer:** PCL specifies capability document schemas and matching rules; distributed network registries, discovery daemons, and cloud indexers belong in external application services (see [`docs/FUTURE_ECOSYSTEM.md`](FUTURE_ECOSYSTEM.md)).
2. **Decoupled Robot Execution:** PCL sits above native execution runtimes (ROS 2, OPC-UA, HTTP); real-time motion control, trajectory planning, and hardware loops remain with native robot controllers.
3. **Decoupled Workflow Orchestration:** Complex multi-step task DAGs belong in external orchestration platforms (e.g., Temporal, Airflow).
