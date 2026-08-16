# PCL V0 Specification

**Version:** 0.1.0
**Status:** Draft

## 1. Purpose

PCL defines a minimal machine-readable representation for:

1. Physical entities (providers)
2. Physical capabilities (outcome-oriented contracts)
3. Intents (consumer demand)
4. Inputs, outputs, constraints
5. Runtime state and availability
6. Location
7. Execution bindings (references to native protocols)
8. Evidence envelopes (post-execution, stub in V0)

PCL does **not** define domain vocabularies, motion primitives, payment, or communication protocols.

## 2. Design Principles

1. **Meta-model, not ontology** — Domain meaning lives in external vocabularies via `SemanticRef`.
2. **Capability ≠ Execution** — A capability describes an outcome; execution binding points to ROS/OPC UA/WoT/etc.
3. **Declaration ≠ Runtime** — Static capability declarations are separate from runtime offers.
4. **Fail-closed matching** — If an intent constraint has no corresponding capability constraint, the capability is rejected.
5. **Minimal and composable** — Extension via `extensions` bag; unknown keys ignored.

## 3. Document Types

### 3.1 Entity

A physical or physical-world service provider.

```json
{
  "pcl_version": "0.1.0",
  "id": "robot-17",
  "name": "Warehouse Robot 17",
  "entity_type": { "term": "mobile_robot", "vocabulary": "https://pcl.dev/vocab/core/v0" },
  "controller": "org:acme-robotics",
  "contains": ["gripper-17"],
  "location": { "kind": "semantic", "ref": "warehouse-floor-2" }
}
```

### 3.2 CapabilityDeclaration

Static description of what a provider can do.

Required fields: `pcl_version`, `id`, `entity_id`, `semantic_type`, `inputs`, `execution`.

### 3.3 CapabilityOffer

Runtime snapshot for matching.

Required fields: `declaration_id`, `entity_id`, `state`, `availability`.

### 3.4 Intent

Consumer request for an outcome.

Required fields: `pcl_version`, `id`, `goal`, `inputs`.

### 3.5 Evidence (V0 stub)

Post-execution proof artifact. Not used in matching.

## 4. Semantic References & Vocabularies

Capabilities and intents reference external domain vocabularies to establish semantic meaning:

```json
{
  "vocabulary": "https://pcl.dev/vocab/logistics/v0",
  "term": "package_transport",
  "label": "Package Transport"
}
```

- **Exact Matching Guarantee:** In PCL V0, semantic matching requires exact string equality of `term` and (if specified) `vocabulary`.
- **Vocabulary Resolution Boundary:** PCL core **does not resolve or dereference vocabulary URIs at runtime**. Vocabulary governance, synonym aliasing, and ontology reasoning belong to external registries and tooling.

## 5. Inputs and Outputs

Both capabilities and intents express interface contracts using `IOContract`:

| Field | Type | Description |
|-------|------|-------------|
| `name` | `string` | Parameter key used in intent input maps and parameter bindings |
| `role` | `string` | Functional role: `object`, `origin`, `destination`, `parameter`, `artifact`, `report` |
| `value_kind` | `string` | Data type: `entity_ref`, `location_ref`, `quantity`, `file_ref`, `string`, `structured` |
| `required` | `boolean` | Mandatory requirement (default: `true`) |

### 5.1 Intent Value Representation & Unwrapping Precedence
An intent input parameter is provided as an `IntentInputValue` envelope:
```json
{
  "ref": "pkg-4412",
  "value": { "lat": 12.9716, "lon": 77.5946 },
  "quantity": { "value": 10, "unit": "kg" }
}
```

When evaluated or resolved into execution bindings, conformant implementations MUST apply the following unwrapping precedence:
1. **`value`**: If non-null, unwrapped as the primary payload value.
2. **`ref`**: If non-null, unwrapped as the string identifier/URI reference.
3. **`quantity`**: If non-null, unwrapped as the Quantity object/value.

## 6. Constraints

PCL supports five generic constraint predicate forms across capabilities and intents:

1. **Scalar / Quantity:**
   ```json
   { "name": "max_payload", "quantity": { "value": 25, "unit": "kg", "comparator": "lte" } }
   ```
   - **Default Comparator:** When `comparator` is omitted, conformant implementations MUST default to `"lte"` (less-than-or-equal).
   - **Supported Comparators:** `"lte"`, `"gte"`, `"eq"`, `"lt"`, `"gt"`.
   - **Unit Mismatch:** Mismatched units without a known conversion factor fail closed with diagnostic rejection.
2. **Interval / Range:**
   ```json
   { "name": "operating_temp", "range": { "min": 0, "max": 50, "unit": "degC" } }
   ```
3. **Categorical / Literal Value:**
   ```json
   { "name": "connector_type", "value": "CCS2" }
   ```
4. **Set Membership:**
   ```json
   { "name": "supported_materials", "in": ["Al-6061", "Steel-4140"] }
   ```
5. **Boolean Flag:**
   ```json
   { "name": "licensed_electrician", "value": true }
   ```

Intent constraints are satisfied when the provider capability envelope accommodates the intent requirements. See [MATCHING.md](MATCHING.md).

## 7. State and Availability

PCL strictly decouples the physical condition of the hardware from the dispatcher's operational policy:

- **RuntimeState** — Physical hardware operating condition:
  `idle`, `busy`, `charging`, `offline`, `maintenance`, `fault`, `active`.
- **Availability** — Dispatcher readiness and temporal validity:
  - `accepts_work` (`boolean`): Whether work is currently accepted.
  - `valid_until` (`ISO 8601 string`, optional): Offer expiration timestamp / TTL.
  - `reason` (`string`, optional): Human/diagnostic explanation of status.
  - `schedule` (`list[string]`, optional): ISO 8601 time windows.

An entity may be `state.status: "charging"` while `availability.accepts_work: true` (e.g. background processing or scheduled job queue). Conversely, an entity may be `state.status: "idle"` while `availability.accepts_work: false` (e.g. reserved or maintenance lockout).

## 8. Location & Spatial Semantics

`Location` acts strictly as a **Spatial Anchor** (a point or reference frame identifier), NOT a GIS geometry or trajectory engine:

```json
{ "kind": "semantic", "ref": "warehouse-floor-2" }
{ "kind": "coordinates", "lat": 12.9716, "lon": 77.5946, "alt": 920.0 }
{ "kind": "uri", "ref": "https://building.example/floor/2" }
```

### 8.1 Coordinate Reference System (CRS)
- **Datum:** WGS84 ellipsoid (EPSG:4326).
- **Latitude (`lat`):** Decimal degrees in the range $[-90.0, 90.0]$. North is positive, South is negative.
- **Longitude (`lon`):** Decimal degrees in the range $[-180.0, 180.0]$. East is positive, West is negative.
- **Altitude (`alt`):** Optional floating-point number representing meters above mean sea level (or subsea depth if negative).

### 8.2 Haversine Great-Circle Distance
Conformant implementations MUST compute coordinate distance using the spherical Haversine formula with the standard volumetric Earth mean radius $R = 6371.0088\text{ km}$:

$$\Delta\phi = \text{radians}(\text{lat}_2 - \text{lat}_1), \quad \Delta\lambda = \text{radians}(\text{lon}_2 - \text{lon}_1)$$
$$a = \sin^2\left(\frac{\Delta\phi}{2}\right) + \cos(\text{radians}(\text{lat}_1))\cos(\text{radians}(\text{lat}_2))\sin^2\left(\frac{\Delta\lambda}{2}\right)$$
$$d = 2 R \arcsin(\sqrt{a})$$

Two coordinate anchors match if $d \le \text{tolerance\_km}$.

## 9. Execution Binding & Parameter Resolution

`ExecutionBinding` defines the protocol-agnostic invocation contract for invoking a physical capability through an external execution system:

```json
{
  "protocol": "ros2",
  "target": "/amr_fleet/transport_package",
  "operation": "send_goal",
  "parameters_map": {
    "goal.item_id": "inputs.object.ref",
    "goal.source_frame": "inputs.origin.ref",
    "goal.target_frame": "inputs.destination.ref"
  },
  "metadata": {
    "action_type": "nav2_msgs/action/NavigateToPose",
    "qos_depth": 10
  }
}
```

### 9.1 Parameter Mapping Grammar
Conformant implementations MUST evaluate source paths in `parameters_map` using the following language-agnostic grammar:

```ebnf
SourcePath       ::= Root '.' Identifier ('.' SubField)*
Root             ::= 'inputs' | 'constraints'
Identifier       ::= [a-zA-Z0-9_-]+
SubField         ::= [a-zA-Z0-9_-]+
NativeParamKey   ::= Identifier ('.' Identifier)*
```

### 9.2 Traversal & Resolution Semantics
- **Mapping Direction:** `native_payload_path -> PCL_source_path`.
- **`inputs.<name>`**: Resolves to the unwrapped value of `Intent.inputs[name]`.
- **`inputs.<name>.<field>`**: Accesses specific properties (`ref`, `lat`, `lon`, `alt`, or dictionary keys).
- **`constraints.<name>.value`**: Resolves to the boundary value of `Intent.constraints[name]`.
- **Nested Object Construction:** Dot-separated segments in `NativeParamKey` (e.g. `"goal.target.lat"`) construct nested native dictionaries.
- **Fail-Closed Execution:** Unresolvable or malformed paths MUST raise an error and fail closed.

### 9.3 Adapter Boundary
PCL describes invocation contracts declaratively. PCL core **does not execute native protocols** (no built-in ROS 2 nodes, HTTP clients, or OPC-UA drivers). Native execution is performed by external protocol adapters.

## 10. Composition (composed_of)

A capability declaration may declare sub-capability dependencies via `composed_of`:

```json
{
  "composed_of": ["cap-cnc-machining", "cap-quality-inspection", "cap-transport-robot17"]
}
```

- **Declarative Lineage:** Lists atomic sub-capabilities that form the composite capability.
- **Authoritative External Contract:** The composite declaration's own inputs, outputs, and constraints define the authoritative external contract for matching.
- **Non-Execution Invariant:** PCL does not execute sub-steps, plan DAG workflows, or manage intermediate rollback states.

## 11. Extensions

```json
"extensions": { "vendor": { "fleet_id": "east-warehouse" } }
```

Unknown extension keys must be ignored by conformant implementations.

## 12. Outcome Evidence & Verification

`Evidence` is a normative post-execution record asserting observed outputs, physical measurements, and artifact digests produced by a capability execution instance.

### 12.1 Evidence Schema

```json
{
  "pcl_version": "0.1.0",
  "id": "evi-9081",
  "execution_id": "exec-7701",
  "intent_id": "intent-transport-01",
  "declaration_id": "cap-transport-robot17",
  "entity_id": "robot-17",
  "timestamp": "2026-08-16T12:00:00Z",
  "outcome": "completed",
  "summary": "Package delivered to destination zone B",
  "observed_outputs": {
    "delivered_object": { "ref": "package-123" }
  },
  "observed_metrics": {
    "transit_duration_minutes": 14,
    "distance_km": 1.2
  },
  "artifacts": [
    {
      "type": "delivery_photo",
      "uri": "https://storage.pcl.dev/blobs/p123.jpg",
      "digest": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    }
  ],
  "attestations": [
    {
      "issuer": "robot-17",
      "role": "provider",
      "algorithm": "ed25519",
      "public_key_ref": "https://registry.pcl.dev/keys/robot-17.pub",
      "timestamp": "2026-08-16T12:00:05Z",
      "signature": "base64:..."
    }
  ]
}
```

### 12.2 Canonicalization & Hashing Rules
- **Canonicalization Standard:** RFC 8785 JSON Canonicalization Scheme (JCS).
- **Signing Material:** The unsigned evidence payload (`Evidence` document excluding the `attestations` list).
- **Digest Computation:** `sha256_digest = "sha256:" + SHA256(JCS(unsigned_payload))`.
- **Supported Cryptographic Algorithms:** `ed25519`, `ecdsa-p256-sha256`.

### 12.3 Cryptographic Integrity vs. Physical Truth
A valid cryptographic attestation guarantees *authenticity* (the holder of the private key signed the payload) and *integrity* (the payload was not altered). It does **not** guarantee that physical sensors or providers cannot report false data. Trust models (self, consumer, third-party inspector) are represented via `Attestation.role`.

### 12.4 Verification Pipeline
Deterministic evidence verification (`verify_evidence`) executes a four-tier evaluation:
1. **Schema Validation:** Draft 2020-12 compliance.
2. **Cryptographic Integrity:** Validates signatures over the RFC 8785 JCS canonical digest.
3. **Provenance Validation:** Verifies linkage of `intent_id`, `declaration_id`, `entity_id`, and `execution_id`.
4. **Constraint Satisfaction:** Evaluates observed metrics against the consumer's `Intent.constraints` using the Phase 1 generalized constraint algebra.

## 13. Non-Goals (V0)

- Workflow / DAG execution engines, behavior trees, task graphs
- Native protocol runtime execution drivers (no rclpy, httpx, asyncua in core)
- Payment, marketplace, reputation, escrow, blockchain/token economics
- Global registry federation
- Real-time 100 Hz telemetry streaming ingestion
- Distributed locking and two-phase commit reservation transactions
- Semantic/AI reasoning engines
- Court arbitration / legal dispute resolution

## 14. Versioning

Every document includes `pcl_version`. Breaking changes increment minor/major per project policy.
