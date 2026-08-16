# PCL Protocol Versioning Policy
**Semantic Versioning for the Physical Capability Language Standard**

---

## 1. Overview

The **Physical Capability Language (PCL)** follows [Semantic Versioning 2.0.0](https://semver.org/) for all protocol specifications, JSON schemas, reference implementations, and conformance test suites.

---

## 2. Release Identification

- **Current Protocol Specification Version:** `0.1.0`
- **Current Milestone Release Tag:** `v0.1.0-alpha`
- **Document Wire Property:** Every normative PCL document (Entity, CapabilityDeclaration, CapabilityOffer, Intent, Evidence) MUST include:
  ```json
  "pcl_version": "0.1.0"
  ```

---

## 3. Versioning Relationships

```
┌────────────────────────────────────────────────────────┐
│ PCL Core Protocol Specification (`spec/SPEC.md`)       │
│ Declares standard version `MAJOR.MINOR.PATCH`          │
└───────────────────────────┬────────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
┌─────────────────┐┌─────────────────┐┌─────────────────┐
│  JSON Schemas   ││   Conformance   ││  Reference SDK  │
│ `spec/schemas/` ││`spec/conformance`││  `sdk/python/`  │
│  Version 0.1.0  ││  Version 0.1.0  ││ Version 0.1.0a1 │
└─────────────────┘└─────────────────┘└─────────────────┘
```

1. **JSON Schemas:** Schemas track the core protocol version. A change to a schema requires an update to the specification version.
2. **Conformance Vectors:** Conformance test fixtures match the targeted protocol version.
3. **Reference SDK & Independent Implementations:** Language SDKs track the protocol version for wire compatibility, appending implementation pre-release/build identifiers (e.g. `0.1.0a1`, `0.1.0-rs.1`).

---

## 4. SemVer Rules & Change Classification

### Major Version Increments (`X.0.0`): Breaking Protocol Changes
A major version bump occurs when:
- Removing, renaming, or changing the type of any required core schema property.
- Modifying the 5-element meta-model ($\langle \text{Actor}, \text{Outcome}, \text{Interface}, \text{Boundary}, \text{Invocation} \rangle$).
- Changing the evaluation algebra of existing constraint predicates (`Quantity`, `Range`, `Set`, `Value`).
- Changing the canonicalization standard (RFC 8785 JCS) or hash construction.
- Modifying the 8-gate matching logic in a way that breaks existing valid matches.

### Minor Version Increments (`0.X.0` or `1.X.0`): Backward-Compatible Additions
A minor version bump occurs when:
- Adding new optional fields to existing schemas.
- Adding support for new cryptographic signature algorithms (e.g., post-quantum suites).
- Adding new standard protocol adapter identifier types.
- Introducing new optional constraint predicate forms.

### Patch Version Increments (`0.1.X`): Non-Normative Clarifications
A patch version bump occurs when:
- Clarifying prose in `spec/SPEC.md` or `spec/MATCHING.md` without altering evaluation logic.
- Adding new conformance test vectors that test previously specified behavior.
- Fixing typos, markdown formatting, or documentation examples.

---

## 5. Extension Field Governance

To prevent fragmentation and breaking changes:
- Core schemas enforce `"additionalProperties": false`.
- All custom, vendor-specific, or domain-experimental metadata MUST be placed inside the `"extensions": {}` object.
- Conformant implementations MUST ignore unknown keys within `extensions: {}`.
