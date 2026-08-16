"""PCL document models."""

from __future__ import annotations

import json
import math
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class Comparator(str, Enum):
    EQ = "eq"
    LTE = "lte"
    GTE = "gte"
    LT = "lt"
    GT = "gt"


class IORole(str, Enum):
    OBJECT = "object"
    ORIGIN = "origin"
    DESTINATION = "destination"
    PARAMETER = "parameter"
    ARTIFACT = "artifact"
    REPORT = "report"


class ValueKind(str, Enum):
    ENTITY_REF = "entity_ref"
    LOCATION_REF = "location_ref"
    QUANTITY = "quantity"
    FILE_REF = "file_ref"
    STRING = "string"
    STRUCTURED = "structured"


class Protocol(str, Enum):
    ROS2 = "ros2"
    OPCUA = "opcua"
    WOT = "wot"
    HTTP = "http"
    CUSTOM = "custom"


class RuntimeStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    CHARGING = "charging"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    FAULT = "fault"
    ACTIVE = "active"


class SemanticRef(BaseModel):
    term: str
    vocabulary: str | None = None
    label: str | None = None

    def matches(self, other: SemanticRef) -> bool:
        if self.vocabulary != other.vocabulary:
            return False
        return self.term == other.term


class Quantity(BaseModel):
    value: float
    unit: str
    comparator: Comparator = Comparator.EQ


class Range(BaseModel):
    min: float
    max: float
    unit: str | None = None


class SetPredicate(BaseModel):
    in_values: list[str | int | float | bool] = Field(alias="in")

    model_config = {"populate_by_name": True}


class ValuePredicate(BaseModel):
    value: Any
    comparator: str | None = None


ConstraintPredicate = Quantity | Range | SetPredicate | ValuePredicate


class ConstraintDiagnostic(BaseModel):
    constraint: str
    result: str
    reason: str | None = None


class IOContract(BaseModel):
    name: str
    role: IORole
    value_kind: ValueKind
    required: bool = True
    schema_ref: str | None = None


class ConstraintSpec(BaseModel):
    name: str
    quantity: Quantity | None = None
    range: Range | None = None
    in_values: list[str | int | float | bool] | None = Field(default=None, alias="in")
    value: Any = None
    applies_to: str = "capability"

    model_config = {"populate_by_name": True}


EARTH_RADIUS_KM = 6371.0088


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on the Earth in kilometers."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_KM * c


class Location(BaseModel):
    kind: str
    ref: str | None = None
    lat: float | None = None
    lon: float | None = None
    alt: float | None = None

    def matches(self, other: Location, tolerance_km: float = 0.0) -> bool:
        if self.kind != other.kind:
            return False

        if self.kind == "semantic":
            return self.ref is not None and self.ref == other.ref

        if self.kind == "coordinates":
            if self.lat is None or self.lon is None or other.lat is None or other.lon is None:
                return False
            dist = haversine_distance(self.lat, self.lon, other.lat, other.lon)
            return dist <= tolerance_km

        if self.kind == "uri":
            return self.ref is not None and self.ref == other.ref

        return False


def _extract_source_value(source_path: str, context: dict[str, Any]) -> Any:
    """Extract a value from context using a dot-delimited source path.

    Path format:
        inputs.<input_name>[.<field_name>]
        constraints.<constraint_name>[.<field_name>]
    """
    if not source_path or not isinstance(source_path, str):
        raise ValueError(f"Invalid source path '{source_path}': must be a non-empty string")

    parts = source_path.strip().split(".")
    if len(parts) < 2:
        raise ValueError(
            f"Malformed source path '{source_path}': must contain at least root and name (e.g. 'inputs.target')"
        )

    root, name = parts[0], parts[1]
    if root not in ("inputs", "constraints"):
        raise ValueError(
            f"Invalid source path root '{root}' in '{source_path}': must start with 'inputs' or 'constraints'"
        )

    root_dict = context.get(root)
    if root_dict is None or not isinstance(root_dict, dict):
        raise ValueError(f"Cannot resolve '{source_path}': root '{root}' not found in context")

    if name not in root_dict:
        raise ValueError(f"Cannot resolve '{source_path}': '{name}' not found in {root}")

    current = root_dict[name]

    # If the path is exactly 'inputs.<name>'
    if len(parts) == 2:
        if isinstance(current, IntentInputValue):
            if current.value is not None:
                return current.value
            elif current.ref is not None:
                return current.ref
            elif current.quantity is not None:
                return current.quantity
            return current
        elif isinstance(current, dict):
            if "value" in current and len(current) == 1:
                return current["value"]
            elif "ref" in current and len(current) == 1:
                return current["ref"]
            elif "quantity" in current and len(current) == 1:
                return current["quantity"]
            return current
        elif isinstance(current, ValuePredicate):
            return current.value
        elif isinstance(current, Quantity):
            return current.value
        return current

    # Traverse remaining path elements
    for part in parts[2:]:
        if current is None:
            raise ValueError(f"Cannot resolve '{source_path}': step '{part}' on None value")

        if isinstance(current, dict):
            if part not in current:
                if "value" in current and isinstance(current["value"], dict) and part in current["value"]:
                    current = current["value"][part]
                elif "value" in current and hasattr(current["value"], part):
                    current = getattr(current["value"], part)
                else:
                    raise ValueError(f"Cannot resolve '{source_path}': key '{part}' not found in dictionary")
            else:
                current = current[part]
        elif isinstance(current, IntentInputValue):
            if hasattr(current, part) and getattr(current, part) is not None:
                current = getattr(current, part)
            elif current.value is not None:
                val = current.value
                if isinstance(val, dict) and part in val:
                    current = val[part]
                elif hasattr(val, part):
                    current = getattr(val, part)
                else:
                    raise ValueError(
                        f"Cannot resolve '{source_path}': attribute '{part}' not found on IntentInputValue.value"
                    )
            else:
                raise ValueError(f"Cannot resolve '{source_path}': field '{part}' not found in IntentInputValue")
        elif hasattr(current, part):
            current = getattr(current, part)
            if isinstance(current, Enum):
                current = current.value
        else:
            raise ValueError(
                f"Cannot resolve '{source_path}': attribute '{part}' not found on object of type {type(current).__name__}"
            )

    if isinstance(current, Enum):
        return current.value
    return current


def _set_nested_value(target_dict: dict[str, Any], native_key: str, value: Any) -> None:
    """Set a value in a nested dictionary from a dot-delimited native key path."""
    if not native_key or not isinstance(native_key, str):
        raise ValueError(f"Invalid native parameter key '{native_key}': must be a non-empty string")

    parts = native_key.strip().split(".")
    curr = target_dict
    for part in parts[:-1]:
        if not part:
            raise ValueError(f"Malformed native parameter key '{native_key}': empty path segment")
        if part not in curr:
            curr[part] = {}
        elif not isinstance(curr[part], dict):
            raise ValueError(
                f"Collision in native parameter mapping for '{native_key}': '{part}' is already a non-dict value"
            )
        curr = curr[part]

    leaf = parts[-1]
    if not leaf:
        raise ValueError(f"Malformed native parameter key '{native_key}': empty leaf segment")
    curr[leaf] = value


class ExecutionBinding(BaseModel):
    protocol: str | Protocol
    target: str | None = None
    operation: str | None = None
    parameters_map: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def resolve_parameters(
        self,
        intent: Any = None,
        inputs: dict[str, Any] | None = None,
        constraints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Deterministically resolve parameters_map against an Intent or inputs/constraints context.

        Returns a nested dictionary representing the native payload.
        Fails closed (raises ValueError) if any required path cannot be resolved.
        """
        context: dict[str, Any] = {"inputs": {}, "constraints": {}}
        if intent is not None:
            if hasattr(intent, "inputs"):
                context["inputs"] = getattr(intent, "inputs")
            if hasattr(intent, "constraints"):
                context["constraints"] = getattr(intent, "constraints")
        if inputs is not None:
            context["inputs"].update(inputs)
        if constraints is not None:
            context["constraints"].update(constraints)

        result: dict[str, Any] = {}
        for native_key, source_path in self.parameters_map.items():
            val = _extract_source_value(source_path, context)
            _set_nested_value(result, native_key, val)

        return result

    def validate_binding(self) -> list[str]:
        """Validate structural correctness of this execution binding.

        Returns a list of error strings; empty if valid.
        """
        errors: list[str] = []
        proto_str = self.protocol.value if isinstance(self.protocol, Enum) else str(self.protocol)
        if not proto_str or not proto_str.strip():
            errors.append("protocol is required and cannot be empty")

        if self.target is not None and not isinstance(self.target, str):
            errors.append("target must be a string if provided")

        if self.operation is not None and not isinstance(self.operation, str):
            errors.append("operation must be a string if provided")

        if not isinstance(self.parameters_map, dict):
            errors.append("parameters_map must be a dictionary")
        else:
            for k, v in self.parameters_map.items():
                if not isinstance(k, str) or not k.strip():
                    errors.append(f"parameters_map key must be a non-empty string, got {k!r}")
                if not isinstance(v, str) or not v.strip():
                    errors.append(f"parameters_map value for '{k}' must be a non-empty string, got {v!r}")
                elif not (v.startswith("inputs.") or v.startswith("constraints.")):
                    errors.append(
                        f"parameters_map source path '{v}' for '{k}' must start with 'inputs.' or 'constraints.'"
                    )
                elif len(v.split(".")) < 2 or any(not seg.strip() for seg in v.split(".")):
                    errors.append(f"malformed parameters_map source path '{v}' for '{k}'")

        return errors


class RuntimeState(BaseModel):
    status: RuntimeStatus
    detail: str | None = None


class Availability(BaseModel):
    accepts_work: bool
    reason: str | None = None
    valid_until: str | None = None
    schedule: list[str] = Field(default_factory=list)


class IntentInputValue(BaseModel):
    ref: str | None = None
    value: Any = None
    quantity: Quantity | None = None


class IntentPreferences(BaseModel):
    provider_id: str | None = None


class Entity(BaseModel):
    pcl_version: str = "0.1.0"
    id: str
    name: str | None = None
    entity_type: SemanticRef | None = None
    controller: str | None = None
    contains: list[str] = Field(default_factory=list)
    location: Location | None = None
    extensions: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_file(cls, path: str | Path) -> Entity:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(data)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class CapabilityDeclaration(BaseModel):
    pcl_version: str = "0.1.0"
    id: str
    entity_id: str
    semantic_type: SemanticRef
    summary: str | None = None
    mode: str = "discrete"
    inputs: list[IOContract] = Field(default_factory=list)
    outputs: list[IOContract] = Field(default_factory=list)
    constraints: list[ConstraintSpec] = Field(default_factory=list)
    execution: ExecutionBinding
    composed_of: list[str] = Field(default_factory=list)
    evidence_spec: list[str] = Field(default_factory=list)
    extensions: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_file(cls, path: str | Path) -> CapabilityDeclaration:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(data)

    def constraint_by_name(self, name: str) -> ConstraintSpec | None:
        for c in self.constraints:
            if c.name == name:
                return c
        return None


class CapabilityOffer(BaseModel):
    id: str | None = None
    declaration_id: str
    entity_id: str
    state: RuntimeState
    availability: Availability
    location: Location | None = None
    resources: dict[str, Any] = Field(default_factory=dict)
    extensions: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_file(cls, path: str | Path) -> CapabilityOffer:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(data)

    @property
    def offer_id(self) -> str:
        return self.id or f"{self.entity_id}:{self.declaration_id}"


class Intent(BaseModel):
    pcl_version: str = "0.1.0"
    id: str
    goal: SemanticRef
    inputs: dict[str, IntentInputValue] = Field(default_factory=dict)
    required_outputs: list[str] = Field(default_factory=list)
    constraints: dict[str, ConstraintPredicate] = Field(default_factory=dict)
    preferences: IntentPreferences | None = None
    extensions: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_file(cls, path: str | Path) -> Intent:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(data)


class MatchResult(BaseModel):
    declaration_id: str
    entity_id: str
    offer_id: str
    score: float
    satisfied: list[str] = Field(default_factory=list)
    unsatisfied: list[str] = Field(default_factory=list)
    diagnostics: list[ConstraintDiagnostic] = Field(default_factory=list)
    offer: CapabilityOffer
    declaration: CapabilityDeclaration


class OutcomeStatus(str, Enum):
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ArtifactRef(BaseModel):
    type: str
    uri: str
    digest: str
    size_bytes: int | None = None
    description: str | None = None


class Attestation(BaseModel):
    issuer: str
    role: str = "provider"
    algorithm: str = "ed25519"
    public_key_ref: str | None = None
    public_key: str | None = None
    timestamp: str
    signature: str

    def verify(self, digest_bytes: bytes, public_key_override: Any = None) -> bool:
        from pcl.crypto import verify_signature

        key_to_use = public_key_override or self.public_key or self.public_key_ref
        if not key_to_use:
            return False
        return verify_signature(
            public_key_input=key_to_use,
            signature_b64=self.signature,
            digest_bytes=digest_bytes,
            algorithm=self.algorithm,
        )


class Evidence(BaseModel):
    pcl_version: str = "0.1.0"
    id: str
    execution_id: str
    intent_id: str
    declaration_id: str
    entity_id: str
    timestamp: str
    outcome: OutcomeStatus
    summary: str | None = None
    observed_outputs: dict[str, Any] = Field(default_factory=dict)
    observed_metrics: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    attestations: list[Attestation] = Field(default_factory=list)
    extensions: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_file(cls, path: str | Path) -> Evidence:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(data)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)

    def canonical_payload(self) -> dict[str, Any]:
        """Return the dictionary of evidence content to be signed, excluding attestations."""
        data = self.model_dump(mode="json", exclude={"attestations"}, exclude_none=True)
        return data

    def canonical_bytes(self) -> bytes:
        """Return RFC 8785 canonical JSON bytes of the unsigned evidence payload."""
        from pcl.canonical import canonicalize

        return canonicalize(self.canonical_payload())

    def digest(self) -> str:
        """Compute the SHA-256 algorithm-qualified digest of the canonicalized evidence."""
        from pcl.canonical import sha256_digest

        return sha256_digest(self.canonical_bytes())

    def sign(
        self,
        private_key: Any,
        issuer: str,
        role: str = "provider",
        algorithm: str = "ed25519",
        public_key: str | None = None,
        public_key_ref: str | None = None,
        timestamp: str | None = None,
    ) -> Attestation:
        """Sign this evidence and append the attestation."""
        from datetime import datetime, timezone
        from pcl.crypto import sign_digest

        ts = timestamp or datetime.now(timezone.utc).isoformat()
        digest_bytes = self.canonical_bytes()
        sig_b64 = sign_digest(private_key, digest_bytes, algorithm=algorithm)
        att = Attestation(
            issuer=issuer,
            role=role,
            algorithm=algorithm,
            public_key_ref=public_key_ref,
            public_key=public_key,
            timestamp=ts,
            signature=sig_b64,
        )
        self.attestations.append(att)
        return att


class VerificationResult(BaseModel):
    valid: bool
    integrity: str  # "verified", "failed", "unverified"
    provenance: str  # "verified", "failed", "unverified"
    constraint_satisfaction: str  # "satisfied", "failed", "not_evaluable"
    outcome: str
    diagnostics: list[ConstraintDiagnostic] = Field(default_factory=list)
