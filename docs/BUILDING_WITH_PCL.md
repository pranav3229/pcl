# Building with PCL
**A Practical Integration Guide for Physical AI & Robotics Teams**

---

## 1. The Core Value Proposition

> *"My robot already works. Why do I need PCL?"*

If your company builds autonomous mobile robots (AMRs), robotic arms, CNC workcells, or automated drones, you already have:
- A real-time control stack (e.g. ROS 2, Nav2, MoveIt, proprietary C++).
- A fleet manager or dispatch service.
- An internal database of missions.

**The problem arises when an external system needs to use your robot:**
- An AI foundation agent wants to request package transport.
- A smart factory floor manager wants to schedule a machine tending job.
- A multi-vendor warehouse needs heterogeneous robots (from 3 different manufacturers) to coordinate tasks.

Without PCL, every integration requires custom API bridges, proprietary topic translation, manual contract negotiation, and custom verification code.

**With PCL, you keep your entire existing stack and expose a standardized, machine-readable capability contract.**

---

## 2. The 3-Step Integration Pattern

```
┌────────────────────────────────────────────────────────┐
│ 1. ADVERTISE: Expose CapabilityDeclaration             │
│ (Describes physical payload, speed, and boundaries)    │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ 2. MAP: Define ExecutionBinding                        │
│ (Declaratively maps PCL Intent to native ROS 2 Action) │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┘
│ 3. ATTEST: Emit Signed Evidence                        │
│ (Signs completed sensor metrics & delivery photos)     │
└────────────────────────────────────────────────────────┘
```

---

## 3. Step-by-Step Robotics Implementation Example

### Step 1: Advertise Your Robot's Capabilities
Instead of documenting proprietary REST endpoints, publish a `CapabilityDeclaration`:

```json
{
  "pcl_version": "0.1.0",
  "id": "cap-pallet-transport-01",
  "entity_id": "amr-unit-42",
  "semantic_type": {
    "vocabulary": "https://pcl.dev/vocab/logistics/v0",
    "term": "pallet_transport"
  },
  "inputs": [
    { "name": "pallet_id", "role": "object", "value_kind": "entity_ref", "required": true },
    { "name": "destination_bay", "role": "destination", "value_kind": "location_ref", "required": true }
  ],
  "constraints": [
    { "name": "max_weight", "quantity": { "value": 500, "unit": "kg", "comparator": "lte" } },
    { "name": "max_speed", "quantity": { "value": 1.5, "unit": "m/s", "comparator": "lte" } }
  ],
  "execution": {
    "protocol": "ros2",
    "target": "/amr42/navigate_to_pose",
    "operation": "send_goal",
    "parameters_map": {
      "goal.target_frame": "inputs.destination_bay.ref",
      "goal.payload_id": "inputs.pallet_id.ref"
    }
  }
}
```

### Step 2: Handle Native Invocations
When a matched `Intent` arrives, the PCL parameter resolver generates the exact payload your ROS 2 action server expects:

```json
{
  "goal": {
    "target_frame": "bay_east_14",
    "payload_id": "pallet-9912"
  }
}
```
Your existing ROS 2 node receives this standard goal message and executes navigation using your normal Nav2 pipeline.

### Step 3: Emit Verifiable Outcome Evidence
When the mission completes, your onboard controller generates an `Evidence` document:

```json
{
  "pcl_version": "0.1.0",
  "id": "evi-pallet-9912",
  "execution_id": "exec-amr42-1049",
  "intent_id": "intent-pallet-transport-808",
  "declaration_id": "cap-pallet-transport-01",
  "entity_id": "amr-unit-42",
  "timestamp": "2026-08-16T12:00:00Z",
  "outcome": "completed",
  "observed_metrics": {
    "duration_minutes": 6.2,
    "max_weight": 420
  },
  "artifacts": [
    {
      "type": "dropoff_lidar_scan",
      "uri": "https://storage.fleet.internal/scans/1049.pcd",
      "digest": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    }
  ],
  "attestations": [
    {
      "issuer": "amr-unit-42",
      "role": "provider",
      "algorithm": "ed25519",
      "public_key": "e8MHlRjtEdoDNghb9pYpIP+H+zxNYwqbWMthU2dPXdY=",
      "timestamp": "2026-08-16T12:00:05Z",
      "signature": "CN+6h5M383fCwx1d9fVPmur37Ie2+SXWVguq/vYdo+xKOLusmwvMK8SJ01kRIGJZ2d7W6y1e3bipQRYHptOcAg=="
    }
  ]
}
```

---

## 4. Architectural Summary

| Layer | Technology | Responsibility |
| :--- | :--- | :--- |
| **Physical AI / Agent Layer** | LLM / Foundation Model | Formulates goal intent, selects capability, verifies outcome. |
| **PCL Protocol Layer** | `pcl-sdk` | Formal capability contracts, deterministic matching, parameter mapping, evidence verification. |
| **Transport Adapter** | `adapters/ros2.py` | Bridges PCL parameters to native ROS 2 topics and actions. |
| **Robotics Control Layer** | ROS 2 / Nav2 / Micro-ROS | Motor control, obstacle avoidance, sensor acquisition. |
