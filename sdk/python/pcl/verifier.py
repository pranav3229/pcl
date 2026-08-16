"""Deterministic evidence verification, provenance validation, and constraint checking."""

from __future__ import annotations

from typing import Any
from datetime import datetime

from pcl.models import (
    CapabilityDeclaration,
    Comparator,
    ConstraintDiagnostic,
    ConstraintPredicate,
    Evidence,
    Intent,
    OutcomeStatus,
    Quantity,
    Range,
    SetPredicate,
    ValuePredicate,
    VerificationResult,
)


def _evaluate_metric_against_predicate(
    metric_val: Any,
    predicate: ConstraintPredicate,
) -> tuple[bool, str | None]:
    """Evaluate an observed evidence metric against an Intent constraint predicate."""
    if isinstance(predicate, Quantity):
        req_val = predicate.value
        req_unit = predicate.unit
        req_comp = predicate.comparator or Comparator.LTE

        obs_val: float | int
        obs_unit: str | None = None

        if isinstance(metric_val, Quantity):
            obs_val = metric_val.value
            obs_unit = metric_val.unit
        elif isinstance(metric_val, dict) and "value" in metric_val:
            obs_val = metric_val["value"]
            obs_unit = metric_val.get("unit")
        elif isinstance(metric_val, (int, float)):
            obs_val = metric_val
            obs_unit = req_unit
        else:
            return False, f"observed metric '{metric_val}' is not a numeric quantity"

        if req_unit and obs_unit and req_unit != obs_unit:
            return False, f"unit mismatch: required '{req_unit}', observed '{obs_unit}'"

        if req_comp == Comparator.LTE:
            if obs_val <= req_val:
                return True, None
            return False, f"observed value {obs_val} exceeds required maximum {req_val} {req_unit or ''}".strip()
        elif req_comp == Comparator.GTE:
            if obs_val >= req_val:
                return True, None
            return False, f"observed value {obs_val} is below required minimum {req_val} {req_unit or ''}".strip()
        elif req_comp == Comparator.EQ:
            if obs_val == req_val:
                return True, None
            return False, f"observed value {obs_val} does not equal required {req_val} {req_unit or ''}".strip()
        return False, f"unknown comparator '{req_comp}'"

    elif isinstance(predicate, Range):
        min_v = predicate.min
        max_v = predicate.max
        unit = predicate.unit

        obs_val = metric_val.value if isinstance(metric_val, Quantity) else metric_val
        if isinstance(metric_val, dict) and "value" in metric_val:
            obs_val = metric_val["value"]

        if not isinstance(obs_val, (int, float)):
            return False, f"observed metric '{metric_val}' is not numeric for range check"

        if min_v <= obs_val <= max_v:
            return True, None
        return False, f"observed value {obs_val} is outside required range [{min_v}, {max_v}] {unit or ''}".strip()

    elif isinstance(predicate, SetPredicate):
        allowed = predicate.in_values
        val = metric_val
        if isinstance(metric_val, dict) and "value" in metric_val:
            val = metric_val["value"]
        if val in allowed:
            return True, None
        return False, f"observed value '{val}' not in required set {allowed}"

    elif isinstance(predicate, ValuePredicate):
        expected = predicate.value
        val = metric_val
        if isinstance(metric_val, dict) and "value" in metric_val:
            val = metric_val["value"]
        if val == expected:
            return True, None
        return False, f"observed value '{val}' does not match required '{expected}'"

    return False, f"unsupported constraint predicate type: {type(predicate).__name__}"


def verify_provenance(
    evidence: Evidence,
    intent: Intent | None = None,
    declaration: CapabilityDeclaration | None = None,
) -> tuple[bool, list[ConstraintDiagnostic]]:
    """Verify that evidence provenance matches expected Intent, Declaration, and execution instance."""
    diagnostics: list[ConstraintDiagnostic] = []

    if not evidence.execution_id or not evidence.execution_id.strip():
        diagnostics.append(
            ConstraintDiagnostic(
                constraint="provenance.execution_id",
                result="rejected",
                reason="missing execution_id in evidence",
            )
        )

    if intent is not None:
        if evidence.intent_id != intent.id:
            diagnostics.append(
                ConstraintDiagnostic(
                    constraint="provenance.intent_id",
                    result="rejected",
                    reason=f"evidence intent_id '{evidence.intent_id}' does not match expected '{intent.id}'",
                )
            )

    if declaration is not None:
        if evidence.declaration_id != declaration.id:
            diagnostics.append(
                ConstraintDiagnostic(
                    constraint="provenance.declaration_id",
                    result="rejected",
                    reason=f"evidence declaration_id '{evidence.declaration_id}' does not match expected '{declaration.id}'",
                )
            )
        if evidence.entity_id != declaration.entity_id:
            diagnostics.append(
                ConstraintDiagnostic(
                    constraint="provenance.entity_id",
                    result="rejected",
                    reason=f"evidence entity_id '{evidence.entity_id}' does not match declared provider '{declaration.entity_id}'",
                )
            )

        # Check required outputs
        for out in declaration.outputs:
            if getattr(out, "required", False):
                if out.name not in evidence.observed_outputs and out.name not in evidence.observed_metrics:
                    diagnostics.append(
                        ConstraintDiagnostic(
                            constraint=f"output.{out.name}",
                            result="rejected",
                            reason=f"required output '{out.name}' missing from observed evidence",
                        )
                    )

    passed = len(diagnostics) == 0
    return passed, diagnostics


def verify_integrity(
    evidence: Evidence,
    public_keys: dict[str, Any] | None = None,
) -> tuple[bool, list[ConstraintDiagnostic]]:
    """Verify cryptographic signatures of all attestations on this evidence."""
    diagnostics: list[ConstraintDiagnostic] = []
    keys = public_keys or {}

    if not evidence.attestations:
        diagnostics.append(
            ConstraintDiagnostic(
                constraint="attestation",
                result="unverified",
                reason="evidence contains no cryptographic attestations",
            )
        )
        return False, diagnostics

    canonical_bytes = evidence.canonical_bytes()

    for att in evidence.attestations:
        pub_key = keys.get(att.issuer) or att.public_key
        if not pub_key:
            diagnostics.append(
                ConstraintDiagnostic(
                    constraint=f"attestation.{att.issuer}",
                    result="rejected",
                    reason=f"public key for issuer '{att.issuer}' not found",
                )
            )
            continue

        valid = att.verify(canonical_bytes, public_key_override=keys.get(att.issuer))
        if valid:
            diagnostics.append(
                ConstraintDiagnostic(
                    constraint=f"attestation.{att.issuer}",
                    result="satisfied",
                    reason=f"valid {att.algorithm} signature by {att.issuer} ({att.role})",
                )
            )
        else:
            diagnostics.append(
                ConstraintDiagnostic(
                    constraint=f"attestation.{att.issuer}",
                    result="rejected",
                    reason=f"invalid signature by {att.issuer} using algorithm {att.algorithm}",
                )
            )

    has_failures = any(d.result == "rejected" for d in diagnostics)
    passed = not has_failures and any(d.result == "satisfied" for d in diagnostics)
    return passed, diagnostics


def verify_constraints(
    evidence: Evidence,
    intent: Intent,
) -> tuple[bool, list[ConstraintDiagnostic]]:
    """Verify that observed evidence metrics satisfy Intent constraints."""
    diagnostics: list[ConstraintDiagnostic] = []
    all_metrics = {}
    all_metrics.update(evidence.observed_metrics)
    all_metrics.update(evidence.observed_outputs)

    for c_name, predicate in intent.constraints.items():
        if c_name not in all_metrics:
            diagnostics.append(
                ConstraintDiagnostic(
                    constraint=f"constraint.{c_name}",
                    result="rejected",
                    reason=f"required constraint metric '{c_name}' not reported in evidence",
                )
            )
            continue

        obs_val = all_metrics[c_name]
        satisfied, reason = _evaluate_metric_against_predicate(obs_val, predicate)
        if satisfied:
            diagnostics.append(
                ConstraintDiagnostic(
                    constraint=f"constraint.{c_name}",
                    result="satisfied",
                    reason=f"metric '{c_name}' satisfied intent constraint",
                )
            )
        else:
            diagnostics.append(
                ConstraintDiagnostic(
                    constraint=f"constraint.{c_name}",
                    result="rejected",
                    reason=reason or f"metric '{c_name}' violated constraint",
                )
            )

    has_failures = any(d.result == "rejected" for d in diagnostics)
    return not has_failures, diagnostics


def verify_evidence(
    evidence: Evidence,
    intent: Intent | None = None,
    declaration: CapabilityDeclaration | None = None,
    public_keys: dict[str, Any] | None = None,
) -> VerificationResult:
    """Perform deterministic verification of an Evidence document against Intent and Declaration contracts.

    Validates:
    1. Cryptographic integrity of attestations.
    2. Provenance linkage.
    3. Observed metric satisfaction of Intent constraints.
    4. Outcome completion status.
    """
    diagnostics: list[ConstraintDiagnostic] = []

    # 1. Cryptographic Integrity
    integrity_passed, integ_diags = verify_integrity(evidence, public_keys=public_keys)
    diagnostics.extend(integ_diags)
    integrity_status = "verified" if integrity_passed else "failed"

    # 2. Provenance
    provenance_passed, prov_diags = verify_provenance(evidence, intent=intent, declaration=declaration)
    diagnostics.extend(prov_diags)
    provenance_status = "verified" if provenance_passed else "failed"

    # 3. Constraint Satisfaction
    if intent is not None and intent.constraints:
        constraints_passed, constr_diags = verify_constraints(evidence, intent)
        diagnostics.extend(constr_diags)
        constraint_status = "satisfied" if constraints_passed else "failed"
    else:
        constraints_passed = True
        constraint_status = "not_evaluable" if intent is None else "satisfied"

    # 4. Outcome Status Evaluation
    outcome_ok = evidence.outcome in (OutcomeStatus.COMPLETED, OutcomeStatus.PARTIAL)
    if evidence.outcome == OutcomeStatus.FAILED:
        diagnostics.append(
            ConstraintDiagnostic(
                constraint="outcome.status",
                result="rejected",
                reason=f"execution reported failed outcome: {evidence.summary or 'failure'}",
            )
        )
    elif evidence.outcome == OutcomeStatus.CANCELLED:
        diagnostics.append(
            ConstraintDiagnostic(
                constraint="outcome.status",
                result="rejected",
                reason=f"execution was cancelled: {evidence.summary or 'cancelled'}",
            )
        )

    overall_valid = integrity_passed and provenance_passed and constraints_passed and outcome_ok

    return VerificationResult(
        valid=overall_valid,
        integrity=integrity_status,
        provenance=provenance_status,
        constraint_satisfaction=constraint_status,
        outcome=evidence.outcome.value if hasattr(evidence.outcome, "value") else str(evidence.outcome),
        diagnostics=diagnostics,
    )
