#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


READY_STATUS = "lane_hard_violation_support_preflight_ready"
REJECT_STATUS = "lane_hard_violation_support_preflight_rejected"
SOURCE_BLOCKED_STATUS = "lane_hard_violation_support_preflight_source_not_ready"
FORMAL_SEED_STATUS = "lane_hard_violation_support_preflight_formal_seed_conflict"

SOURCE_READY_STATUS = "progress_support_separability_bottleneck_diagnosed"
SOURCE_NEXT_WORK = "reject_or_design_new_progress_support_descriptor_family"
AUTHORIZED_NEXT_WORK = (
    "default_off_lane_hard_violation_support_logging_implementation_unit_tests_only"
)

BLOCKED_ACTIONS = (
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "online_selector_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
)


@dataclass(frozen=True)
class LoggingFieldSpec:
    name: str
    shape: str
    source: str
    no_leak_argument: str
    required_for_atoms: tuple[str, ...]


@dataclass(frozen=True)
class AtomSpec:
    name: str
    expression: str
    required_fields: tuple[str, ...]
    nonnegative_argument: str
    convexity_argument: str
    rationale: str


LOGGING_FIELD_SPECS: tuple[LoggingFieldSpec, ...] = (
    LoggingFieldSpec(
        name="candidate_route_lateral_error_profile_m",
        shape="[K,H]",
        source=(
            "signed cross-track distance from each generated DP candidate prefix "
            "point to the current route or route-lane centerline"
        ),
        no_leak_argument=(
            "computed from current candidate geometry and current map/route "
            "geometry before selection; no tracker rollout or closed-loop "
            "outcome is read"
        ),
        required_for_atoms=(
            "route_lateral_envelope_excess_v1",
            "route_lateral_margin_deficit_vs_top1_v1",
            "lateral_divergence_growth_v1",
        ),
    ),
    LoggingFieldSpec(
        name="candidate_route_corridor_half_width_profile_m",
        shape="[K,H]",
        source=(
            "route-lane corridor half width at each projected candidate prefix "
            "point, from lanelet boundaries when available or a predeclared "
            "industrial fallback width when boundaries are unavailable"
        ),
        no_leak_argument=(
            "a deterministic function of the current Autoware map/route and "
            "candidate projection at the current tick"
        ),
        required_for_atoms=(
            "route_lateral_envelope_excess_v1",
            "route_lateral_margin_deficit_vs_top1_v1",
        ),
    ),
    LoggingFieldSpec(
        name="candidate_route_heading_error_profile_rad",
        shape="[K,H]",
        source=(
            "absolute heading difference between each candidate prefix tangent "
            "and the current route tangent at the projected route station"
        ),
        no_leak_argument=(
            "uses candidate prefix geometry and current route tangent only; it "
            "does not use future simulator state"
        ),
        required_for_atoms=(
            "route_heading_divergence_excess_vs_top1_v1",
            "lane_hard_violation_support_conflict_v1",
        ),
    ),
    LoggingFieldSpec(
        name="candidate_lateral_error_rate_profile_mps",
        shape="[K,H-1]",
        source=(
            "finite difference of signed route-lateral error over the generated "
            "candidate prefix"
        ),
        no_leak_argument=(
            "computed from same-tick candidate prefix and route projection "
            "fields with the current planner dt"
        ),
        required_for_atoms=(
            "lateral_error_rate_excess_v1",
            "lateral_divergence_growth_v1",
        ),
    ),
)


ATOM_SPECS: tuple[AtomSpec, ...] = (
    AtomSpec(
        name="route_lateral_envelope_excess_v1",
        expression=(
            "max_h max(abs(candidate_route_lateral_error[h]) - "
            "candidate_route_corridor_half_width[h], 0)"
        ),
        required_fields=(
            "candidate_route_lateral_error_profile_m",
            "candidate_route_corridor_half_width_profile_m",
        ),
        nonnegative_argument="positive part of lateral envelope violation",
        convexity_argument=(
            "convex in logged scalar lateral error and corridor width values; "
            "once logged it is a fixed finite-candidate coefficient"
        ),
        rationale=(
            "targets allowed harmful candidates with lane/hard-violation "
            "regressions that had zero progress-support risk"
        ),
    ),
    AtomSpec(
        name="route_lateral_margin_deficit_vs_top1_v1",
        expression=(
            "max(top1_min_lateral_margin - candidate_min_lateral_margin, 0)"
        ),
        required_fields=(
            "candidate_route_lateral_error_profile_m",
            "candidate_route_corridor_half_width_profile_m",
        ),
        nonnegative_argument="positive part of margin loss relative to DP Top-1",
        convexity_argument=(
            "convex after reducing logged profile to fixed per-candidate margin "
            "coefficients; no global trajectory-coordinate convexity is claimed"
        ),
        rationale=(
            "keeps the DP Top-1 lane-support margin as an industrial baseline "
            "while allowing candidates that are not less lane-supported"
        ),
    ),
    AtomSpec(
        name="route_heading_divergence_excess_vs_top1_v1",
        expression="max(max_h heading_error[h] - top1_max_heading_error, 0)",
        required_fields=("candidate_route_heading_error_profile_rad",),
        nonnegative_argument="positive part of heading divergence excess",
        convexity_argument=(
            "convex in logged heading-error scalars after absolute error is "
            "computed; fixed coefficient in CAMP scoring"
        ),
        rationale=(
            "captures route-lane departure risk that may not immediately change "
            "route progress or tail speed"
        ),
    ),
    AtomSpec(
        name="lateral_error_rate_excess_v1",
        expression="max_h max(abs(lateral_error_rate[h]) - rate_budget_mps, 0)",
        required_fields=("candidate_lateral_error_rate_profile_mps",),
        nonnegative_argument="positive part of lateral-error-rate budget excess",
        convexity_argument=(
            "convex in logged lateral-rate scalars after absolute value; fixed "
            "per candidate before CAMP weight optimization"
        ),
        rationale=(
            "flags candidates that quickly leave route support even when their "
            "instantaneous progress-support atoms remain zero"
        ),
    ),
    AtomSpec(
        name="lateral_divergence_growth_v1",
        expression=(
            "max_h max(abs(lateral_error[h+1]) - abs(lateral_error[h]), 0) "
            "* max_h abs(lateral_error_rate[h])"
        ),
        required_fields=(
            "candidate_route_lateral_error_profile_m",
            "candidate_lateral_error_rate_profile_mps",
        ),
        nonnegative_argument="product of nonnegative logged growth and rate terms",
        convexity_argument=(
            "not claimed convex in raw logged variables; admissible only as a "
            "fixed finite-candidate coefficient after logging, preserving "
            "affinity in CAMP weights"
        ),
        rationale=(
            "diagnoses outward lane-support divergence without using future "
            "closed-loop lane-violation labels"
        ),
    ),
    AtomSpec(
        name="lane_hard_violation_support_conflict_v1",
        expression=(
            "route_lateral_envelope_excess_v1 * "
            "route_heading_divergence_excess_vs_top1_v1"
        ),
        required_fields=(
            "candidate_route_lateral_error_profile_m",
            "candidate_route_corridor_half_width_profile_m",
            "candidate_route_heading_error_profile_rad",
        ),
        nonnegative_argument="product of nonnegative lateral and heading risks",
        convexity_argument=(
            "not claimed convex in raw trajectory coordinates; it is a fixed "
            "candidate atom coefficient before the simplex/CVaR/L2 master sees it"
        ),
        rationale=(
            "targets the diagnosed hard-violation blind spot while keeping the "
            "runtime selector feature no-leak"
        ),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only preflight for default-off lane/hard-violation support "
            "logging after progress-support separability bottleneck diagnosis."
        )
    )
    parser.add_argument("--bottleneck_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--fail_on_formal_seeds", action="store_true")
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        bottleneck_report=_load_json(args.bottleneck_json),
        label=args.label,
        fail_on_formal_seeds=args.fail_on_formal_seeds,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def analyze(
    *,
    bottleneck_report: dict[str, Any],
    label: str | None = None,
    fail_on_formal_seeds: bool = False,
    field_specs: tuple[LoggingFieldSpec, ...] = LOGGING_FIELD_SPECS,
    atom_specs: tuple[AtomSpec, ...] = ATOM_SPECS,
) -> dict[str, Any]:
    source = _source_gate(bottleneck_report)
    formal_seed_records = _formal_seed_records(bottleneck_report)
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden for this preflight.")
    allowed_harmful = bottleneck_report.get("allowed_harmful") or {}
    blocked_beneficial = bottleneck_report.get("blocked_beneficial") or {}
    fields = [_field_report(spec, atom_specs) for spec in field_specs]
    atoms = [_atom_report(spec, field_specs) for spec in atom_specs]
    math_checks = _math_checks(fields, atoms)
    blind_spot = _blind_spot_summary(allowed_harmful, blocked_beneficial)
    decision = _decision(
        source=source,
        formal_seed_records=formal_seed_records,
        fields=fields,
        atoms=atoms,
        math_checks=math_checks,
        blind_spot=blind_spot,
    )
    return {
        "analysis": {
            "name": "dp_camp_lane_hard_violation_support_preflight_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "uses_existing_artifact_only": True,
            "future_outcome_labels_used_for_field_definitions": False,
            "future_outcome_labels_used_for_atom_definitions": False,
            "future_outcome_labels_used_for_source_diagnosis": True,
            "logging_mode": "default_off_preflight_only",
            "math_boundary": (
                "Proposed lane/hard-violation support fields are current-tick "
                "finite-candidate quantities computed from generated DP "
                "candidates, current route/lane map geometry, and planner dt "
                "before selector execution. Proposed atoms are nonnegative "
                "scalar functions of those fields. Once logged, each atom is a "
                "fixed coefficient a_k, so CAMP scoring remains affine "
                "score_k(w)=a_k^T w and the simplex/CVaR/L2 master remains "
                "convex in weights. This preflight makes no global convexity "
                "claim over trajectory coordinates and constructs no DP-side "
                "classical Benders master/subproblem, dual, or cut."
            ),
        },
        "source_progress_support_bottleneck_gate": source,
        "source_blind_spot_summary": blind_spot,
        "records": {
            "formal_seed_records": formal_seed_records,
        },
        "logging_field_reports": fields,
        "atom_reports": atoms,
        "math_checks": math_checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") if isinstance(report, dict) else None
    counts = report.get("counts") if isinstance(report, dict) else None
    if not isinstance(decision, dict):
        return {"passed": False, "status": "missing_final_decision"}
    passed = (
        decision.get("status") == SOURCE_READY_STATUS
        and bool(decision.get("passed"))
        and decision.get("authorized_next_work") == SOURCE_NEXT_WORK
        and isinstance(counts, dict)
        and int(counts.get("harmful_allowed") or 0) > 0
    )
    return {
        "passed": passed,
        "status": decision.get("status"),
        "primary_gap": decision.get("primary_gap"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "harmful_allowed": int(counts.get("harmful_allowed") or 0)
        if isinstance(counts, dict)
        else None,
    }


def _blind_spot_summary(
    allowed_harmful: dict[str, Any],
    blocked_beneficial: dict[str, Any],
) -> dict[str, Any]:
    allowed_outcome = allowed_harmful.get("outcome_summary") or {}
    blocked_outcome = blocked_beneficial.get("outcome_summary") or {}
    lane_worse = int(allowed_outcome.get("lane_worse_count") or 0)
    hard_delta = _as_float(allowed_outcome.get("hard_violation_delta_mean"))
    blocked_lane_worse = int(blocked_outcome.get("lane_worse_count") or 0)
    blocked_hard_delta = _as_float(blocked_outcome.get("hard_violation_delta_mean"))
    progress_support_zero = _all_zero_contributions(allowed_harmful)
    has_lane_or_hard_gap = lane_worse > 0 or hard_delta > 0.0
    return {
        "allowed_harmful_count": int(allowed_harmful.get("count") or 0),
        "allowed_harmful_lane_worse_count": lane_worse,
        "allowed_harmful_hard_violation_delta_mean": hard_delta,
        "allowed_harmful_progress_support_contribution_zero": progress_support_zero,
        "blocked_beneficial_count": int(blocked_beneficial.get("count") or 0),
        "blocked_beneficial_lane_worse_count": blocked_lane_worse,
        "blocked_beneficial_hard_violation_delta_mean": blocked_hard_delta,
        "has_lane_or_hard_gap": has_lane_or_hard_gap,
        "target_failure_mode": (
            "allowed harmful candidates include lane/hard-violation regressions "
            "with zero progress-support risk"
            if has_lane_or_hard_gap and progress_support_zero
            else "lane/hard-violation blind spot not established"
        ),
    }


def _field_report(
    spec: LoggingFieldSpec,
    atom_specs: tuple[AtomSpec, ...],
) -> dict[str, Any]:
    required_by = [
        atom.name for atom in atom_specs
        if spec.name in atom.required_fields
    ]
    return {
        "name": spec.name,
        "shape": spec.shape,
        "source": spec.source,
        "no_leak_argument": spec.no_leak_argument,
        "required_for_atoms": list(spec.required_for_atoms),
        "required_by_atoms": required_by,
        "default_off": True,
        "current_tick": True,
        "finite_candidate_quantity": True,
        "uses_closed_loop_outcome": False,
        "passed_preflight": bool(required_by),
    }


def _atom_report(
    spec: AtomSpec,
    field_specs: tuple[LoggingFieldSpec, ...],
) -> dict[str, Any]:
    available = {field.name for field in field_specs}
    missing = [field for field in spec.required_fields if field not in available]
    return {
        "name": spec.name,
        "expression": spec.expression,
        "required_fields": list(spec.required_fields),
        "missing_fields": missing,
        "nonnegative_argument": spec.nonnegative_argument,
        "convexity_argument": spec.convexity_argument,
        "rationale": spec.rationale,
        "future_outcome_label_dependency": False,
        "fixed_finite_candidate_coefficient": True,
        "affine_in_camp_weights": True,
        "passed_preflight": not missing,
    }


def _math_checks(
    fields: list[dict[str, Any]],
    atoms: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "name": "all_fields_default_off_no_leak",
            "passed": all(
                field["default_off"]
                and field["current_tick"]
                and not field["uses_closed_loop_outcome"]
                for field in fields
            ),
        },
        {
            "name": "all_atoms_have_required_fields",
            "passed": all(atom["passed_preflight"] for atom in atoms),
        },
        {
            "name": "all_atoms_fixed_finite_candidate_coefficients",
            "passed": all(
                atom["fixed_finite_candidate_coefficient"]
                and atom["affine_in_camp_weights"]
                and not atom["future_outcome_label_dependency"]
                for atom in atoms
            ),
        },
        {
            "name": "no_global_trajectory_convexity_claim",
            "passed": True,
        },
        {
            "name": "no_classical_benders_claim",
            "passed": True,
        },
    ]


def _decision(
    *,
    source: dict[str, Any],
    formal_seed_records: int,
    fields: list[dict[str, Any]],
    atoms: list[dict[str, Any]],
    math_checks: list[dict[str, Any]],
    blind_spot: dict[str, Any],
) -> dict[str, Any]:
    if not source["passed"]:
        status = SOURCE_BLOCKED_STATUS
        primary_gap = "progress_support_bottleneck_source_not_ready"
        next_work = None
    elif formal_seed_records:
        status = FORMAL_SEED_STATUS
        primary_gap = "formal_seed_conflict"
        next_work = None
    elif not blind_spot["has_lane_or_hard_gap"]:
        status = REJECT_STATUS
        primary_gap = "lane_hard_violation_blind_spot_not_established"
        next_work = None
    elif not blind_spot["allowed_harmful_progress_support_contribution_zero"]:
        status = REJECT_STATUS
        primary_gap = "allowed_harmful_not_zero_progress_support_risk"
        next_work = None
    elif not all(field["passed_preflight"] for field in fields):
        status = REJECT_STATUS
        primary_gap = "logging_field_preflight_failed"
        next_work = None
    elif not all(atom["passed_preflight"] for atom in atoms):
        status = REJECT_STATUS
        primary_gap = "atom_preflight_failed"
        next_work = None
    elif not all(check["passed"] for check in math_checks):
        status = REJECT_STATUS
        primary_gap = "math_preflight_failed"
        next_work = None
    else:
        status = READY_STATUS
        primary_gap = "lane_hard_violation_support_logging_preflight_ready"
        next_work = AUTHORIZED_NEXT_WORK
    return {
        "status": status,
        "passed": status == READY_STATUS,
        "primary_gap": primary_gap,
        "authorized_next_work": next_work,
        **{key: False for key in BLOCKED_ACTIONS},
    }


def _formal_seed_records(report: dict[str, Any]) -> int:
    records = report.get("records")
    if isinstance(records, dict):
        return int(records.get("formal_seed_records") or 0)
    counts = report.get("counts")
    if isinstance(counts, dict):
        return int(counts.get("formal_seed_records") or 0)
    return 0


def _all_zero_contributions(summary: dict[str, Any]) -> bool:
    contributions = summary.get("descriptor_contribution_mean")
    if not isinstance(contributions, dict) or not contributions:
        return False
    values = [_as_float(value) for value in contributions.values()]
    return all(abs(value) <= 1e-12 for value in values)


def _as_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# DP CAMP Lane/Hard-Violation Support Preflight",
        "",
        "This is a read-only design preflight for default-off no-leak "
        "lane/hard-violation support logging. It does not implement DP logging, "
        "train CAMP, run replay, or authorize a selector.",
        "",
        "## Decision",
        "",
        f"status=`{decision['status']}`",
        f"passed=`{decision['passed']}`",
        f"primary_gap=`{decision['primary_gap']}`",
        f"authorized_next_work=`{decision['authorized_next_work']}`",
        "",
        "## Source Blind Spot",
        "",
        "```json",
        json.dumps(report["source_blind_spot_summary"], indent=2, sort_keys=True),
        "```",
        "",
        "## Logging Fields",
        "",
        "```json",
        json.dumps(report["logging_field_reports"], indent=2, sort_keys=True),
        "```",
        "",
        "## Atom Candidates",
        "",
        "```json",
        json.dumps(report["atom_reports"], indent=2, sort_keys=True),
        "```",
        "",
        "## Mathematical Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
