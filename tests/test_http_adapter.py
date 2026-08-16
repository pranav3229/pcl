"""Integration and unit tests for the PCL HTTP Execution Adapter.

Performs real network HTTP I/O against a local HTTP server test fixture.
Tests:
- Successful invocation with parameter mapping and 2xx JSON response
- Payload serialization and verification on server side
- Connection error handling (unreachable/wrong port)
- HTTP error status code handling (500 Internal Server Error)
- Request timeout handling against slow endpoints
- Security validation (unsupported URL schemes)
- Custom headers and HTTP methods (PUT, POST)
- Full End-to-End PCL Lifecycle:
  Match Intent -> Resolve Parameters -> HTTP Invoke -> Construct Evidence -> Sign Attestation -> Verify Evidence
"""

from __future__ import annotations

import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Generator
import pytest

from adapters.base import HttpAdapter, ExecutionResult
from pcl.crypto import generate_ed25519_keypair
from pcl.matcher import match_intent_to_offer
from pcl.models import (
    Availability,
    CapabilityDeclaration,
    CapabilityOffer,
    Comparator,
    ConstraintSpec,
    Evidence,
    ExecutionBinding,
    IOContract,
    IORole,
    Intent,
    IntentInputValue,
    OutcomeStatus,
    Protocol,
    Quantity,
    RuntimeState,
    RuntimeStatus,
    SemanticRef,
    ValueKind,
)
from pcl.verifier import verify_evidence


class MockCapabilityHandler(BaseHTTPRequestHandler):
    """Local HTTP capability mock server handler."""

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress stdout log noise during automated test runs."""
        return

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length) if content_length > 0 else b""
        
        # Save received request data on server instance for assertion in tests
        self.server.last_request = {
            "path": self.path,
            "method": "POST",
            "headers": {k.lower(): v for k, v in self.headers.items()},
            "body": body_bytes.decode("utf-8", errors="replace"),
        }

        if self.path == "/api/v1/transport":
            try:
                data = json.loads(body_bytes.decode("utf-8"))
            except Exception:
                data = {}

            response_data = {
                "status": "completed",
                "execution_id": "exec-http-7701",
                "summary": f"Transported {data.get('object', 'unknown')} from {data.get('from', 'A')} to {data.get('to', 'B')}",
                "outputs": {
                    "delivered_object": {"ref": data.get("object", "package-123")}
                },
                "metrics": {
                    "max_payload": 10.0,
                    "deadline": 14.0,
                    "budget": 45.0,
                },
                "artifacts": [
                    {
                        "type": "delivery_photo",
                        "uri": "https://storage.pcl.dev/blobs/delivery-7701.jpg",
                        "digest": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    }
                ],
            }
            resp_bytes = json.dumps(response_data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp_bytes)))
            self.end_headers()
            self.wfile.write(resp_bytes)

        elif self.path == "/api/v1/error":
            error_data = {
                "error": "Actuator arm hardware fault during transport",
                "code": "ACTUATOR_FAULT",
                "retryable": False,
            }
            resp_bytes = json.dumps(error_data).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp_bytes)))
            self.end_headers()
            self.wfile.write(resp_bytes)

        elif self.path == "/api/v1/slow":
            # Deliberate sleep exceeding test client timeout
            time.sleep(0.5)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"late"}')

        elif self.path == "/api/v1/plain":
            resp_bytes = b"OK - Physical machine started"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(resp_bytes)))
            self.end_headers()
            self.wfile.write(resp_bytes)

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error":"not found"}')

    def do_PUT(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length) if content_length > 0 else b""
        self.server.last_request = {
            "path": self.path,
            "method": "PUT",
            "headers": {k.lower(): v for k, v in self.headers.items()},
            "body": body_bytes.decode("utf-8", errors="replace"),
        }
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"updated"}')


class LocalTestServer(HTTPServer):
    def __init__(self, server_address: tuple[str, int]) -> None:
        super().__init__(server_address, MockCapabilityHandler)
        self.last_request: dict[str, Any] = {}


@pytest.fixture
def mock_http_server() -> Generator[tuple[LocalTestServer, str], None, None]:
    """Start local mock HTTP server on an OS-assigned ephemeral port."""
    server = LocalTestServer(("127.0.0.1", 0))
    port = server.server_address[1]
    base_url = f"http://127.0.0.1:{port}"

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield server, base_url

    server.shutdown()
    server.server_close()


# ============================================================================
# 1. HTTP ADAPTER UNIT & TRANSPORT TESTS
# ============================================================================


def test_http_adapter_successful_post_invocation(mock_http_server: tuple[LocalTestServer, str]) -> None:
    """HttpAdapter successfully sends POST request with resolved JSON body and parses 200 response."""
    server, base_url = mock_http_server
    adapter = HttpAdapter(default_timeout=5.0)

    binding = ExecutionBinding(
        protocol="http",
        target=f"{base_url}/api/v1/transport",
        operation="POST",
        parameters_map={
            "object": "inputs.object.ref",
            "from": "inputs.origin.ref",
            "to": "inputs.destination.ref",
        },
    )

    inputs = {
        "object": IntentInputValue(ref="package-42"),
        "origin": IntentInputValue(ref="shelf-A1"),
        "destination": IntentInputValue(ref="dock-3"),
    }

    result = adapter.invoke(binding, inputs=inputs)

    assert isinstance(result, ExecutionResult)
    assert result.success is True
    assert result.protocol == "http"
    assert result.target == f"{base_url}/api/v1/transport"
    assert result.operation == "POST"
    assert result.error is None
    assert result.metadata.get("status_code") == 200
    assert result.payload.get("status") == "completed"
    assert result.payload.get("execution_id") == "exec-http-7701"

    # Verify what the server actually received over the wire
    assert server.last_request["method"] == "POST"
    assert server.last_request["path"] == "/api/v1/transport"
    received_payload = json.loads(server.last_request["body"])
    assert received_payload == {
        "object": "package-42",
        "from": "shelf-A1",
        "to": "dock-3",
    }


def test_http_adapter_connection_failure_handled_gracefully() -> None:
    """Connection failure on unreachable endpoint returns structured failure, not uncaught crash."""
    # Find an unused local port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    unused_port = sock.getsockname()[1]
    sock.close()

    adapter = HttpAdapter(default_timeout=2.0)
    binding = ExecutionBinding(
        protocol="http",
        target=f"http://127.0.0.1:{unused_port}/not-running",
        operation="POST",
    )

    result = adapter.invoke(binding, inputs={})

    assert isinstance(result, ExecutionResult)
    assert result.success is False
    assert result.error is not None
    assert "Connection error" in result.error or "timed out" in result.error


def test_http_adapter_server_error_500_response(mock_http_server: tuple[LocalTestServer, str]) -> None:
    """Server returning HTTP 500 is cleanly reported as a failure with error details."""
    server, base_url = mock_http_server
    adapter = HttpAdapter(default_timeout=5.0)

    binding = ExecutionBinding(
        protocol="http",
        target=f"{base_url}/api/v1/error",
        operation="POST",
    )

    result = adapter.invoke(binding, inputs={})

    assert result.success is False
    assert result.metadata.get("status_code") == 500
    assert "HTTP 500" in (result.error or "")
    assert result.payload.get("code") == "ACTUATOR_FAULT"


def test_http_adapter_timeout_handling(mock_http_server: tuple[LocalTestServer, str]) -> None:
    """Adapter timeout terminates slow request and returns structured timeout error."""
    server, base_url = mock_http_server
    # Configure tight timeout of 0.1s against slow endpoint that sleeps 0.5s
    adapter = HttpAdapter(default_timeout=0.1)

    binding = ExecutionBinding(
        protocol="http",
        target=f"{base_url}/api/v1/slow",
        operation="POST",
    )

    result = adapter.invoke(binding, inputs={})

    assert result.success is False
    assert "timed out" in (result.error or "").lower()
    assert result.metadata.get("error_type") == "TimeoutError"


def test_http_adapter_security_url_scheme_validation() -> None:
    """HttpAdapter fails closed on dangerous or non-http schemes (file://, ftp://)."""
    adapter = HttpAdapter()

    # file:// scheme
    binding_file = ExecutionBinding(protocol="http", target="file:///etc/passwd", operation="POST")
    res_file = adapter.invoke(binding_file, inputs={})
    assert res_file.success is False
    assert "must start with http:// or https://" in (res_file.error or "")

    # ftp:// scheme
    binding_ftp = ExecutionBinding(protocol="http", target="ftp://storage.example.com", operation="GET")
    res_ftp = adapter.invoke(binding_ftp, inputs={})
    assert res_ftp.success is False
    assert "must start with http:// or https://" in (res_ftp.error or "")


def test_http_adapter_custom_headers_and_put_method(mock_http_server: tuple[LocalTestServer, str]) -> None:
    """HttpAdapter sends custom metadata headers and handles PUT method."""
    server, base_url = mock_http_server
    adapter = HttpAdapter()

    binding = ExecutionBinding(
        protocol="http",
        target=f"{base_url}/api/v1/update",
        operation="PUT",
        parameters_map={"status": "inputs.new_status.value"},
        metadata={
            "headers": {
                "X-Robot-Auth-Token": "secret-token-12345",
                "X-Client-ID": "dispatcher-alpha",
            }
        },
    )

    inputs = {"new_status": IntentInputValue(value="online")}
    result = adapter.invoke(binding, inputs=inputs)

    assert result.success is True
    assert server.last_request["method"] == "PUT"
    assert server.last_request["headers"].get("x-robot-auth-token") == "secret-token-12345"
    assert server.last_request["headers"].get("x-client-id") == "dispatcher-alpha"


def test_http_adapter_plain_text_response_handling(mock_http_server: tuple[LocalTestServer, str]) -> None:
    """Non-JSON plain text responses are captured gracefully in raw_response."""
    server, base_url = mock_http_server
    adapter = HttpAdapter()

    binding = ExecutionBinding(
        protocol="http",
        target=f"{base_url}/api/v1/plain",
        operation="POST",
    )

    result = adapter.invoke(binding, inputs={})
    assert result.success is True
    assert "Physical machine started" in result.payload.get("raw_response", "")


# ============================================================================
# 2. FULL END-TO-END PCL HTTP LIFECYCLE TEST
# ============================================================================


def test_end_to_end_http_lifecycle_matching_to_verification(mock_http_server: tuple[LocalTestServer, str]) -> None:
    """Full PCL Lifecycle: Match -> Resolve -> HTTP Invoke -> Evidence -> Verify.

    1. Match consumer Intent against HTTP-bound CapabilityDeclaration + Offer.
    2. Resolve invocation parameters into native HTTP JSON body.
    3. Dispatch real HTTP request via HttpAdapter to local mock capability server.
    4. Receive ExecutionResult containing observed metrics, outputs, and artifacts.
    5. Construct an Evidence document from the execution record.
    6. Sign Evidence with provider's Ed25519 private key.
    7. Cryptographically verify the Evidence against original Intent and Declaration.
    """
    server, base_url = mock_http_server

    # 1. Define Capability Declaration with real HTTP binding
    decl = CapabilityDeclaration(
        pcl_version="0.1.0",
        id="cap-transport-http-amr",
        entity_id="robot-amr-42",
        semantic_type=SemanticRef(
            vocabulary="https://pcl.dev/vocab/logistics/v0",
            term="package_transport",
            label="AMR Package Transport",
        ),
        summary="Autonomous package transport via HTTP REST capability bridge",
        inputs=[
            IOContract(name="object", role=IORole.OBJECT, value_kind=ValueKind.ENTITY_REF, required=True),
            IOContract(name="origin", role=IORole.ORIGIN, value_kind=ValueKind.LOCATION_REF, required=True),
            IOContract(name="destination", role=IORole.DESTINATION, value_kind=ValueKind.LOCATION_REF, required=True),
        ],
        outputs=[
            IOContract(name="delivered_object", role=IORole.OBJECT, value_kind=ValueKind.ENTITY_REF),
        ],
        constraints=[
            ConstraintSpec(name="max_payload", quantity=Quantity(value=25.0, unit="kg", comparator=Comparator.LTE)),
            ConstraintSpec(name="deadline", quantity=Quantity(value=30.0, unit="min", comparator=Comparator.LTE)),
        ],
        execution=ExecutionBinding(
            protocol=Protocol.HTTP,
            target=f"{base_url}/api/v1/transport",
            operation="POST",
            parameters_map={
                "object": "inputs.object.ref",
                "from": "inputs.origin.ref",
                "to": "inputs.destination.ref",
            },
        ),
    )

    offer = CapabilityOffer(
        id="offer-http-amr-01",
        declaration_id="cap-transport-http-amr",
        entity_id="robot-amr-42",
        state=RuntimeState(status=RuntimeStatus.IDLE),
        availability=Availability(accepts_work=True),
    )

    # 2. Consumer Intent
    intent = Intent(
        pcl_version="0.1.0",
        id="intent-pkg-transport-99",
        goal=SemanticRef(
            vocabulary="https://pcl.dev/vocab/logistics/v0",
            term="package_transport",
        ),
        inputs={
            "object": IntentInputValue(ref="package-101"),
            "origin": IntentInputValue(ref="storage-bay-2"),
            "destination": IntentInputValue(ref="dispatch-dock-A"),
        },
        constraints={
            "max_payload": Quantity(value=10.0, unit="kg", comparator=Comparator.LTE),
            "deadline": Quantity(value=20.0, unit="min", comparator=Comparator.LTE),
        },
    )

    # Step 1: Matching
    match_result = match_intent_to_offer(intent, offer, decl)
    assert match_result is not None
    assert match_result.entity_id == "robot-amr-42"
    assert "constraints" in match_result.satisfied
    assert "goal" in match_result.satisfied

    # Step 2: Parameter Resolution
    resolved_payload = decl.execution.resolve_parameters(
        inputs=intent.inputs,
        constraints=intent.constraints,
    )
    assert resolved_payload == {
        "object": "package-101",
        "from": "storage-bay-2",
        "to": "dispatch-dock-A",
    }

    # Step 3: HTTP Adapter Execution
    adapter = HttpAdapter(default_timeout=5.0)
    exec_result = adapter.invoke(
        decl.execution,
        inputs=intent.inputs,
        context={"constraints": intent.constraints},
    )

    assert exec_result.success is True
    assert exec_result.metadata["status_code"] == 200
    assert exec_result.payload["status"] == "completed"

    # Step 4: Construct Evidence Document from Execution Result
    resp_body = exec_result.payload
    priv_key, pub_b64 = generate_ed25519_keypair()

    evidence = Evidence(
        pcl_version="0.1.0",
        id="evi-transport-exec-001",
        execution_id=resp_body["execution_id"],
        intent_id=intent.id,
        declaration_id=decl.id,
        entity_id=decl.entity_id,
        timestamp="2026-08-16T12:00:00Z",
        outcome=OutcomeStatus.COMPLETED,
        summary=resp_body["summary"],
        observed_outputs=resp_body["outputs"],
        observed_metrics=resp_body["metrics"],
        artifacts=resp_body["artifacts"],
    )

    # Step 5: Sign Evidence Attestation
    att = evidence.sign(
        private_key=priv_key,
        issuer="robot-amr-42",
        role="provider",
        algorithm="ed25519",
        public_key=pub_b64,
        timestamp="2026-08-16T12:00:05Z",
    )
    assert att.signature is not None

    # Step 6: Verify Evidence (Cryptographic Integrity, Provenance Linkage, Intent Constraint Satisfaction)
    verification = verify_evidence(
        evidence=evidence,
        intent=intent,
        declaration=decl,
        public_keys={"robot-amr-42": pub_b64},
    )

    assert verification.valid is True
    assert verification.integrity == "verified"
    assert verification.provenance == "verified"
    assert verification.constraint_satisfaction == "satisfied"
    assert verification.outcome == "completed"
