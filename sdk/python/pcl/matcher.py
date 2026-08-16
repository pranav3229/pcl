from __future__ import annotations

from datetime import datetime, timezone

from pcl.models import (
    CapabilityDeclaration,
    CapabilityOffer,
    Comparator,
    ConstraintDiagnostic,
    ConstraintPredicate,
    ConstraintSpec,
    IORole,
    Intent,
    Location,
    MatchResult,
    Quantity,
    Range,
    RuntimeStatus,
    SemanticRef,
    SetPredicate,
    ValuePredicate,
    haversine_distance,
)
from pcl.registry import Registry

BLOCKED_STATES = {RuntimeStatus.OFFLINE, RuntimeStatus.MAINTENANCE, RuntimeStatus.FAULT}


def goal_matches(intent_goal: SemanticRef, capability_type: SemanticRef) -> bool:
    return intent_goal.matches(capability_type)


def inputs_compatible(intent: Intent, declaration: CapabilityDeclaration) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    for io in declaration.inputs:
        if not io.required:
            continue
        if io.name not in intent.inputs:
            reasons.append(f"missing required input: {io.name}")
            continue
        value = intent.inputs[io.name]
        if value.ref is None and value.value is None and value.quantity is None:
            reasons.append(f"empty input: {io.name}")
    return len(reasons) == 0, reasons


def outputs_compatible(intent: Intent, declaration: CapabilityDeclaration) -> tuple[bool, list[str]]:
    if not intent.required_outputs:
        return True, []
    declared = {o.name: o for o in declaration.outputs}
    reasons: list[str] = []
    for name in intent.required_outputs:
        if name not in declared:
            reasons.append(f"missing required output: {name}")
    return len(reasons) == 0, reasons


def _quantity_vs_quantity(
    name: str,
    intent_q: Quantity,
    cap_q: Quantity,
) -> tuple[bool, str | None]:
    if intent_q.unit != cap_q.unit:
        return False, f"unit mismatch for '{name}': provider uses '{cap_q.unit}' but intent requires '{intent_q.unit}'"

    i_comp = intent_q.comparator
    c_comp = cap_q.comparator
    i_val = intent_q.value
    c_val = cap_q.value

    if i_comp == Comparator.LTE:
        if c_comp in (Comparator.LTE, Comparator.EQ):
            if c_val >= i_val:
                return True, None
            return False, f"provider maximum {name} ({c_val} {cap_q.unit}) is less than required {i_val} {intent_q.unit}"
        elif c_comp == Comparator.LT:
            if c_val > i_val:
                return True, None
            return False, f"provider limit {name} (< {c_val} {cap_q.unit}) cannot satisfy {i_val} {intent_q.unit}"
        elif c_comp in (Comparator.GTE, Comparator.GT):
            return False, f"provider minimum constraint on '{name}' cannot satisfy upper limit requirement"

    elif i_comp == Comparator.LT:
        if c_comp in (Comparator.LTE, Comparator.EQ, Comparator.LT):
            if c_val >= i_val:
                return True, None
            return False, f"provider limit {name} ({c_val} {cap_q.unit}) is less than required {i_val} {intent_q.unit}"
        return False, f"incompatible comparators for '{name}'"

    elif i_comp == Comparator.GTE:
        if c_comp in (Comparator.GTE, Comparator.GT):
            if c_val <= i_val:
                return True, None
            return False, f"provider minimum limit {name} ({c_val} {cap_q.unit}) cannot satisfy required {i_val} {intent_q.unit}"
        elif c_comp in (Comparator.LTE, Comparator.EQ):
            if c_val >= i_val:
                return True, None
            return False, f"provider capacity {name} ({c_val} {cap_q.unit}) is less than required minimum {i_val} {intent_q.unit}"

    elif i_comp == Comparator.GT:
        if c_comp in (Comparator.GTE, Comparator.GT):
            if c_val <= i_val:
                return True, None
            return False, f"provider limit {name} ({c_val} {cap_q.unit}) cannot satisfy > {i_val} {intent_q.unit}"
        elif c_comp in (Comparator.LTE, Comparator.EQ):
            if c_val > i_val:
                return True, None
            return False, f"provider capacity {name} ({c_val} {cap_q.unit}) does not exceed required minimum {i_val} {intent_q.unit}"

    elif i_comp == Comparator.EQ:
        if c_comp == Comparator.EQ:
            if c_val == i_val:
                return True, None
            return False, f"provider value {name} ({c_val} {cap_q.unit}) does not equal required {i_val} {intent_q.unit}"
        elif c_comp == Comparator.LTE:
            if c_val >= i_val:
                return True, None
            return False, f"provider maximum {name} ({c_val} {cap_q.unit}) is less than required {i_val} {intent_q.unit}"
        elif c_comp == Comparator.GTE:
            if c_val <= i_val:
                return True, None
            return False, f"provider minimum {name} ({c_val} {cap_q.unit}) exceeds required {i_val} {intent_q.unit}"

    return False, f"constraint not satisfied for '{name}'"


def _quantity_vs_range(
    name: str,
    intent_q: Quantity,
    cap_r: Range,
) -> tuple[bool, str | None]:
    if intent_q.unit and cap_r.unit and intent_q.unit != cap_r.unit:
        return False, f"unit mismatch for '{name}': provider uses '{cap_r.unit}' but intent requires '{intent_q.unit}'"

    i_val = intent_q.value
    if intent_q.comparator == Comparator.EQ:
        if cap_r.min <= i_val <= cap_r.max:
            return True, None
        return False, f"intent value {i_val} for '{name}' is outside provider range [{cap_r.min}, {cap_r.max}]"
    elif intent_q.comparator in (Comparator.LTE, Comparator.LT):
        if i_val <= cap_r.max:
            return True, None
        return False, f"intent upper limit {i_val} for '{name}' exceeds provider maximum {cap_r.max}"
    elif intent_q.comparator in (Comparator.GTE, Comparator.GT):
        if i_val >= cap_r.min:
            return True, None
        return False, f"intent lower limit {i_val} for '{name}' is below provider minimum {cap_r.min}"

    return False, f"constraint '{name}' not satisfied against provider range"


def _range_vs_range(
    name: str,
    intent_r: Range,
    cap_r: Range,
) -> tuple[bool, str | None]:
    if intent_r.unit and cap_r.unit and intent_r.unit != cap_r.unit:
        return False, f"unit mismatch for '{name}': provider uses '{cap_r.unit}' but intent requires '{intent_r.unit}'"

    if cap_r.min <= intent_r.min and intent_r.max <= cap_r.max:
        return True, None

    if cap_r.min > intent_r.min:
        return False, f"provider range minimum ({cap_r.min}) for '{name}' exceeds intent minimum ({intent_r.min})"
    if cap_r.max < intent_r.max:
        return False, f"provider range maximum ({cap_r.max}) for '{name}' is less than intent maximum ({intent_r.max})"

    return False, f"intent range [{intent_r.min}, {intent_r.max}] is not fully contained in provider range [{cap_r.min}, {cap_r.max}]"


def _range_vs_quantity(
    name: str,
    intent_r: Range,
    cap_q: Quantity,
) -> tuple[bool, str | None]:
    if intent_r.unit and cap_q.unit and intent_r.unit != cap_q.unit:
        return False, f"unit mismatch for '{name}': provider uses '{cap_q.unit}' but intent requires '{intent_r.unit}'"

    if cap_q.comparator == Comparator.LTE:
        if intent_r.max <= cap_q.value:
            return True, None
        return False, f"intent maximum ({intent_r.max}) for '{name}' exceeds provider limit ({cap_q.value})"
    elif cap_q.comparator == Comparator.GTE:
        if intent_r.min >= cap_q.value:
            return True, None
        return False, f"intent minimum ({intent_r.min}) for '{name}' is below provider limit ({cap_q.value})"

    return False, f"intent range for '{name}' cannot be satisfied by provider scalar quantity"


def _evaluate_constraint(
    name: str,
    intent_pred: ConstraintPredicate,
    cap_spec: ConstraintSpec,
) -> tuple[bool, str | None]:
    if isinstance(intent_pred, Quantity):
        if cap_spec.quantity is not None:
            return _quantity_vs_quantity(name, intent_pred, cap_spec.quantity)
        elif cap_spec.range is not None:
            return _quantity_vs_range(name, intent_pred, cap_spec.range)
        else:
            return False, f"provider constraint '{name}' is not a quantitative limit or range"

    elif isinstance(intent_pred, Range):
        if cap_spec.range is not None:
            return _range_vs_range(name, intent_pred, cap_spec.range)
        elif cap_spec.quantity is not None:
            return _range_vs_quantity(name, intent_pred, cap_spec.quantity)
        else:
            return False, f"provider constraint '{name}' does not specify a supported range"

    elif isinstance(intent_pred, SetPredicate):
        intent_set = set(intent_pred.in_values)
        if cap_spec.in_values is not None:
            provider_set = set(cap_spec.in_values)
            if intent_set.intersection(provider_set):
                return True, None
            return False, f"no overlap between provider supported set {list(cap_spec.in_values)} and intent acceptable set {list(intent_pred.in_values)}"
        elif cap_spec.value is not None:
            if cap_spec.value in intent_set:
                return True, None
            return False, f"provider value '{cap_spec.value}' is not in intent acceptable set {list(intent_pred.in_values)}"
        else:
            return False, f"provider constraint '{name}' does not specify a value or supported set"

    elif isinstance(intent_pred, ValuePredicate):
        req_val = intent_pred.value
        if cap_spec.value is not None:
            if cap_spec.value == req_val:
                return True, None
            return False, f"provider value '{cap_spec.value}' does not match required value '{req_val}'"
        elif cap_spec.in_values is not None:
            if req_val in cap_spec.in_values:
                return True, None
            return False, f"required value '{req_val}' is not in provider supported set {list(cap_spec.in_values)}"
        elif cap_spec.range is not None and isinstance(req_val, (int, float)):
            if cap_spec.range.min <= req_val <= cap_spec.range.max:
                return True, None
            return False, f"intent value {req_val} is outside provider range [{cap_spec.range.min}, {cap_spec.range.max}]"
        else:
            return False, f"provider constraint '{name}' does not specify matching value or options"

    return False, f"unsupported intent constraint format for '{name}'"


def constraints_satisfied(
    intent: Intent, declaration: CapabilityDeclaration
) -> tuple[bool, list[str], list[ConstraintDiagnostic]]:
    reasons: list[str] = []
    diagnostics: list[ConstraintDiagnostic] = []

    for name, intent_pred in intent.constraints.items():
        cap_constraint = declaration.constraint_by_name(name)
        if cap_constraint is None:
            reason = f"capability missing constraint: {name}"
            reasons.append(reason)
            diagnostics.append(
                ConstraintDiagnostic(constraint=name, result="rejected", reason=reason)
            )
            continue

        ok, fail_reason = _evaluate_constraint(name, intent_pred, cap_constraint)
        if ok:
            diagnostics.append(
                ConstraintDiagnostic(constraint=name, result="satisfied", reason=None)
            )
        else:
            reason = fail_reason or f"constraint not satisfied: {name}"
            reasons.append(reason)
            diagnostics.append(
                ConstraintDiagnostic(constraint=name, result="rejected", reason=reason)
            )

    return len(reasons) == 0, reasons, diagnostics


def _extract_intent_origin_location(
    intent: Intent, declaration: CapabilityDeclaration
) -> Location | None:
    """Extract required origin/location from intent inputs if present."""
    target_input_names = {"origin", "location"}
    for io in declaration.inputs:
        if io.role == IORole.ORIGIN or io.name in target_input_names:
            target_input_names.add(io.name)

    for name in target_input_names:
        if name in intent.inputs:
            input_val = intent.inputs[name]
            if isinstance(input_val.value, Location):
                return input_val.value
            elif isinstance(input_val.value, dict) and "kind" in input_val.value:
                return Location.model_validate(input_val.value)
            elif input_val.ref is not None:
                return Location(kind="semantic", ref=input_val.ref)

    return None


def _extract_spatial_tolerance_km(intent: Intent) -> float:
    """Extract location tolerance in km from intent constraints if present."""
    if "location_tolerance" in intent.constraints:
        c = intent.constraints["location_tolerance"]
        if isinstance(c, Quantity):
            if c.unit == "km":
                return c.value
            elif c.unit == "m":
                return c.value / 1000.0
    if "max_distance" in intent.constraints:
        c = intent.constraints["max_distance"]
        if isinstance(c, Quantity):
            if c.unit == "km":
                return c.value
            elif c.unit == "m":
                return c.value / 1000.0
    return 0.0


def location_allows(
    offer: CapabilityOffer,
    declaration: CapabilityDeclaration,
    intent: Intent,
) -> tuple[bool, list[str], list[ConstraintDiagnostic]]:
    diagnostics: list[ConstraintDiagnostic] = []

    # If the Offer provides no specific location anchor, location gating passes
    if offer.location is None:
        return True, [], diagnostics

    intent_origin = _extract_intent_origin_location(intent, declaration)

    # If the Intent expresses no spatial origin requirement, location gating passes
    if intent_origin is None:
        return True, [], diagnostics

    tolerance_km = _extract_spatial_tolerance_km(intent)

    if offer.location.matches(intent_origin, tolerance_km=tolerance_km):
        diagnostics.append(
            ConstraintDiagnostic(
                constraint="location",
                result="satisfied",
                reason=None,
            )
        )
        return True, [], diagnostics

    # Generate descriptive rejection diagnostic
    if offer.location.kind != intent_origin.kind:
        reason = f"location kind mismatch: offer uses '{offer.location.kind}' but intent requires '{intent_origin.kind}'"
    elif offer.location.kind == "semantic":
        reason = f"offer location '{offer.location.ref}' does not match requested origin '{intent_origin.ref}'"
    elif offer.location.kind == "coordinates":
        if offer.location.lat is not None and offer.location.lon is not None and intent_origin.lat is not None and intent_origin.lon is not None:
            dist = haversine_distance(offer.location.lat, offer.location.lon, intent_origin.lat, intent_origin.lon)
            reason = f"offer is {dist:.1f} km from requested origin; tolerance is {tolerance_km:.1f} km"
        else:
            reason = "missing coordinate values on offer or intent origin"
    else:
        reason = "offer location does not match requested origin"

    diagnostics.append(
        ConstraintDiagnostic(
            constraint="location",
            result="rejected",
            reason=reason,
        )
    )
    return False, [f"location: {reason}"], diagnostics


def state_allows(offer: CapabilityOffer) -> tuple[bool, list[str]]:
    if offer.state.status in BLOCKED_STATES:
        return False, [f"blocked state: {offer.state.status.value}"]
    return True, []


def _parse_datetime(dt_str: str) -> datetime:
    """Parse ISO 8601 datetime string to UTC-aware datetime."""
    normalized = dt_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def availability_allows(
    offer: CapabilityOffer,
    evaluation_time: datetime | str | None = None,
) -> tuple[bool, list[str], list[ConstraintDiagnostic]]:
    diagnostics: list[ConstraintDiagnostic] = []

    if not offer.availability.accepts_work:
        reason = offer.availability.reason or "offer does not currently accept work"
        diagnostics.append(
            ConstraintDiagnostic(
                constraint="availability.accepts_work",
                result="rejected",
                reason=reason,
            )
        )
        return False, [f"availability: {reason}"], diagnostics

    if offer.availability.valid_until:
        if evaluation_time is None:
            eval_dt = datetime.now(timezone.utc)
        elif isinstance(evaluation_time, str):
            eval_dt = _parse_datetime(evaluation_time)
        elif isinstance(evaluation_time, datetime):
            eval_dt = evaluation_time if evaluation_time.tzinfo else evaluation_time.replace(tzinfo=timezone.utc)
            eval_dt = eval_dt.astimezone(timezone.utc)
        else:
            eval_dt = datetime.now(timezone.utc)

        valid_dt = _parse_datetime(offer.availability.valid_until)

        if eval_dt > valid_dt:
            reason = f"offer expired at {offer.availability.valid_until}"
            diagnostics.append(
                ConstraintDiagnostic(
                    constraint="availability.valid_until",
                    result="rejected",
                    reason=reason,
                )
            )
            return False, [f"availability: {reason}"], diagnostics
        else:
            diagnostics.append(
                ConstraintDiagnostic(
                    constraint="availability.valid_until",
                    result="satisfied",
                    reason=None,
                )
            )

    return True, [], diagnostics


def compute_score(
    intent: Intent,
    offer: CapabilityOffer,
    satisfied: list[str],
    unsatisfied: list[str],
) -> float:
    score = 100.0 - (10.0 * len(unsatisfied))
    if intent.preferences and intent.preferences.provider_id:
        if intent.preferences.provider_id == offer.entity_id:
            score += 1000.0
    score += len(satisfied) * 0.1
    return score


def match_intent_to_offer(
    intent: Intent,
    offer: CapabilityOffer,
    declaration: CapabilityDeclaration,
    evaluation_time: datetime | str | None = None,
) -> MatchResult | None:
    satisfied: list[str] = []
    unsatisfied: list[str] = []
    all_diagnostics: list[ConstraintDiagnostic] = []

    if not goal_matches(intent.goal, declaration.semantic_type):
        return None
    satisfied.append("goal")

    ok, reasons = inputs_compatible(intent, declaration)
    if not ok:
        return None
    satisfied.append("inputs")

    ok, reasons = outputs_compatible(intent, declaration)
    if not ok:
        return None
    if intent.required_outputs:
        satisfied.append("outputs")

    ok, reasons, diag = constraints_satisfied(intent, declaration)
    all_diagnostics.extend(diag)
    if not ok:
        return None
    satisfied.append("constraints")

    ok, reasons, diag = location_allows(offer, declaration, intent)
    all_diagnostics.extend(diag)
    if not ok:
        return None
    if diag:
        satisfied.append("location")

    ok, reasons = state_allows(offer)
    if not ok:
        return None
    satisfied.append("state")

    ok, reasons, diag = availability_allows(offer, evaluation_time=evaluation_time)
    all_diagnostics.extend(diag)
    if not ok:
        return None
    satisfied.append("availability")

    score = compute_score(intent, offer, satisfied, unsatisfied)

    return MatchResult(
        declaration_id=declaration.id,
        entity_id=offer.entity_id,
        offer_id=offer.offer_id,
        score=score,
        satisfied=satisfied,
        unsatisfied=unsatisfied,
        diagnostics=all_diagnostics,
        offer=offer,
        declaration=declaration,
    )


def match(
    intent: Intent,
    registry: Registry,
    evaluation_time: datetime | str | None = None,
) -> list[MatchResult]:
    """Match an intent against all offers in the registry."""
    results: list[MatchResult] = []
    for offer in registry.offers:
        declaration = registry.get_declaration_for_offer(offer)
        if declaration is None:
            continue
        result = match_intent_to_offer(intent, offer, declaration, evaluation_time=evaluation_time)
        if result is not None:
            results.append(result)

    results.sort(key=lambda r: (-r.score, r.entity_id))
    return results
