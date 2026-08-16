# PCL V0 Architecture

## Layer Model

```
┌─────────────────────────────────────────────────────────┐
│  Consumer / AI Agent                                     │
│  Intent documents                                        │
└───────────────────────────┬─────────────────────────────┘
                            │ match()
┌───────────────────────────▼─────────────────────────────┐
│  PCL Registry                                            │
│  Entities + Declarations + Offers                        │
└───────────────────────────┬─────────────────────────────┘
                            │ select + invoke
┌───────────────────────────▼─────────────────────────────┐
│  Adapters (V0: interface + stub)                         │
│  ros2 | opcua | wot | http | custom                      │
└───────────────────────────┬─────────────────────────────┘
                            │
                   Native protocols / APIs
```

## Object Relationships

```
Entity
├── declares → CapabilityDeclaration (1:N)
└── publishes → CapabilityOffer (1:N, references declaration)

Intent
└── matched against → CapabilityOffer + CapabilityDeclaration

Evidence
└── references → Intent + CapabilityDeclaration (post-execution)
```

## Declaration vs Offer

| Aspect | CapabilityDeclaration | CapabilityOffer |
|--------|----------------------|-----------------|
| Mutability | Static | Dynamic |
| Contains | IO, constraints, execution | State, availability, location |
| Used for | Contract definition | Runtime matching |

## What PCL Adds vs Existing Standards

| Standard | Provides | PCL Layer |
|----------|----------|-----------|
| WoT TD | Device affordances, bindings | Outcome contracts + intents |
| OPC UA Skills | Machine skills, ontologyURL | Cross-domain intent matching |
| ROS 2 | Actions/services | Capability abstraction above actions |
| IEEE 1872 | Robotics vocabulary | External vocabulary reference |

## Reference Implementation

Python SDK in `sdk/python/pcl/`:

- `models` — typed document objects
- `validate` — JSON Schema validation
- `registry` — local file-backed registry
- `matcher` — deterministic matching pipeline
- `adapters` — execution binding interface
