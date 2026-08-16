#!/usr/bin/env python3
"""Minimal local HTTP capability server for PCL HTTP Execution Adapter demo.

Simulates an Autonomous Mobile Robot (AMR) executing physical package transport.
No external dependencies required (uses standard library http.server).
"""

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any


class CapabilityServerHandler(BaseHTTPRequestHandler):
    """Handles execution dispatch requests from PCL HTTP Adapter."""

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(200, {"status": "healthy", "service": "pcl-amr-http-server", "robot": "robot-17"})
        else:
            self._send_json(404, {"error": "Not Found", "path": self.path})

    def do_POST(self) -> None:
        if self.path != "/api/v1/transport":
            self._send_json(404, {"error": "Not Found", "path": self.path})
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

        try:
            payload = json.loads(body)
        except Exception as e:
            self._send_json(400, {"error": f"Invalid JSON payload: {e}"})
            return

        obj = payload.get("object", "package-unknown")
        origin = payload.get("from", "origin-unknown")
        dest = payload.get("to", "destination-unknown")

        print(f"\n[ROBOT-17 AMR SERVER] Received dispatch goal:")
        print(f"  - Object:      {obj}")
        print(f"  - Origin:      {origin}")
        print(f"  - Destination: {dest}")
        print(f"[ROBOT-17 AMR SERVER] Executing simulated navigation & transport...")

        # Construct realistic physical execution record
        response_data = {
            "status": "completed",
            "execution_id": "exec-http-8801",
            "summary": f"Package {obj} successfully transported from {origin} to {dest}",
            "outputs": {
                "delivered_object": {"ref": obj}
            },
            "metrics": {
                "max_payload": 10.0,
                "deadline": 12.5,
                "distance_km": 1.1
            },
            "artifacts": [
                {
                    "type": "delivery_photo",
                    "uri": "https://storage.pcl.dev/blobs/robot17-dropoff-8801.jpg",
                    "digest": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    "description": "Optical confirmation of package dropoff"
                }
            ]
        }

        print(f"[ROBOT-17 AMR SERVER] Mission complete. Returning execution payload.\n")
        self._send_json(200, response_data)

    def _send_json(self, status: int, data: dict[str, Any]) -> None:
        resp_bytes = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp_bytes)))
        self.end_headers()
        self.wfile.write(resp_bytes)


def main() -> None:
    parser = argparse.ArgumentParser(description="PCL Mock Capability HTTP Server")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    parser.add_argument("--host", default="127.0.0.1", help="Host address to bind to (default: 127.0.0.1)")
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), CapabilityServerHandler)
    print(f"==================================================")
    print(f"PCL Capability HTTP Server (Mock Robot-17 AMR)")
    print(f"Listening on: http://{args.host}:{args.port}")
    print(f"Endpoint:     http://{args.host}:{args.port}/api/v1/transport")
    print(f"Health Check: http://{args.host}:{args.port}/health")
    print(f"Press Ctrl+C to stop.")
    print(f"==================================================")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        server.server_close()


if __name__ == "__main__":
    main()
