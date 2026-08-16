# PCL Developer Quickstart
**Get up and running with the Physical Capability Language in 10 minutes**

---

## What You Will Build & Run

In this quickstart, you will:
1. **Declare a Physical Capability** for an Autonomous Mobile Robot (AMR) in a warehouse.
2. **Express Consumer Intent** requesting a package transport task.
3. **Execute Capability Matching** to deterministically pair demand with the best robot.
4. **Resolve Invocation Parameters** into a native ROS 2 action goal.
5. **Generate & Sign Evidence** representing completed physical execution.
6. **Cryptographically Verify** the resulting outcome, provenance, and constraint satisfaction.

---

## 1. Installation

Clone the repository and install the Python reference SDK in development mode:

```bash
git clone https://github.com/pcl-standard/pcl.git
cd pcl/sdk/python
pip install -e .
```

Verify that the CLI is accessible:

```bash
python -m pcl.cli --help
```

---

## 2. Step 1: Declare a Physical Capability

A **Capability Declaration** defines *what* a physical entity can do, its input/output interface, physical boundary constraints, and how native systems invoke it.

Save this declaration as `cap-transport.json`:

```json
{
  "pcl_version": "0.1.0",
  "id": "cap-transport-robot17",
  "entity_id": "robot-17",
  "semantic_type": {
    "vocabulary": "https://pcl.dev/vocab/logistics/v0",
    "term": "package_transport",
    "label": "Package Transport"
  },
  "summary": "Autonomous pallet and package transport within warehouse floor 2",
  "inputs": [
    { "name": "object", "role": "object", "value_kind": "entity_ref", "required": true },
    { "name": "origin", "role": "origin", "value_kind": "location_ref", "required": true },
    { "name": "destination", "role": "destination", "value_kind": "location_ref", "required": true }
  ],
  "outputs": [
    { "name": "delivered_object", "role": "object", "value_kind": "entity_ref" }
  ],
  "constraints": [
    { "name": "max_payload", "quantity": { "value": 25, "unit": "kg", "comparator": "lte" } },
    { "name": "deadline", "quantity": { "value": 30, "unit": "min", "comparator": "lte" } },
    { "name": "budget", "quantity": { "value": 100, "unit": "INR", "comparator": "lte" } }
  ],
  "execution": {
    "protocol": "ros2",
    "target": "/robot17",
    "operation": "transport_package",
    "parameters_map": {
      "object": "inputs.object",
      "from": "inputs.origin",
      "to": "inputs.destination"
    }
  }
}
```

---

## 3. Step 2: Express Consumer Intent

An **Intent** expresses *what outcome is needed*, without knowing which robot will perform it.

Save this intent as `intent-transport.json`:

```json
{
  "pcl_version": "0.1.0",
  "id": "intent-package-transport-001",
  "goal": {
    "vocabulary": "https://pcl.dev/vocab/logistics/v0",
    "term": "package_transport",
    "label": "Package Transport"
  },
  "inputs": {
    "object": { "ref": "package-123" },
    "origin": { "ref": "warehouse-floor-2" },
    "destination": { "ref": "zone-B" }
  },
  "constraints": {
    "max_payload": { "value": 10, "unit": "kg", "comparator": "lte" },
    "deadline": { "value": 10, "unit": "min", "comparator": "lte" },
    "budget": { "value": 50, "unit": "INR", "comparator": "lte" }
  }
}
```

> **Key Distinction:**
> - **Capability:** *"I can carry up to 25 kg in under 30 min."*
> - **Intent:** *"I have a 10 kg package and need it moved in under 10 min."*

---

## 4. Step 3: Match Demand to Capability

Run the deterministic capability matcher against the local registry:

```bash
python sdk/python/pcl/cli.py match spec/examples/intent-package-transport.json
```

### Output:
```
score=100.6 entity=robot-17 declaration=cap-transport-robot17 satisfied=['goal', 'inputs', 'constraints', 'location', 'state', 'availability']
```

### What Happened During Matching?
1. **Goal Gate:** Evaluated exact match on `(vocabulary, term)`.
2. **Inputs Gate:** Confirmed that `object`, `origin`, and `destination` are provided.
3. **Constraints Gate:** Evaluated payload ($10\text{ kg} \le 25\text{ kg}$), deadline ($10\text{ min} \le 30\text{ min}$), and budget ($50\text{ INR} \le 100\text{ INR}$).
4. **Operational & State Gates:** Confirmed `robot-17` is `idle` and `accepts_work: true`.
5. **Ranking:** Computed base score $100.0 + (6 \times 0.1) = 100.6$.

---

## 5. Step 4: Resolve Invocation Parameters

Once a capability matches, resolve the invocation parameters to construct the native execution payload:

```bash
python sdk/python/pcl/cli.py resolve-binding \
  --declaration registry/declarations/cap-transport-robot17.json \
  --intent spec/examples/intent-package-transport.json
```

### Resulting Native Payload:
```json
{
  "object": "package-123",
  "from": "warehouse-floor-2",
  "to": "zone-B"
}
```

---

## 6. The External Execution Boundary

PCL core **does not execute native protocols** (it does not spawn ROS nodes or make HTTP calls). Instead, an external protocol adapter consumes the resolved payload and dispatches it to the physical system:

```
┌────────────────────────────────────────────────────────┐
│ PCL Matcher & Parameter Resolver                       │
│ (Produces declarative native payload)                  │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ External Protocol Adapter (e.g. adapters/ros2.py)       │
│ (Translates payload to ROS 2 Action Goal / HTTP POST)  │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ Physical Robot Hardware / ROS 2 Navigation Stack       │
│ (Executes physical motion in the real world)           │
└────────────────────────────────────────────────────────┘
```

---

## 7. Step 5: Post-Execution Evidence & Attestation

When execution finishes, the robot emits an **Evidence** document recording observed outputs, measured metrics, and cryptographic attestations.

Save as `evidence-transport.json`:

```json
{
  "pcl_version": "0.1.0",
  "id": "evi-transport-robot17-001",
  "execution_id": "exec-7701-a1",
  "intent_id": "intent-package-transport-001",
  "declaration_id": "cap-transport-robot17",
  "entity_id": "robot-17",
  "timestamp": "2026-08-16T12:00:00Z",
  "outcome": "completed",
  "summary": "Package delivered to warehouse zone B dropoff bay",
  "observed_outputs": {
    "delivered_object": { "ref": "package-123" }
  },
  "observed_metrics": {
    "max_payload": 10,
    "deadline": 8,
    "budget": 45
  },
  "artifacts": [
    {
      "type": "dropoff_photo",
      "uri": "https://storage.pcl.dev/blobs/robot17-dropoff-123.jpg",
      "digest": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "description": "Optical confirmation of package dropoff"
    }
  ],
  "attestations": [
    {
      "issuer": "robot-17",
      "role": "provider",
      "algorithm": "ed25519",
      "public_key": "Ot2yxtcRvibMwLOoW0NKKtaHv1XdZE5VpfeVCFo5+2g=",
      "timestamp": "2026-08-16T12:00:05Z",
      "signature": "VlK9F...=="
    }
  ]
}
```

---

## 8. Step 6: Verify Outcome Evidence

Run the verifier to validate cryptographic signatures, provenance linkage, and constraint satisfaction:

```bash
python sdk/python/pcl/cli.py verify spec/examples/evidence-package-transport.json \
  --intent spec/examples/intent-package-transport.json \
  --declaration registry/declarations/cap-transport-robot17.json
```

### Output:
```
VERIFIED: integrity=verified provenance=verified constraints=satisfied
```

---

## 9. Complete Lifecycle Summary

```
   Physical Entity / Robot
             │
             ▼
   [CapabilityDeclaration] ──┐
             │               │
   [CapabilityOffer]         │
             │               ▼
             ├────────► [Capability Matching] ◄──────── [Intent] (Consumer Demand)
             │                 │
             │                 ▼
             │          [MatchResult]
             │                 │
             │                 ▼
             └────────► [ExecutionBinding Parameter Resolution]
                               │
                               ▼
                        [Native Payload]
                               │
                               ▼ (External Protocol Adapter)
                        [Physical Execution]
                               │
                               ▼
                        [Outcome Evidence]
                               │
                               ▼ (RFC 8785 JCS + Ed25519)
                        [Cryptographic Attestation]
                               │
                               ▼
                        [Deterministic Verification]
```

---

## 10. Next Steps

- Explore the complete meta-model in [Architecture Overview](ARCHITECTURE.md).
- Learn how to implement PCL in Rust, Go, or TypeScript in [Clean-Room Implementation Guide](CLEAN_ROOM_IMPLEMENTATION.md).
- Read the normative specifications in [spec/SPEC.md](../spec/SPEC.md) and [spec/MATCHING.md](../spec/MATCHING.md).
