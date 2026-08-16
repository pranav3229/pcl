# PCL Clean-Room Implementation Guide
**Language-Independent Protocol Implementation Reference**

---

## 1. Introduction

The **Physical Capability Language (PCL)** is an open, language-agnostic protocol for describing, discovering, matching, invoking, and verifying physical-world capabilities across robots, machines, humans, and infrastructure.

The Python SDK in this repository is a **reference implementation**. It is **not** the definition of PCL. An independent engineer building an implementation in **Rust, Go, TypeScript, C++, or Swift** must implement the protocol purely against:

1. **Normative Specifications:** [`spec/SPEC.md`](../spec/SPEC.md) & [`spec/MATCHING.md`](../spec/MATCHING.md).
2. **Normative JSON Schemas:** [`spec/schemas/*.json`](../spec/schemas/).
3. **Portable Conformance Vectors:** [`spec/conformance/`](../spec/conformance/).

---

## 2. Core Meta-Model

An independent implementation must model the 5 irreducible primitives:

$$\text{PCL Core} = \langle \text{Actor}, \text{Outcome}, \text{Interface}, \text{Boundary}, \text{Invocation} \rangle$$

| Protocol Element | Wire Schema | Responsibility |
| :--- | :--- | :--- |
| **Actor** | [`entity.json`](../spec/schemas/entity.json) | The physical entity/machine providing capabilities. |
| **Outcome** | [`common.json#/$defs/SemanticRef`](../spec/schemas/common.json) | The vocabulary-grounded physical goal or task. |
| **Interface** | [`common.json#/$defs/IOContract`](../spec/schemas/common.json) | Inputs required and outputs produced. |
| **Boundary** | [`common.json#/$defs/ConstraintSpec`](../spec/schemas/common.json) | Physical limits (Quantity, Range, Set, Categorical, Boolean). |
| **Invocation** | [`common.json#/$defs/ExecutionBinding`](../spec/schemas/common.json) | Protocol-agnostic mapping to native execution endpoints. |

---

## 3. The 5 Conceptual Pipeline Operations

A compliant PCL SDK must implement these 5 functional operations:

```
                  ┌────────────────────────────────────────┐
                  │ 1. Document Schema Validation          │
                  │    (JSON Schema Draft 2020-12)         │
                  └──────────────────┬─────────────────────┘
                                     │
                  ┌──────────────────▼─────────────────────┐
                  │ 2. Capability Matching Pipeline        │
                  │    match(intent, registry)             │
                  └──────────────────┬─────────────────────┘
                                     │
                  ┌──────────────────▼─────────────────────┐
                  │ 3. Invocation Parameter Resolution     │
                  │    resolve_binding(binding, intent)    │
                  └──────────────────┬─────────────────────┘
                                     │
                  ┌──────────────────▼─────────────────────┐
                  │ 4. RFC 8785 JCS Canonicalization       │
                  │    canonicalize(evidence_payload)      │
                  └──────────────────┬─────────────────────┘
                                     │
                  ┌──────────────────▼─────────────────────┐
                  │ 5. Outcome Evidence Verification       │
                  │    verify_evidence(evidence, intent)   │
                  └────────────────────────────────────────┘
```

---

## 4. Step-by-Step Implementation Details

### Step 1: Document Schema Validation
Load and validate documents using a standard Draft 2020-12 JSON Schema validator against the schemas in `spec/schemas/`.

### Step 2: Capability Matching Pipeline
Implement the 8 deterministic evaluation gates defined in [`spec/MATCHING.md`](../spec/MATCHING.md):
1. **Goal Gate:** Exact match of `(vocabulary, term)`.
2. **Inputs Gate:** All mandatory capability inputs must be supplied by Intent.
3. **Outputs Gate:** All required Intent outputs must be declared by Capability.
4. **Constraints Gate:** Generalized constraint algebra ($R \subseteq C$) for Quantity, Range, Set, and Value predicates. Fail closed on unit mismatch.
5. **Spatial Anchor Gate:** Haversine great-circle distance on WGS84 ellipsoid ($R = 6371.0088\text{ km}$). Matches if distance $\le \text{tolerance\_km}$.
6. **State Gate:** Rejects `offline`, `maintenance`, `fault`. Permits `charging` if `accepts_work` is true.
7. **Availability Gate:** Checks `accepts_work: true` and UTC `valid_until` timestamp.
8. **Ranking:** Calculate Score:
   $$\text{Score} = 100.0 - (10.0 \times |\text{unsatisfied}|) + (1000.0 \times \mathbb{I}(\text{preferred})) + (0.1 \times |\text{satisfied}|)$$
   Sort candidates descending by `Score`, tie-breaking lexicographically on `entity_id`.

### Step 3: Invocation Parameter Resolution
Parse dot-paths in `ExecutionBinding.parameters_map` according to the EBNF grammar:
- Resolve `inputs.<name>` via unwrapping precedence (`value` > `ref` > `quantity`).
- Resolve `inputs.<name>.<field>` (e.g. `lat`, `lon`, `alt`, or dictionary key).
- Construct nested native dictionaries matching the dot-separated native parameter key (e.g. `"goal.target.lat"` $\to$ `{"goal": {"target": {"lat": ...}}}`).

### Step 4: RFC 8785 JCS Canonicalization
Implement or link an RFC 8785 JSON Canonicalization Scheme library:
- Object keys sorted lexicographically by UTF-16 code units.
- No whitespace outside strings.
- Floats formatted according to ECMAScript standard (no trailing zeroes).
- Compute SHA-256 digest: `"sha256:" + hex(SHA256(canonical_bytes))`.

### Step 5: Evidence & Attestation Verification
Implement `verify_evidence(evidence, intent, declaration, public_keys)`:
1. **Integrity:** Verify Ed25519 and ECDSA P-256 signatures over the unsigned payload's canonical JCS digest.
2. **Provenance:** Check `intent_id`, `declaration_id`, `entity_id`, and `execution_id`.
3. **Constraint Evaluation:** Evaluate `observed_metrics` against original `Intent.constraints` using the normative constraint algebra.

---

## 5. Conformance Verification

To verify that your independent implementation is 100% conformant with the PCL standard, execute your test suite against the portable JSON test vectors located in:

- [`spec/conformance/matching/matching-vectors.json`](../spec/conformance/matching/matching-vectors.json)
- [`spec/conformance/spatial/spatial-vectors.json`](../spec/conformance/spatial/spatial-vectors.json)
- [`spec/conformance/parameters_map/parameter-map-vectors.json`](../spec/conformance/parameters_map/parameter-map-vectors.json)
- [`spec/conformance/canonicalization/jcs-vectors.json`](../spec/conformance/canonicalization/jcs-vectors.json)
- [`spec/conformance/verification/evidence-verification-vectors.json`](../spec/conformance/verification/evidence-verification-vectors.json)

Your implementation must reproduce the expected outputs, scores, and boolean match decisions byte-for-byte.
