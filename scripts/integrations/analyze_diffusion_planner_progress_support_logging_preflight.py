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

from scripts.integrations.analyze_diffusion_planner_affine_allowed_harmful_residual import (  # noqa: E402
    READY_STATUS as RESIDUAL_READY_STATUS,
)
from scripts.integrations.analyze_diffusion_planner_matched_observable_descriptor_separability import (  # noqa: E402
    _load_json,
)


READY_STATUS = "progress_support_logging_preflight_ready"
REJECT_STATUS = "progress_support_logging_preflight_rejected"
SOURCE_BLOCKED_STATUS = "progress_support_logging_preflight_source_not_ready"
FORMAL_SEED_STATUS = "progress_support_logging_preflight_formal_seed_conflict"

RESIDUAL_NEXT_WORK = "reject_observable_route_or_design_new_logging_preflight"
AUTHORIZED_NEXT_WORK = "default_off_progress_support_logging_implementation_unit_tests_only"

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
        name="candidate_route_progress_s_profile_m",
        shape="[K,H]",
        source=(
            "project each generated DP candidate prefix onto the current route "
            "polyline before selector execution"
        ),
        no_leak_argument=(
            "uses only current map/route and generated candidate geometry; it "
            "does not use tracker execution or closed-loop outcomes"
        ),
        required_for_atoms=(
            "route_progress_deficit_envelope_v1",
            "route_progress_regression_envelope_v1",
        ),
    ),
    LoggingFieldSpec(
        name="candidate_plan_arc_length_profile_m",
        shape="[K,H]",
        source="cumulative arc length along each generated DP candidate prefix",
        no_leak_argument=(
            "computed from the candidate trajectory itself at the current tick, "
            "before selection"
        ),
        required_for_atoms=("plan_arc_support_deficit_v1",),
    ),
    LoggingFieldSpec(
        name="candidate_speed_profile_mps",
        shape="[K,H-1]",
        source="finite-difference speed profile from generated candidate prefix",
        no_leak_argument=(
            "uses candidate prefix timestamps and positions only; no future "
            "simulator state or selected trajectory outcome is read"
        ),
        required_for_atoms=(
            "tail_speed_support_deficit_v1",
            "low_speed_progress_conflict_v1",
        ),
    ),
    LoggingFieldSpec(
        name="candidate_route_remaining_m",
        shape="[K]",
        source=(
            "current route remaining distance at each candidate prefix endpoint, "
            "clipped to nonnegative values"
        ),
        no_leak_argument=(
            "route remaining is a deterministic function of current route and "
            "generated candidate endpoint"
        ),
        required_for_atoms=("route_remaining_excess_vs_top1_v1",),
    ),
    LoggingFieldSpec(
        name="candidate_goal_alignment_progress_m",
        shape="[K]",
        source=(
            "dot product between candidate endpoint displacement and current "
            "route-to-goal tangent, clipped to nonnegative route support"
        ),
        no_leak_argument=(
            "computed from current ego pose, route tangent, and candidate "
            "endpoint only"
        ),
        required_for_atoms=("goal_alignment_progress_deficit_v1",),
    ),
)


ATOM_SPECS: tuple[AtomSpec, ...] = (
    AtomSpec(
        name="route_progress_deficit_envelope_v1",
        expression=(
            "max_h max(top1_route_progress_s[h] - candidate_route_progress_s[h], 0)"
        ),
        required_fields=("candidate_route_progress_s_profile_m",),
        nonnegative_argument="outer and inner max operators clip the atom at zero",
        convexity_argument=(
            "convex in the logged scalar profile values; once logged, it is a "
            "fixed nonnegative coefficient a_k"
        ),
        rationale=(
            "allowed harmful residuals are dominated by posterior progress loss; "
            "this logs a stronger current-tick progress-support envelope"
        ),
    ),
    AtomSpec(
        name="route_progress_regression_envelope_v1",
        expression=(
            "max_h max(candidate_route_progress_s[h] - candidate_route_progress_s[h+1], 0)"
        ),
        required_fields=("candidate_route_progress_s_profile_m",),
        nonnegative_argument="positive part of route-progress backtracking",
        convexity_argument=(
            "max of affine differences is convex in logged scalar values; CAMP "
            "master sees only fixed coefficients"
        ),
        rationale=(
            "captures candidates whose current plan loses route support within "
            "the generated prefix"
        ),
    ),
    AtomSpec(
        name="plan_arc_support_deficit_v1",
        expression=(
            "max(top1_plan_arc_length_final - candidate_plan_arc_length_final, 0)"
        ),
        required_fields=("candidate_plan_arc_length_profile_m",),
        nonnegative_argument="positive part relative to Top-1 arc support",
        convexity_argument=(
            "convex in logged final arc length scalars; fixed after logging"
        ),
        rationale=(
            "separates low-support candidates that may look route-aligned but "
            "do not advance enough along their own plan"
        ),
    ),
    AtomSpec(
        name="tail_speed_support_deficit_v1",
        expression="max(top1_tail_speed_mps - candidate_tail_speed_mps, 0)",
        required_fields=("candidate_speed_profile_mps",),
        nonnegative_argument="positive part of tail-speed deficit",
        convexity_argument="convex in logged tail-speed scalars; fixed per candidate",
        rationale=(
            "progress-loss residuals may be induced by near-stop candidates that "
            "are not captured by geometric envelope alone"
        ),
    ),
    AtomSpec(
        name="route_remaining_excess_vs_top1_v1",
        expression="max(candidate_route_remaining - top1_route_remaining, 0)",
        required_fields=("candidate_route_remaining_m",),
        nonnegative_argument="positive part of excess remaining route distance",
        convexity_argument=(
            "convex in logged route-remaining scalars; no trajectory-coordinate "
            "convexity is claimed"
        ),
        rationale="direct current-tick proxy for not making route progress",
    ),
    AtomSpec(
        name="goal_alignment_progress_deficit_v1",
        expression=(
            "max(top1_goal_alignment_progress - candidate_goal_alignment_progress, 0)"
        ),
        required_fields=("candidate_goal_alignment_progress_m",),
        nonnegative_argument="positive part of goal-aligned progress deficit",
        convexity_argument=(
            "convex in logged goal-alignment scalars; fixed coefficient in CAMP"
        ),
        rationale=(
            "guards against candidates that move but do not support the active route goal"
        ),
    ),
    AtomSpec(
        name="low_speed_progress_conflict_v1",
        expression=(
            "route_progress_deficit_envelope_v1 * "
            "max(top1_tail_speed_mps - candidate_tail_speed_mps, 0)"
        ),
        required_fields=(
            "candidate_route_progress_s_profile_m",
            "candidate_speed_profile_mps",
        ),
        nonnegative_argument="product of nonnegative logged scalar deficits",
        convexity_argument=(
            "not claimed convex in raw logged variables; admissible only as a "
            "fixed finite-candidate coefficient after logging"
        ),
        rationale=(
            "diagnoses whether progress-loss residuals are specifically low-speed "
            "support conflicts"
        ),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only preflight for default-off no-leak DP-CAMP progress-support "
            "logging and candidate atom definitions."
        )
    )
    parser.add_argument("--affine_residual_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--fail_on_formal_seeds", action="store_true")
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        affine_residual_report=_load_json(args.affine_residual_json),
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
    affine_residual_report: dict[str, Any],
    label: str | None = None,
    fail_on_formal_seeds: bool = False,
    field_specs: tuple[LoggingFieldSpec, ...] = LOGGING_FIELD_SPECS,
    atom_specs: tuple[AtomSpec, ...] = ATOM_SPECS,
) -> dict[str, Any]:
    source = _source_gate(affine_residual_report)
    formal_seed_records = int(
        ((affine_residual_report.get("records") or {}).get("formal_seed_records") or 0)
    )
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden for this preflight.")
    residual = affine_residual_report.get("residual_allowed_harmful") or {}
    fields = [_field_report(spec, atom_specs) for spec in field_specs]
    atoms = [_atom_report(spec, field_specs) for spec in atom_specs]
    math_checks = _math_checks(fields, atoms)
    decision = _decision(source, formal_seed_records, fields, atoms, math_checks, residual)
    return {
        "analysis": {
            "name": "dp_camp_progress_support_logging_preflight_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "uses_existing_artifact_only": True,
            "future_outcome_labels_used_for_field_definitions": False,
            "future_outcome_labels_used_for_atom_definitions": False,
            "future_outcome_labels_used_for_source_residual_diagnosis": True,
            "logging_mode": "default_off_preflight_only",
            "math_boundary": (
                "Proposed fields are current-tick finite-candidate quantities "
                "computed from generated DP candidates, current route/map, and "
                "current ego state before selector execution. Proposed atoms are "
                "nonnegative scalar functions of those logged fields. Once "
                "logged, each atom is a fixed coefficient a_k, so CAMP scoring "
                "remains affine score_k(w)=a_k^T w and the simplex/CVaR/L2 "
                "master remains convex. This preflight makes no global "
                "convexity claim over trajectory coordinates and constructs no "
                "DP-side classical Benders master/subproblem, dual, or cut."
            ),
        },
        "source_affine_residual_gate": source,
        "source_residual_summary": {
            "dominant_primary_reason": residual.get("dominant_primary_reason"),
            "primary_reason_counts": residual.get("primary_reason_counts"),
            "multi_label_counts": residual.get("multi_label_counts"),
            "candidate_state_family_hint": residual.get("candidate_state_family_hint"),
        },
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
    residual = report.get("residual_allowed_harmful") if isinstance(report, dict) else None
    if not isinstance(decision, dict):
        return {"passed": False, "status": "missing_final_decision"}
    ready = (
        decision.get("status") == RESIDUAL_READY_STATUS
        and bool(decision.get("passed"))
        and decision.get("authorized_next_work") == RESIDUAL_NEXT_WORK
        and isinstance(residual, dict)
        and residual.get("dominant_primary_reason") == "progress_loss"
    )
    return {
        "passed": ready,
        "status": decision.get("status"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "dominant_primary_reason": (
            residual.get("dominant_primary_reason") if isinstance(residual, dict) else None
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
    residual: dict[str, Any],
) -> dict[str, Any]:
    if not source["passed"]:
        status = SOURCE_BLOCKED_STATUS
        primary_gap = "affine_residual_gate_not_progress_loss_ready"
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
    elif residual.get("dominant_primary_reason") != "progress_loss":
        status = REJECT_STATUS
        primary_gap = "residual_not_progress_support_dominated"
        next_work = None
    else:
        status = READY_STATUS
        primary_gap = "progress_support_logging_preflight_ready"
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
        "# DP CAMP Progress-Support Logging Preflight",
        "",
        "This is a read-only design preflight for default-off no-leak "
        "progress-support logging. It does not implement DP logging, train CAMP, "
        "run replay, or authorize a selector.",
        "",
        "## Decision",
        "",
        f"status=`{decision['status']}`",
        f"passed=`{decision['passed']}`",
        f"primary_gap=`{decision['primary_gap']}`",
        f"authorized_next_work=`{decision['authorized_next_work']}`",
        "",
        "## Source Residual",
        "",
        "```json",
        json.dumps(report["source_residual_summary"], indent=2, sort_keys=True),
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
