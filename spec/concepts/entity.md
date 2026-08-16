# Entity

An **Entity** is a physical or physical-world service provider that exposes capabilities.

Examples: humanoid robot, drone, CNC machine, warehouse, charging station, human-operated service.

Entities may compose other entities via `contains`.

## Fields

- `id` — unique identifier
- `name` — human-readable label
- `entity_type` — SemanticRef
- `controller` — who operates/provides the entity (URI or org string)
- `contains` — child entity IDs
- `location` — current location (optional on entity)

Identity is entity-scoped in V0, not per-capability.
