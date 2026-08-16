# Why PCL?
**The Missing Abstraction Between AI Agents and the Physical World**

---

## 1. The Core Problem

Software has spent decades standardizing how digital systems communicate. We have **OpenAPI** for web services, **POSIX** for operating systems, **SQL** for relational databases, and **MCP (Model Context Protocol)** for connecting Large Language Models to digital software tools.

**When an AI agent needs to act in the physical world, this abstraction layer disappears.**

Consider an AI agent in a logistics facility given a simple goal:
> *"Move this 10 kg package from storage bay 3 to loading dock A within 20 minutes."*

In the digital world, an agent queries an API catalog, reads a JSON Schema, sends a request, and parses the response. 

In the physical world, the situation is fragmented:
* There may be **20 heterogeneous machines** nearby: Autonomous Mobile Robots (AMRs), robotic arms, conveyors, autonomous forklifts, and human operators.
* Each entity has **different physical envelopes**: payload capacities ($5\text{ kg}$ vs $500\text{ kg}$), speed profiles, reach limits, and power requirements.
* Each entity has **different real-time operational states**: battery levels, charging status, fault codes, or maintenance schedules.
* Each entity is located at **different spatial coordinates**: a robot 2 miles away cannot satisfy an urgent 10-minute task.
* Each entity speaks **different native control languages**: one uses ROS 2 action servers, another exposes an HTTP REST endpoint, an industrial machine speaks OPC-UA or Modbus, and a human operator has no digital API at all.

---

## 2. Why Existing Technologies Don't Solve This Alone

Engineers frequently ask why existing standards aren't sufficient. The answer is that existing standards operate at different layers of the stack:

```
┌────────────────────────────────────────────────────────────────────────┐
│ AGENT / PLANNER LAYER (AI Foundation Models, Workflow Orchestrators)   │
├────────────────────────────────────────────────────────────────────────┤
│ PCL CAPABILITY LAYER (Physical Capability Language)                    │
│ • Affordance Declarations  • Spatial Gating  • Deterministic Matching  │
│ • Parameter Resolution     • JCS Crypto      • Evidence Verification   │
├────────────────────────────────────────────────────────────────────────┤
│ NATIVE EXECUTION & TRANSPORT (HTTP REST, ROS 2, OPC-UA, MQTT, VDA 5050)│
├────────────────────────────────────────────────────────────────────────┤
│ PHYSICAL HARDWARE & SENSORS (Motors, Actuators, Cameras, Lidars)      │
└────────────────────────────────────────────────────────────────────────┘
```

### ROS 2 is Middleware, Not a Capability Discovery Protocol
**ROS 2** is the premier framework for robotics control, kinematics, trajectory generation, and sensor pipelines. However:
* ROS 2 does not specify a machine-readable capability contract for external agents.
* An external AI agent cannot query a generic ROS 2 network and automatically deduce that `/amr42/navigate_to_pose` represents a package transport affordance with a $25\text{ kg}$ payload limit without custom point-to-point integration code.
* PCL operates *above* ROS 2, mapping abstract consumer intent into exact ROS 2 action goal parameters.

### MCP is for Digital Tools, Not Physical Affordances
Anthropic's **Model Context Protocol (MCP)** connects LLMs to digital software tools (SQL databases, GitHub repositories, web browsers). When applied to physical hardware, MCP breaks down because:
1. **No Physical Constraint Algebra:** MCP tools are generic function signatures. They cannot express or evaluate physical envelopes (e.g. $10\text{ kg} \le 25\text{ kg}$, $2^\circ\text{C} \le \text{temp} \le 8^\circ\text{C}$).
2. **No Geodesic Spatial Grounding:** Digital tools have no physical location. PCL natively integrates WGS84 geodesic coordinates and Haversine distance proximity gating.
3. **No Operational State or Ephemeral Leases:** Digital tools are either online or offline. Physical robots have complex state machines (`idle`, `charging`, `fault`) and expiring availability leases (`valid_until` TTLs).
4. **No Cryptographic Outcome Verification:** In software, a 200 OK implies execution success. In the physical world, tasks involve physical liability, sensor logs, and tamper-proof verification.

### Protocol Comparison Matrix

| Technology | Primary Focus | Layer | Relationship to PCL |
| :--- | :--- | :--- | :--- |
| **OpenAPI / REST** | Web service endpoints | Transport | Target execution binding for web-connected machines |
| **MCP (Anthropic)** | LLM ↔ Digital Software Tools | Agent/Tool | Complementary tool standard for pure software tasks |
| **ROS 2 & Nav2** | Real-time robot control & kinematics | Robotics Runtime | Underlying execution system for mobile robots and arms |
| **OPC-UA / MQTT** | Industrial machine telemetry & SCADA | Industrial Bus | Target execution transport for manufacturing equipment |
| **VDA 5050** | AGV/AMR fleet task dispatch | Fleet Dispatch | Lower-level transport protocol for industrial mobile robots |
| **PCL** | **Physical capability semantics, matching & evidence** | **Protocol Layer** | **Universal capability contract & cryptographic verification** |

---

## 3. The Core Insight: Standardize the Capability, Not the Machine

Rather than trying to force every robot, machine, and human in the world to run the same operating system or speak the same transport protocol, PCL standardizes **how capabilities and intents are described and evaluated**:

```
Who or what provides the capability?                      → Entity
What can it do (envelopes, physical limits, I/O)?         → CapabilityDeclaration
What does someone want done (goal, inputs, deadlines)?    → Intent
Can that capability deterministically satisfy the intent? → 8-Gate Matcher
How is the request translated into the native interface?  → ExecutionBinding
What actually happened in the physical world?             → Evidence (Attestation)
```

---

## 4. Key Architectural Pillars

### 1. Deterministic & Fail-Closed Matching
Physical execution involves safety risks, material costs, and physical constraints. PCL rejects non-deterministic LLM hallucination at the matching layer. The 8-gate matching pipeline mathematically verifies goal semantics, required inputs, output contracts, constraint inequalities, spatial proximity, and hardware state machines.

### 2. Transport Independence
PCL is not "an HTTP protocol" or "a ROS protocol." It defines a declarative parameter mapping grammar (EBNF dot-paths) that translates abstract intent fields into native payload structures for HTTP, ROS 2, OPC-UA, or W3C Web of Things endpoints.

### 3. Cryptographic Verification & The Physical Oracle
PCL does not naively claim to "solve" the physical oracle problem (a broken sensor could always report false telemetry). Instead, it provides a rigorous cryptographic audit trail:
* The executing entity emits an **Evidence** manifest recording observed metrics and content-addressed sensor digests (e.g. photos, LiDAR point clouds).
* The payload is canonicalized via **RFC 8785 JSON Canonicalization Scheme (JCS)** and digitally signed using **Ed25519** or **ECDSA P-256**.
* The verifier mathematically confirms signature authenticity, provenance linkage, and verifies that the reported metrics satisfied the original contract.

---

## 5. Summary

PCL provides the missing language that allows Physical AI agents and heterogeneous physical machines to discover, negotiate, execute, and verify physical work without requiring proprietary point-to-point integration code for every device.
