"""RFC 8785 JSON Canonicalization Scheme (JCS) and content digest calculation."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any


def _format_number(n: int | float) -> str:
    """Format number according to ECMAScript / RFC 8785 JSON number rules."""
    if isinstance(n, bool):
        return "true" if n else "false"
    if isinstance(n, int):
        return str(n)
    if isinstance(n, float):
        if math.isnan(n) or math.isinf(n):
            raise ValueError(f"Cannot canonicalize NaN or Infinity: {n}")
        if n == 0.0:
            return "0"
        # Check if float is an exact integer
        if n.is_integer():
            return str(int(n))
        # Use standard Python repr for float, which matches shortest round-trip (ECMAScript compliant)
        s = repr(n)
        if "e" in s or "E" in s:
            # Normalize exponential notation (e.g. 1e+05 -> 1e5 or 1e-05 -> 1e-5)
            s = s.replace("+0", "+").replace("-0", "-")
            if "+0" in s or "-0" in s:
                s = s.replace("0", "")
        return s
    raise TypeError(f"Unsupported number type: {type(n)}")


def canonicalize(obj: Any) -> bytes:
    """Serialize a Python data structure into canonical JSON bytes according to RFC 8785.

    Rules:
    - Object keys are sorted lexicographically by UTF-16 code units.
    - No whitespace is included outside string literals.
    - Strings are UTF-8 encoded with minimal standard JSON escaping.
    - Floats are formatted per ECMAScript / JCS specifications.
    """
    if obj is None:
        return b"null"
    if isinstance(obj, bool):
        return b"true" if obj else b"false"
    if isinstance(obj, (int, float)):
        return _format_number(obj).encode("utf-8")
    if isinstance(obj, str):
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if isinstance(obj, list):
        items = [canonicalize(x) for x in obj]
        return b"[" + b",".join(items) + b"]"
    if isinstance(obj, tuple):
        items = [canonicalize(x) for x in obj]
        return b"[" + b",".join(items) + b"]"
    if isinstance(obj, dict):
        # Sort keys lexicographically
        sorted_keys = sorted(obj.keys(), key=lambda k: str(k).encode("utf-16-be"))
        members = [
            json.dumps(str(k), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            + b":"
            + canonicalize(obj[k])
            for k in sorted_keys
        ]
        return b"{" + b",".join(members) + b"}"
    if hasattr(obj, "model_dump"):
        return canonicalize(obj.model_dump(mode="json", exclude_none=True))
    if hasattr(obj, "to_dict"):
        return canonicalize(obj.to_dict())

    raise TypeError(f"Type {type(obj).__name__} is not canonicalizable JSON")


def sha256_digest(data: Any) -> str:
    """Compute the algorithm-qualified SHA-256 digest of canonicalized data.

    Returns string in format: 'sha256:<hex_digest>'
    """
    if isinstance(data, bytes):
        raw_bytes = data
    else:
        raw_bytes = canonicalize(data)
    h = hashlib.sha256(raw_bytes).hexdigest()
    return f"sha256:{h}"
