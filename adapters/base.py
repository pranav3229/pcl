"""Protocol adapter interface for execution bindings."""

from __future__ import annotations

from enum import Enum
from typing import Any, Protocol, runtime_checkable
from pydantic import BaseModel, Field

from pcl.models import ExecutionBinding


class ExecutionResult(BaseModel):
    """Result returned by a protocol adapter invocation."""

    success: bool
    protocol: str
    target: str | None = None
    operation: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class ExecutionAdapter(Protocol):
    protocol: str

    def validate_binding(self, binding: ExecutionBinding) -> list[str]:
        """Return validation errors; empty list if valid."""

    def invoke(
        self,
        binding: ExecutionBinding,
        inputs: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Invoke native protocol. Not implemented in V0 stubs."""


class BaseAdapter:
    """Base abstract adapter providing parameter resolution and structural validation."""

    def __init__(self, protocol: str) -> None:
        self.protocol = protocol

    def _proto_str(self, binding: ExecutionBinding) -> str:
        if isinstance(binding.protocol, Enum):
            return binding.protocol.value
        return str(binding.protocol)

    def validate_binding(self, binding: ExecutionBinding) -> list[str]:
        errors: list[str] = binding.validate_binding()
        if self._proto_str(binding) != self.protocol:
            errors.append(f"expected protocol {self.protocol}, got {self._proto_str(binding)}")
        return errors

    def prepare_payload(
        self,
        binding: ExecutionBinding,
        inputs: dict[str, Any],
        constraints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Resolve native payload using binding parameters_map."""
        return binding.resolve_parameters(inputs=inputs, constraints=constraints)

    def invoke(
        self,
        binding: ExecutionBinding,
        inputs: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        errors = self.validate_binding(binding)
        if errors:
            return ExecutionResult(
                success=False,
                protocol=self.protocol,
                target=binding.target,
                operation=binding.operation,
                error=f"Binding validation failed: {'; '.join(errors)}",
            )
        raise NotImplementedError(
            f"V0 {self.protocol} adapter is a declarative stub; native network execution is not implemented"
        )


class StubAdapter(BaseAdapter):
    """Stub adapter for testing."""


class Ros2Adapter(BaseAdapter):
    def __init__(self) -> None:
        super().__init__("ros2")

    def validate_binding(self, binding: ExecutionBinding) -> list[str]:
        errors = super().validate_binding(binding)
        if not binding.target:
            errors.append("ros2 binding requires target (action/service/topic name)")
        return errors


class HttpAdapter(BaseAdapter):
    def __init__(self) -> None:
        super().__init__("http")

    def validate_binding(self, binding: ExecutionBinding) -> list[str]:
        errors = super().validate_binding(binding)
        if not binding.target:
            errors.append("http binding requires target URL")
        if not binding.operation:
            errors.append("http binding requires operation (e.g. POST, GET, PUT)")
        return errors


class OpcUaAdapter(BaseAdapter):
    def __init__(self) -> None:
        super().__init__("opcua")

    def validate_binding(self, binding: ExecutionBinding) -> list[str]:
        errors = super().validate_binding(binding)
        if not binding.target:
            errors.append("opcua binding requires target server endpoint")
        return errors


class WotAdapter(BaseAdapter):
    def __init__(self) -> None:
        super().__init__("wot")

    def validate_binding(self, binding: ExecutionBinding) -> list[str]:
        errors = super().validate_binding(binding)
        if not binding.target:
            errors.append("wot binding requires target (Thing Description URI)")
        return errors
