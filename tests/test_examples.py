"""End-to-end integration and canonical example validation tests."""

import json
from pathlib import Path

from pcl.matcher import match
from pcl.models import CapabilityDeclaration, Evidence, Intent
from pcl.registry import Registry
from pcl.validate import validate_document
from pcl.verifier import verify_evidence

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = REPO_ROOT / "spec" / "examples"
REGISTRY_DIR = REPO_ROOT / "registry"


def test_canonical_warehouse_transport_lifecycle():
    """Validates the canonical warehouse AMR transport example through all 6 lifecycle stages."""
    # 1. Schema Validation
    decl_path = REGISTRY_DIR / "declarations" / "cap-transport-robot17.json"
    intent_path = EXAMPLES_DIR / "intent-package-transport.json"
    evidence_path = EXAMPLES_DIR / "evidence-package-transport.json"

    decl_data = json.loads(decl_path.read_text(encoding="utf-8"))
    intent_data = json.loads(intent_path.read_text(encoding="utf-8"))
    evidence_data = json.loads(evidence_path.read_text(encoding="utf-8"))

    assert validate_document(decl_data, "capability-declaration") == []
    assert validate_document(intent_data, "intent") == []
    assert validate_document(evidence_data, "evidence") == []

    # 2. Capability Matching
    intent = Intent.from_file(intent_path)
    registry = Registry.load(REGISTRY_DIR)
    results = match(intent, registry)

    assert len(results) >= 1
    best_match = results[0]
    assert best_match.entity_id == "robot-17"
    assert best_match.declaration_id == "cap-transport-robot17"
    assert best_match.score >= 100.0

    # 3. Invocation Parameter Resolution
    decl = CapabilityDeclaration.from_file(decl_path)
    assert decl.execution is not None
    native_payload = decl.execution.resolve_parameters(
        inputs=intent.inputs,
        constraints=intent.constraints,
    )
    assert native_payload == {
        "object": "package-123",
        "from": "warehouse-floor-2",
        "to": "zone-B",
    }

    # 4. Evidence Verification
    evidence = Evidence.from_file(evidence_path)
    veri_res = verify_evidence(evidence, intent=intent, declaration=decl)

    assert veri_res.valid is True
    assert veri_res.integrity == "verified"
    assert veri_res.provenance == "verified"
    assert veri_res.constraint_satisfaction == "satisfied"
