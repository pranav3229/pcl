"""PCL command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pcl.matcher import match
from pcl.models import Intent
from pcl.registry import Registry
from pcl.validate import validate_document


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def cmd_validate(args: argparse.Namespace) -> int:
    schema_map = {
        "entity": "entity",
        "declaration": "capability-declaration",
        "offer": "capability-offer",
        "intent": "intent",
        "evidence": "evidence",
    }
    schema_name = schema_map.get(args.type)
    if schema_name is None:
        print(f"Unknown type: {args.type}", file=sys.stderr)
        return 1

    data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    errors = validate_document(data, schema_name)
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1
    print("OK")
    return 0


def cmd_match(args: argparse.Namespace) -> int:
    registry_path = Path(args.registry)
    intent = Intent.from_file(args.intent)
    registry = Registry.load(registry_path)
    results = match(intent, registry)

    if not results:
        print("No matches.")
        return 0

    for r in results:
        print(
            f"score={r.score:.1f} entity={r.entity_id} "
            f"declaration={r.declaration_id} satisfied={r.satisfied}"
        )
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    from pcl.models import CapabilityDeclaration, Evidence, Intent
    from pcl.verifier import verify_evidence

    evidence = Evidence.from_file(args.evidence)
    intent = Intent.from_file(args.intent) if args.intent else None
    declaration = CapabilityDeclaration.from_file(args.declaration) if args.declaration else None

    result = verify_evidence(evidence, intent=intent, declaration=declaration)
    if result.valid:
        print(f"VERIFIED: integrity={result.integrity} provenance={result.provenance} constraints={result.constraint_satisfaction}")
        return 0
    else:
        print(f"FAILED: integrity={result.integrity} provenance={result.provenance} constraints={result.constraint_satisfaction}", file=sys.stderr)
        for d in result.diagnostics:
            if d.result == "rejected":
                print(f"  - {d.constraint}: {d.reason}", file=sys.stderr)
        return 1


def cmd_resolve_binding(args: argparse.Namespace) -> int:
    from pcl.models import CapabilityDeclaration, Intent

    declaration = CapabilityDeclaration.from_file(args.declaration)
    intent = Intent.from_file(args.intent)
    binding = declaration.execution
    if not binding or not binding.parameters_map:
        print("No parameters_map defined in execution binding.", file=sys.stderr)
        return 1

    resolved = binding.resolve_parameters(inputs=intent.inputs, constraints=intent.constraints)
    print(json.dumps(resolved, indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="pcl", description="PCL reference tools")
    sub = parser.add_subparsers(dest="command", required=True)

    validate_parser = sub.add_parser("validate", help="Validate a PCL document")
    validate_parser.add_argument("type", choices=["entity", "declaration", "offer", "intent", "evidence"])
    validate_parser.add_argument("file")
    validate_parser.set_defaults(func=cmd_validate)

    match_parser = sub.add_parser("match", help="Match an intent against a registry")
    match_parser.add_argument("intent")
    match_parser.add_argument("--registry", default=str(_repo_root() / "registry"))
    match_parser.set_defaults(func=cmd_match)

    verify_parser = sub.add_parser("verify", help="Verify an evidence document against intent and declaration")
    verify_parser.add_argument("evidence")
    verify_parser.add_argument("--intent", default=None)
    verify_parser.add_argument("--declaration", default=None)
    verify_parser.set_defaults(func=cmd_verify)

    resolve_parser = sub.add_parser("resolve-binding", help="Resolve native invocation parameters from declaration and intent")
    resolve_parser.add_argument("--declaration", required=True)
    resolve_parser.add_argument("--intent", required=True)
    resolve_parser.set_defaults(func=cmd_resolve_binding)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
