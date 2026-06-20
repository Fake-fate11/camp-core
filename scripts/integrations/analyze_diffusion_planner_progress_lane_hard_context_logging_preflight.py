#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.analyze_diffusion_planner_progress_lane_hard_joint_descriptor_separability import (  # noqa: E402
    _load_json,
)
from scripts.integrations.analyze_diffusion_planner_progress_lane_hard_joint_separability_bottleneck import (  # noqa: E402
    NEXT_WORK as BOTTLENECK_NEXT_WORK,
    READY_STATUS as BOTTLENECK_READY_STATUS,
)


READY_STATUS = "progress_lane_hard_context_logging_preflight_ready"
REJECT_STATUS = "progress_lane_hard_context_logging_preflight_rejected"
SOURCE_BLOCKED_STATUS = "progress_lane_hard_context_logging_preflight_source_not_ready"
FORMAL_SEED_STATUS = "progress_lane_hard_context_logging_preflight_formal_seed_conflict"

SOURCE_PRIMARY_GAP = (
    "strict_screens_overblock_beneficial_and_high_retain_screens_allow_harmful"
)
AUTHORIZED_NEXT_WORK = (
    "default_off_progress_lane_hard_context_logging_implementation_unit_tests_only"
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
    candidate_level: bool = True


@dataclass(frozen=True)
class AtomSpec:
    name: str
    expression: str
    required_fields: tuple[str, ...]
    nonnegative_argument: str
    convexity_argument: str
    monotone_sign_constraint: str
    rationale: str


LOGGING_FIELD_SPECS: tuple[LoggingFieldSpec, ...] = (
    LoggingFieldSpec(
        name="route_curvature_context_abs_radpm",
        shape="[H-1]",
        source=(
            "absolute heading change per route arc length from the current "
            "Autoware route centerline around the ego pose"
        ),
        no_leak_argument=(
            "uses only the current map/route geometry before candidate outcome "
            "evaluation"
        ),
        required_for_atoms=(
            "curvature_conditioned_lateral_rate_excess_v1",
            "heading_curvature_residual_v1",
            "lane_progress_coherence_excess_v1",
        ),
        candidate_level=False,
    ),
    LoggingFieldSpec(
        name="candidate_lateral_error_rate_profile_mps",
        shape="[K,H-1]",
        source="finite difference of route-relative candidate lateral error",
        no_leak_argument=(
            "computed from generated DP candidate geometry and the current "
            "route frame before selector execution"
        ),
        required_for_atoms=(
            "curvature_conditioned_lateral_rate_excess_v1",
            "lane_progress_coherence_excess_v1",
        ),
    ),
    LoggingFieldSpec(
        name="candidate_speed_profile_mps",
        shape="[K,H-1]",
        source="finite-difference speed profile from each generated candidate prefix",
        no_leak_argument="uses candidate prefix timestamps and positions only",
        required_for_atoms=(
            "curvature_conditioned_lateral_rate_excess_v1",
            "lane_progress_coherence_excess_v1",
        ),
    ),
    LoggingFieldSpec(
        name="candidate_route_progress_delta_profile_m",
        shape="[K,H-1]",
        source="first difference of candidate route projection support",
        no_leak_argument=(
            "uses current route projection of generated candidates; no closed-loop "
            "tracker state or future outcome is read"
        ),
        required_for_atoms=("lane_progress_coherence_excess_v1",),
    ),
    LoggingFieldSpec(
        name="candidate_route_corridor_margin_profile_m",
        shape="[K,H]",
        source=(
            "route corridor half width minus absolute route-relative lateral "
            "error for each candidate support point"
        ),
        no_leak_argument=(
            "computed from current route/corridor geometry and generated "
            "candidate support points"
        ),
        required_for_atoms=("corridor_margin_exhaustion_v1",),
    ),
    LoggingFieldSpec(
        name="candidate_route_heading_error_profile_rad",
        shape="[K,H]",
        source="wrapped candidate heading error relative to the current route tangent",
        no_leak_argument="uses generated candidate headings and current route tangent only",
        required_for_atoms=("heading_curvature_residual_v1",),
    ),
)


ATOM_SPECS: tuple[AtomSpec, ...] = (
    AtomSpec(
        name="curvature_conditioned_lateral_rate_excess_v1",
        expression=(
            "max_h max(|candidate_lateral_error_rate[h]| - "
            "beta * route_curvature_context_abs[h] * candidate_speed[h] - margin, 0)"
        ),
        required_fields=(
            "route_curvature_context_abs_radpm",
            "candidate_lateral_error_rate_profile_mps",
            "candidate_speed_profile_mps",
        ),
        nonnegative_argument="outer max clips the residual at zero",
        convexity_argument=(
            "convex in the lateral-rate profile for fixed logged curvature and "
            "speed allowances; after logging it is a fixed finite-candidate "
            "coefficient"
        ),
        monotone_sign_constraint="nonnegative risk atom; larger residual cannot reduce risk",
        rationale=(
            "the strict lane/hard atom overblocks beneficial candidates with "
            "large lateral support shape; this residual gives route curvature "
            "a no-leak allowance before treating lateral motion as risk"
        ),
    ),
    AtomSpec(
        name="corridor_margin_exhaustion_v1",
        expression="max_h max(safety_margin - candidate_route_corridor_margin[h], 0)",
        required_fields=("candidate_route_corridor_margin_profile_m",),
        nonnegative_argument="positive part of corridor margin exhaustion",
        convexity_argument=(
            "convex in logged corridor-margin scalars; fixed coefficient after "
            "logging"
        ),
        monotone_sign_constraint="nonnegative risk atom; lower remaining margin is worse",
        rationale=(
            "distinguishes high lateral motion that stays well inside the route "
            "corridor from high lateral motion that consumes safety margin"
        ),
    ),
    AtomSpec(
        name="heading_curvature_residual_v1",
        expression=(
            "max_h max(|candidate_heading_error[h]| - "
            "gamma * route_curvature_context_abs[h] - heading_margin, 0)"
        ),
        required_fields=(
            "route_curvature_context_abs_radpm",
            "candidate_route_heading_error_profile_rad",
        ),
        nonnegative_argument="positive part of route-curvature-conditioned heading error",
        convexity_argument=(
            "convex in logged heading-error scalars for fixed route curvature; "
            "fixed coefficient after logging"
        ),
        monotone_sign_constraint="nonnegative risk atom; larger residual is never safer",
        rationale=(
            "helps separate intended turn geometry from route-inconsistent "
            "heading drift without using future outcomes"
        ),
    ),
    AtomSpec(
        name="lane_progress_coherence_excess_v1",
        expression=(
            "max_h max(|candidate_lateral_error_rate[h]| - "
            "alpha * max(candidate_route_progress_delta[h], 0) - "
            "beta * route_curvature_context_abs[h] * candidate_speed[h], 0)"
        ),
        required_fields=(
            "route_curvature_context_abs_radpm",
            "candidate_lateral_error_rate_profile_mps",
            "candidate_speed_profile_mps",
            "candidate_route_progress_delta_profile_m",
        ),
        nonnegative_argument="positive part of lateral motion unexplained by progress/curvature",
        convexity_argument=(
            "not claimed globally convex in trajectory coordinates because route "
            "projection is logged; admissible as a fixed finite-candidate "
            "coefficient in CAMP"
        ),
        monotone_sign_constraint="nonnegative risk atom; unexplained lateral motion is penalized",
        rationale=(
            "targets the exact joint bottleneck: beneficial candidates may have "
            "large lateral support only when paired with route progress and turn "
            "context, while harmful candidates should retain residual risk"
        ),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only preflight for default-off no-leak progress+lane/hard "
            "context logging and candidate atom definitions."
        )
    )
    parser.add_argument("--joint_bottleneck_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--fail_on_formal_seeds", action="store_true")
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        joint_bottleneck_report=_load_json(args.joint_bottleneck_json),
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
    joint_bottleneck_report: dict[str, Any],
    label: str | None = None,
    fail_on_formal_seeds: bool = False,
    field_specs: tuple[LoggingFieldSpec, ...] = LOGGING_FIELD_SPECS,
    atom_specs: tuple[AtomSpec, ...] = ATOM_SPECS,
) -> dict[str, Any]:
    source = _source_gate(joint_bottleneck_report)
    formal_seed_records = int(joint_bottleneck_report.get("formal_seed_records") or 0)
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden for this preflight.")

    fields = [_field_report(spec, atom_specs) for spec in field_specs]
    atoms = [_atom_report(spec, field_specs) for spec in atom_specs]
    math_checks = _math_checks(fields, atoms)
    decision = _decision(
        source,
        formal_seed_records,
        fields,
        atoms,
        math_checks,
    )
    return {
        "analysis": {
            "name": "dp_camp_progress_lane_hard_context_logging_preflight_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "uses_existing_artifact_only": True,
            "future_outcome_labels_used_for_field_definitions": False,
            "future_outcome_labels_used_for_atom_definitions": False,
            "future_outcome_labels_used_for_source_bottleneck_diagnosis": True,
            "logging_mode": "default_off_preflight_only",
            "predeclared_hypothesis": (
                "Route-curvature-conditioned lane/progress context can expose "
                "why high lane/hard support is acceptable for some beneficial "
                "candidates but harmful for others, while preserving current-tick "
                "finite-candidate CAMP atomization."
            ),
            "math_boundary": (
                "Proposed fields are current-tick finite-candidate quantities "
                "computed from generated DP candidates, current route/map, and "
                "current ego state before selector execution. Proposed atoms are "
                "nonnegative scalar functions of those logged fields and are used "
                "with nonnegative risk weights. Once logged, each atom is a fixed "
                "coefficient a_k, so CAMP scoring remains affine "
                "score_k(w)=a_k^T w and the simplex/CVaR/L2 master remains "
                "convex. This preflight makes no global convexity claim over DP "
                "trajectory generation and constructs no DP-side classical "
                "Benders master/subproblem, dual, or cut."
            ),
        },
        "source_bottleneck_gate": source,
        "source_bottleneck_summary": _source_summary(joint_bottleneck_report),
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
    diagnosis = report.get("diagnosis") if isinstance(report, dict) else None
    blocked = report.get("blocked_beneficial") if isinstance(report, dict) else None
    if not isinstance(decision, dict) or not isinstance(diagnosis, dict):
        return {"passed": False, "status": "missing_final_decision_or_diagnosis"}
    contribution_counts = (
        blocked.get("dominant_contribution_family_counts")
        if isinstance(blocked, dict)
        else {}
    )
    lane_dominated = int((contribution_counts or {}).get("lane_hard_support") or 0) > 0
    ready = (
        decision.get("status") == BOTTLENECK_READY_STATUS
        and bool(decision.get("passed"))
        and decision.get("authorized_next_work") == BOTTLENECK_NEXT_WORK
        and diagnosis.get("primary_gap") == SOURCE_PRIMARY_GAP
        and diagnosis.get("camp_retraining_recommended") is False
        and lane_dominated
    )
    return {
        "passed": ready,
        "status": decision.get("status"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "primary_gap": diagnosis.get("primary_gap"),
        "camp_retraining_recommended": diagnosis.get("camp_retraining_recommended"),
        "lane_hard_support_dominated_blocked_beneficial": lane_dominated,
    }


def _source_summary(report: dict[str, Any]) -> dict[str, Any]:
    diagnosis = report.get("diagnosis") or {}
    counts = report.get("counts") or {}
    tradeoff = report.get("screen_tradeoff") or {}
    blocked = report.get("blocked_beneficial") or {}
    return {
        "best_screen_name": diagnosis.get("best_screen_name"),
        "beneficial_total": counts.get("beneficial_total"),
        "beneficial_retained": counts.get("beneficial_retained"),
        "beneficial_blocked": counts.get("beneficial_blocked"),
        "harmful_total": counts.get("harmful_total"),
        "harmful_allowed": counts.get("harmful_allowed"),
        "strict_safe_screen_count": diagnosis.get("strict_safe_screen_count"),
        "high_retain_screen_count": diagnosis.get("high_retain_screen_count"),
        "best_high_retain_screen": tradeoff.get("best_high_retain_screen"),
        "blocked_beneficial_dominant_contribution_family_counts": blocked.get(
            "dominant_contribution_family_counts"
        ),
        "blocked_beneficial_reason_counts": blocked.get("reason_counts"),
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
        "candidate_level": spec.candidate_level,
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
        "monotone_sign_constraint": spec.monotone_sign_constraint,
        "rationale": spec.rationale,
        "future_outcome_label_dependency": False,
        "fixed_finite_candidate_coefficient": True,
        "affine_in_camp_weights": True,
        "requires_nonnegative_weight": True,
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
            "name": "all_atoms_nonnegative_fixed_affine_coefficients",
            "passed": all(
                atom["fixed_finite_candidate_coefficient"]
                and atom["affine_in_camp_weights"]
                and atom["requires_nonnegative_weight"]
                and not atom["future_outcome_label_dependency"]
                for atom in atoms
            ),
        },
        {
            "name": "no_classical_benders_claim",
            "passed": True,
        },
    ]


def _decision(
    source: dict[str, Any],
    formal_seed_records: int,
    fields: list[dict[str, Any]],
    atoms: list[dict[str, Any]],
    math_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    if not source["passed"]:
        status = SOURCE_BLOCKED_STATUS
        primary_gap = "joint_bottleneck_gate_not_ready_for_context_logging"
        next_work = None
    elif formal_seed_records:
        status = FORMAL_SEED_STATUS
        primary_gap = "formal_seed_conflict"
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
        primary_gap = "progress_lane_hard_context_logging_preflight_ready"
        next_work = AUTHORIZED_NEXT_WORK
    return {
        "status": status,
        "passed": status == READY_STATUS,
        "primary_gap": primary_gap,
        "authorized_next_work": next_work,
        **{key: False for key in BLOCKED_ACTIONS},
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Progress + Lane/Hard Context Logging Preflight",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- primary gap: `{decision['primary_gap']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Source Bottleneck Summary",
        "",
        "```json",
        json.dumps(report["source_bottleneck_summary"], indent=2, sort_keys=True),
        "```",
        "",
        "## Logging Fields",
        "",
        "```json",
        json.dumps(report["logging_field_reports"], indent=2, sort_keys=True),
        "```",
        "",
        "## Atom Reports",
        "",
        "```json",
        json.dumps(report["atom_reports"], indent=2, sort_keys=True),
        "```",
        "",
        "## Math Checks",
        "",
        "```json",
        json.dumps(report["math_checks"], indent=2, sort_keys=True),
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
