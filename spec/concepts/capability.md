# Capability

A **CapabilityDeclaration** describes a provider's ability to produce an outcome.

A **CapabilityOffer** is the runtime snapshot used for matching.

## Capability ≠ Execution

```
CapabilityDeclaration          ExecutionBinding
  semantic_type: transport  →    protocol: ros2
  inputs, outputs, constraints   operation: transport_package
```

The same semantic capability may bind to ROS, OPC UA, or WoT on different providers.

## Composition

Optional `composed_of` lists other capability IDs. V0 does not resolve composition graphs during matching.
