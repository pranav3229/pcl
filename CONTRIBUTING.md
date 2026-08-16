# Contributing to the Physical Capability Language (PCL)

Thank you for your interest in contributing to PCL! PCL is being developed as an open, vendor-neutral protocol standard for Physical AI and robotics capability discovery, invocation, and verification.

---

## 1. The Core Architectural Invariant

> **CRITICAL RULE:** The **normative source of truth** is the combination of:
> 1. The Specification documents ([`spec/SPEC.md`](spec/SPEC.md), [`spec/MATCHING.md`](spec/MATCHING.md))
> 2. The JSON Schemas ([`spec/schemas/`](spec/schemas/))
> 3. The Conformance Test Vectors ([`spec/conformance/`](spec/conformance/))
>
> Changing Python SDK code without updating the normative specification and conformance vectors is **NOT** an acceptable protocol change.

---

## 2. Where Changes Belong

| Area | Directory | Contribution Rules |
| :--- | :--- | :--- |
| **Protocol Specification** | `spec/` | Modifying core semantics, schemas, or wire representations requires an approved RFC/issue discussion. Changes MUST maintain language-agnosticism. |
| **Conformance Vectors** | `spec/conformance/` | Any new normative behavior MUST include portable JSON test vectors for cross-language validation. |
| **Reference SDK** | `sdk/python/` | Reference implementation of the standard. Must conform 100% to `spec/conformance/`. |
| **Protocol Adapters** | `adapters/` | Transport plugins (ROS 2, HTTP, OPC-UA). Must remain strictly external to PCL core. |
| **Documentation** | `docs/` | Guides, tutorials, and architectural explanations. |

---

## 3. Development Setup & Testing

### Installation
```bash
git clone https://github.com/pcl-standard/pcl.git
cd pcl/sdk/python
pip install -e ".[dev]"
```

### Running the Test Suite
```bash
# Run all unit, adversarial, conformance, and example tests
pytest ../../tests -v
```

All contributions must pass 100% of existing tests with zero regressions.

---

## 4. How to Propose Changes

1. **Specification Ambiguities or Bugs:** Open an issue categorized as a *Specification Ambiguity* before submitting code.
2. **New Capabilities / Constraints:** Use the generalized constraint algebra (`Quantity`, `Range`, `Set`, `Value`) before proposing new schema primitives.
3. **Protocol Adapters:** When contributing adapters for new transports (e.g. MQTT, DDS), implement them within `adapters/` without adding runtime dependencies to `sdk/python/`.

---

## 5. Anti-Overengineering Checklist

Before proposing a new primitive or feature, verify:
- [ ] Can this be expressed using existing `Intent`, `CapabilityDeclaration`, or `ConstraintSpec` models?
- [ ] Does this belong in an application/ecosystem layer (e.g. workflow engine, payment gateway) rather than the core capability protocol?
- [ ] Does this introduce vendor lock-in or assume a specific robotics framework?
