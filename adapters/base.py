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
    """Declarative stub for ROS 2 execution bindings (V1 roadmap)."""

    def __init__(self) -> None:
        super().__init__("ros2")

    def validate_binding(self, binding: ExecutionBinding) -> list[str]:
        errors = super().validate_binding(binding)
        if not binding.target:
            errors.append("ros2 binding requires target (action/service/topic name)")
        return errors


class HttpAdapter(BaseAdapter):
    """Protocol adapter for HTTP REST execution bindings.
    
    Executes real HTTP requests (POST, PUT, GET, PATCH, DELETE) to external
    endpoints with JSON payload serialization, timeout controls, and structured error handling.
    """

    DEFAULT_TIMEOUT_SECONDS: float = 10.0
    MAX_RESPONSE_BYTES: int = 10 * 1024 * 1024  # 10 MB maximum response payload safety limit

    def __init__(self, default_timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        super().__init__("http")
        self.default_timeout = default_timeout

    def validate_binding(self, binding: ExecutionBinding) -> list[str]:
        errors = super().validate_binding(binding)
        if not binding.target:
            errors.append("http binding requires target URL")
        elif not (binding.target.startswith("http://") or binding.target.startswith("https://")):
            errors.append("http binding target must start with http:// or https://")
        if not binding.operation:
            errors.append("http binding requires operation (e.g. POST, GET, PUT, PATCH, DELETE)")
        return errors

    def invoke(
        self,
        binding: ExecutionBinding,
        inputs: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        """Invoke external HTTP endpoint with resolved parameters."""
        import json
        import socket
        import urllib.error
        import urllib.request

        errors = self.validate_binding(binding)
        if errors:
            return ExecutionResult(
                success=False,
                protocol=self.protocol,
                target=binding.target,
                operation=binding.operation,
                error=f"Binding validation failed: {'; '.join(errors)}",
            )

        constraints = context.get("constraints") if context else None
        try:
            payload = self.prepare_payload(binding, inputs=inputs, constraints=constraints)
        except Exception as e:
            return ExecutionResult(
                success=False,
                protocol=self.protocol,
                target=binding.target,
                operation=binding.operation,
                error=f"Parameter resolution failed: {e}",
            )

        method = (binding.operation or "POST").upper()
        target_url = binding.target

        # Determine timeout: context > binding.metadata > default
        timeout = self.default_timeout
        if context and "timeout" in context and isinstance(context["timeout"], (int, float)):
            timeout = float(context["timeout"])
        elif binding.metadata and "timeout" in binding.metadata and isinstance(binding.metadata["timeout"], (int, float)):
            timeout = float(binding.metadata["timeout"])

        # Configure headers
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "PCL-HttpAdapter/0.1.0",
        }
        if binding.metadata and "headers" in binding.metadata and isinstance(binding.metadata["headers"], dict):
            for k, v in binding.metadata["headers"].items():
                headers[str(k)] = str(v)

        req_data: bytes | None = None
        if method in ("POST", "PUT", "PATCH", "DELETE") and payload is not None:
            try:
                req_data = json.dumps(payload).encode("utf-8")
            except Exception as e:
                return ExecutionResult(
                    success=False,
                    protocol=self.protocol,
                    target=target_url,
                    operation=method,
                    error=f"Failed to serialize payload to JSON: {e}",
                )

        req = urllib.request.Request(
            url=target_url,
            data=req_data,
            headers=headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                status_code = response.status
                raw_bytes = response.read(self.MAX_RESPONSE_BYTES)
                resp_text = raw_bytes.decode("utf-8", errors="replace")

                resp_payload: Any = {}
                if resp_text.strip():
                    try:
                        resp_payload = json.loads(resp_text)
                    except Exception:
                        resp_payload = {"raw_response": resp_text}

                resp_headers = {k: v for k, v in response.headers.items()}
                success = 200 <= status_code < 300

                return ExecutionResult(
                    success=success,
                    protocol=self.protocol,
                    target=target_url,
                    operation=method,
                    payload=resp_payload if isinstance(resp_payload, dict) else {"data": resp_payload},
                    error=None if success else f"HTTP request returned status {status_code}",
                    metadata={
                        "status_code": status_code,
                        "headers": resp_headers,
                    },
                )
        except urllib.error.HTTPError as e:
            status_code = e.code
            err_payload: Any = {}
            try:
                raw_bytes = e.read(self.MAX_RESPONSE_BYTES)
                resp_text = raw_bytes.decode("utf-8", errors="replace")
                if resp_text.strip():
                    try:
                        err_payload = json.loads(resp_text)
                    except Exception:
                        err_payload = {"raw_response": resp_text}
            except Exception:
                err_payload = {}

            return ExecutionResult(
                success=False,
                protocol=self.protocol,
                target=target_url,
                operation=method,
                payload=err_payload if isinstance(err_payload, dict) else {"error_data": err_payload},
                error=f"HTTP {status_code}: {e.reason}",
                metadata={
                    "status_code": status_code,
                },
            )
        except urllib.error.URLError as e:
            if isinstance(e.reason, (TimeoutError, socket.timeout)):
                return ExecutionResult(
                    success=False,
                    protocol=self.protocol,
                    target=target_url,
                    operation=method,
                    error=f"Request timed out after {timeout}s",
                    metadata={"error_type": "TimeoutError"},
                )
            return ExecutionResult(
                success=False,
                protocol=self.protocol,
                target=target_url,
                operation=method,
                error=f"Connection error: {e.reason}",
                metadata={"error_type": "URLError"},
            )
        except (TimeoutError, socket.timeout):
            return ExecutionResult(
                success=False,
                protocol=self.protocol,
                target=target_url,
                operation=method,
                error=f"Request timed out after {timeout}s",
                metadata={"error_type": "TimeoutError"},
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                protocol=self.protocol,
                target=target_url,
                operation=method,
                error=f"Execution failed: {e}",
                metadata={"error_type": type(e).__name__},
            )


class OpcUaAdapter(BaseAdapter):
    """Declarative stub for OPC-UA execution bindings (V1 roadmap)."""

    def __init__(self) -> None:
        super().__init__("opcua")

    def validate_binding(self, binding: ExecutionBinding) -> list[str]:
        errors = super().validate_binding(binding)
        if not binding.target:
            errors.append("opcua binding requires target server endpoint")
        return errors


class WotAdapter(BaseAdapter):
    """Declarative stub for W3C Web of Things execution bindings (V1 roadmap)."""

    def __init__(self) -> None:
        super().__init__("wot")

    def validate_binding(self, binding: ExecutionBinding) -> list[str]:
        errors = super().validate_binding(binding)
        if not binding.target:
            errors.append("wot binding requires target (Thing Description URI)")
        return errors
