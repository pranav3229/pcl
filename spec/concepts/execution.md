# Execution Binding

Execution bindings reference native protocol invocation. PCL V0 does not implement protocols.

## Adapter Contract

Adapters implement:

```python
class ExecutionAdapter(Protocol):
    protocol: str

    def validate_binding(self, binding: ExecutionBinding) -> list[str]:
        """Return validation errors, empty if valid."""

    def invoke(self, binding, inputs, context) -> dict:
        """Future: invoke native protocol. Not implemented in V0 stub."""
```

## Supported Protocols (V0)

| Protocol | Binding fields |
|----------|----------------|
| `ros2` | target, operation, parameters_map |
| `opcua` | target, operation, parameters_map |
| `wot` | target (TD URI), operation, parameters_map |
| `http` | target (URL), operation (method), parameters_map |
| `custom` | target, operation, metadata |
