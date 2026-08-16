# PCL V0 Matching Algorithm

Matching is **deterministic and explainable**. No semantic reasoning in V0.

## Pipeline

```
Intent
  → Goal type filter
  → Input compatibility
  → Output compatibility (if intent specifies required_outputs)
  → Constraint satisfaction (fail-closed)
  → Spatial anchor gating (semantic equality / Haversine proximity)
  → State gate
  → Availability & TTL gate (valid_until)
  → Rank survivors
  → MatchResult[]
```

## 1. Goal Type Filter

Match when `intent.goal.vocabulary == declaration.semantic_type.vocabulary`
and `intent.goal.term == declaration.semantic_type.term`.

Optional alias table (same vocabulary only) may map equivalent terms.

## 2. Input Compatibility

For each `IOContract` in declaration where `required: true`:

- Intent must provide key matching `name`
- Intent value must be present (non-null)

If declaration input is optional, intent need not provide it.

## 3. Output Compatibility

If intent specifies `required_outputs`, each named output must exist in declaration with compatible `value_kind`.

## 4. Constraint Satisfaction (Fail-Closed)

For each constraint in `intent.constraints`:

1. Find declaration constraint with same `name`
2. If **not found** → **reject** (capability limits unknown, fail-closed)
3. If found, evaluate per rules below

### 4.1 Quantity Constraints
- **Unit rule:** Units must match exactly in V0.
- `lte` (upper bound / capacity): capability limit $\ge$ intent value.
- `gte` (precision / tolerance): capability minimum $\le$ intent value; (capacity threshold): capability maximum $\ge$ intent value.
- `eq` (exact scalar): capability value $==$ intent value (or contained in capability range).

### 4.2 Range / Interval Constraints
- Intent range $[I_{min}, I_{max}]$ against capability range $[C_{min}, C_{max}]$:
  Satisfied iff $C_{min} \le I_{min}$ and $I_{max} \le C_{max}$ (provider range fully covers requested range).
- Intent scalar against capability range:
  Satisfied iff $C_{min} \le I_{val} \le C_{max}$.

### 4.3 Set Membership Constraints
- Intent single value against capability set `in: [C1, C2, ...]`:
  Satisfied iff $I_{val} \in C_{set}$.
- Intent acceptable set `in: [I1, I2, ...]` against capability set `in: [C1, C2, ...]`:
  Satisfied iff $I_{set} \cap C_{set} \neq \emptyset$.

### 4.4 Categorical & Boolean Constraints
- Intent value against capability value:
  Satisfied iff $I_{val} == C_{val}$.
- Boolean values must match directly (`true == true`, `false == false`).

## 5. Spatial Anchor Gating

Evaluated when the Offer declares a `location` anchor and the Intent specifies an origin or location requirement:

1. **Semantic Anchor:** Matched iff $\text{Offer.location.ref} == \text{Intent.origin.ref}$.
2. **Coordinate Proximity:** Matched iff Haversine distance between Offer and Intent origin $\le \text{tolerance}$.
   - Tolerance is extracted from `intent.constraints.location_tolerance` or `max_distance` (default: 0.0 km).
3. **Mismatched Kinds:** Mismatches between semantic and coordinate kinds fail closed.
4. **No Spatial Requirement in Intent:** If Intent does not specify an origin/location requirement, spatial anchor gating passes unconditionally.

## 6. State Gate

Reject if `offer.state.status` is in blocklist: `offline`, `maintenance`, `fault`.
- `charging` is NOT blocked by default, as an entity may accept work while charging.

## 7. Availability & TTL Gate

1. **Policy Acceptance:** Reject if `offer.availability.accepts_work == false`.
2. **Temporal TTL:** If `offer.availability.valid_until` is present, reject if $\text{evaluation\_time} > \text{valid\_until}$.
   - Evaluated using UTC-aware ISO 8601 timestamps.
   - `evaluation_time` defaults to current UTC time, or a deterministic override timestamp in tests.

## 8. Ranking

Candidates that pass all mandatory matching gates are scored and ordered deterministically:

### 8.1 Score Formula
$$\text{Score} = 100.0 - (10.0 \times |\text{unsatisfied}|) + (1000.0 \times \mathbb{I}(\text{entity\_id} == \text{intent.preferences.provider\_id})) + (0.1 \times |\text{satisfied}|)$$

- **Base Score:** `100.0`.
- **Unsatisfied Penalty:** `-10.0` per unsatisfied optional gate/constraint.
- **Provider Preference Bonus:** `+1000.0` if `intent.preferences.provider_id` matches `offer.entity_id`.
- **Satisfied Gate Bonus:** `+0.1` per satisfied gate in `["goal", "inputs", "outputs", "constraints", "location", "state", "availability"]`.

### 8.2 Candidate Ordering & Tie-Breaking
Matched candidates are sorted deterministically using the following lexicographical tuple:
$$\text{SortKey}(R) = (-\text{Score}, \text{entity\_id}, \text{declaration\_id})$$

1. **Primary Sort:** Descending by numerical `Score`.
2. **Secondary Tie-Break:** Ascending lexicographical ASCII/UTF-8 order of `entity_id`.
3. **Tertiary Tie-Break:** Ascending lexicographical ASCII/UTF-8 order of `declaration_id`.

## 9. Structured Diagnostics

Matching produces machine-readable `ConstraintDiagnostic` records for constraint evaluations and gating rejections:

```json
{
  "constraint": "location",
  "result": "rejected",
  "reason": "offer is 4.2 km from requested origin; tolerance is 1.0 km"
}
```

```json
{
  "constraint": "availability.valid_until",
  "result": "rejected",
  "reason": "offer expired at 2026-08-16T18:00:00Z"
}
```

## MatchResult

```json
{
  "declaration_id": "cap-transport-robot17",
  "entity_id": "robot-17",
  "offer_id": "offer-robot17-transport",
  "score": 100.6,
  "satisfied": ["goal", "inputs", "constraints", "location", "state", "availability"],
  "unsatisfied": [],
  "diagnostics": [...]
}
```

## 10. Composition and Invocation Boundary

- **Composite Capabilities:** When matching against a composite capability (`composed_of`), the matcher evaluates the composite declaration's own authoritative outer contract (`inputs`, `outputs`, `constraints`).
- **No Workflow Execution in Matcher:** The matcher does not traverse sub-capabilities, resolve workflow DAGs, or manage intermediate execution states.
- **Invocation Execution:** `ExecutionBinding` is resolved by external protocol adapters post-matching to dispatch native protocol payloads.

## 11. Pre-Execution Matching vs. Post-Execution Evidence Boundary

- **Pre-Execution Matching:** Capability matching evaluates advertised affordances, operational states, and availability constraints before execution begins.
- **Post-Execution Evidence Verification:** Evidence verification evaluates cryptographically attested outcome artifacts, observed outputs, and physical measurements produced after execution completes.
- **Strict Separation:** The capability matcher does not process or evaluate `Evidence` documents.
