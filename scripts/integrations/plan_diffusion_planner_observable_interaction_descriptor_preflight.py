#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.analyze_diffusion_planner_matched_observable_descriptor_separability import (  # noqa: E402
    FEATURE_SPECS as REJECTED_OBSERVABLE_FEATURE_SPECS,
    REJECT_STATUS as OBSERVABLE_REJECT_STATUS,
    _load_json,
)
from scripts.integrations.analyze_diffusion_planner_observable_descriptor_bottleneck import (  # noqa: E402
    READY_STATUS as OBSERVABLE_BOTTLENECK_READY_STATUS,
)
from scripts.integrations.analyze_diffusion_planner_observable_state_payload_coverage import (  # noqa: E402
    EXPECTED_FIELDS as OBSERVABLE_FIELDS,
)
from scripts.integrations.synthesize_diffusion_planner_relaxed_strict_atom_observability_limit import (  # noqa: E402
    READY_STATUS as LIMIT_READY_STATUS,
)


READY_STATUS = "observable_interaction_descriptor_preflight_ready"
REJECT_STATUS = "observable_interaction_descriptor_preflight_rejected"
SOURCE_BLOCKED_STATUS = "observable_interaction_descriptor_preflight_source_not_ready"
NEXT_WORK = "offline_observable_interaction_descriptor_separability_screen_only"

BLOCKED_ACTIONS = (
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "online_selector_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


@dataclass(frozen=True)
class InteractionDescriptorSpec:
    name: str
    expression: str
    required_fields: tuple[str, ...]
    rationale: str
    nonnegative_argument: str
    convexity_note: str
    interaction_degree: int = 2
    default_off: bool = True
    uses_future_outcomes: bool = False
    candidate_level: bool = True


DESCRIPTOR_SPECS: tuple[InteractionDescriptorSpec, ...] = (
    InteractionDescriptorSpec(
        name="red_aligned_stopline_proximity_hinge_v1",
        expression=(
            "max(0, mean(red_heading_alignment[k])) * "
            "max(0, red_distance_budget_m - min(red_stopline_distance[k]))"
        ),
        required_fields=(
            "candidate_red_stopline_distance_m",
            "candidate_red_heading_alignment",
        ),
        rationale=(
            "single red-distance and red-alignment descriptors were already "
            "screened; the interaction targets candidates that are both close "
            "to a red stopline and aligned with crossing it"
        ),
        nonnegative_argument="product of two nonnegative hinge terms",
        convexity_note=(
            "not a trajectory-space convexity claim; the computed value is a "
            "fixed nonnegative coefficient before CAMP chooses weights"
        ),
    ),
    InteractionDescriptorSpec(
        name="clearance_progress_tradeoff_hinge_v1",
        expression=(
            "max(0, clearance_budget_m - clearance[k]) * "
            "max(0, route_projection_delta_vs_top1[k])"
        ),
        required_fields=(
            "candidate_min_obstacle_clearance_lower_bound_m",
            "candidate_route_projection_s_m",
        ),
        rationale=(
            "separates progress-seeking alternatives that buy progress while "
            "spending current-tick obstacle clearance"
        ),
        nonnegative_argument="product of nonnegative clearance and progress hinges",
        convexity_note="fixed candidate coefficient keeps score_k(w)=a_k^T w affine",
    ),
    InteractionDescriptorSpec(
        name="turn_lateral_clearance_context_hinge_v1",
        expression=(
            "max(route_heading_change_abs_context) * "
            "max(0, abs_lateral_error[k] - lateral_error_budget_m) * "
            "max(0, clearance_budget_m - clearance[k])"
        ),
        required_fields=(
            "candidate_route_heading_change_rad",
            "candidate_route_lateral_error_m",
            "candidate_min_obstacle_clearance_lower_bound_m",
        ),
        rationale=(
            "targets sharp-turn candidates where lateral route error and "
            "clearance pressure co-occur; the previous single-field observable "
            "screen did not model this co-occurrence"
        ),
        nonnegative_argument="product of nonnegative absolute/hinge summaries",
        convexity_note="fixed candidate coefficient; no global convexity in xy is claimed",
        interaction_degree=3,
    ),
    InteractionDescriptorSpec(
        name="top1_deviation_without_current_safety_gain_v1",
        expression=(
            "max(0, route_lateral_deviation_vs_top1 + "
            "route_projection_loss_vs_top1 - current_tick_safety_gain)"
        ),
        required_fields=(
            "candidate_route_projection_s_m",
            "candidate_route_lateral_error_m",
            "candidate_red_stopline_distance_m",
            "candidate_red_heading_alignment",
            "candidate_min_obstacle_clearance_lower_bound_m",
        ),
        rationale=(
            "keeps a DP Top-1 prior unless the candidate has an observable "
            "current-tick safety gain from red-light relation or clearance; "
            "this addresses the high quality of DP Top-1 without making Top-1 "
            "dominance unconditional"
        ),
        nonnegative_argument="outer hinge clamps the derived difference at zero",
        convexity_note="all terms are fixed before selection, so CAMP remains affine in w",
        interaction_degree=3,
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only preflight for a new observable interaction descriptor "
            "family after relaxed-strict atoms and single-field observable "
            "descriptors were rejected. It does not run replay, train CAMP, "
            "or change online selection."
        )
    )
    parser.add_argument("--observability_limit_json", type=Path, required=True)
    parser.add_argument("--observable_separability_json", type=Path, required=True)
    parser.add_argument("--observable_bottleneck_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        observability_limit_report=_load_json(args.observability_limit_json),
        observable_separability_report=_load_json(args.observable_separability_json),
        observable_bottleneck_report=_load_json(args.observable_bottleneck_json),
        label=args.label,
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
    observability_limit_report: dict[str, Any],
    observable_separability_report: dict[str, Any],
    observable_bottleneck_report: dict[str, Any],
    label: str | None = None,
    descriptor_specs: tuple[InteractionDescriptorSpec, ...] = DESCRIPTOR_SPECS,
) -> dict[str, Any]:
    source_gates = {
        "observability_limit": _decision(observability_limit_report),
        "observable_separability": _decision(observable_separability_report),
        "observable_bottleneck": _decision(observable_bottleneck_report),
    }
    descriptor_audit = _descriptor_audit(descriptor_specs)
    source_ready = _sources_ready(source_gates)
    descriptors_ready = not descriptor_audit["errors"]
    if source_ready and descriptors_ready:
        status = READY_STATUS
        passed = True
        primary_gap = "interaction_descriptor_family_preflight_passed"
        authorized_next_work = NEXT_WORK
    elif not source_ready:
        status = SOURCE_BLOCKED_STATUS
        passed = False
        primary_gap = _source_gap(source_gates)
        authorized_next_work = "fix_source_gates_before_interaction_preflight"
    else:
        status = REJECT_STATUS
        passed = False
        primary_gap = "interaction_descriptor_specs_invalid"
        authorized_next_work = "revise_interaction_descriptor_specs_design_only"
    final = {
        "status": status,
        "passed": passed,
        "primary_gap": primary_gap,
        "authorized_next_work": authorized_next_work,
        **{key: False for key in BLOCKED_ACTIONS},
    }
    return {
        "analysis": {
            "name": "dp_camp_observable_interaction_descriptor_preflight_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "closed_loop_replay": False,
            "online_selector_change": False,
            "uses_existing_artifacts_only": True,
            "future_outcome_labels_used_for_descriptors": False,
            "future_outcome_labels_used_for_preflight": False,
            "selection_effect": False,
            "math_boundary": (
                "The proposed descriptors are finite current-tick candidate "
                "coefficients computed from already logged observable-state "
                "fields. Products and hinges are allowed only as fixed feature "
                "computations before selection; CAMP still scores each "
                "candidate as score_k(w)=a_k^T w, so the simplex/CVaR/L2 "
                "master remains convex in weights. This gate does not claim "
                "trajectory-space convexity and does not construct a DP-side "
                "classical Benders master/subproblem, dual, or cut."
            ),
        },
        "source_gates": source_gates,
        "rejected_single_field_descriptors": [
            spec.name for spec in REJECTED_OBSERVABLE_FEATURE_SPECS
        ],
        "available_observable_fields": list(OBSERVABLE_FIELDS),
        "proposed_descriptors": [asdict(spec) for spec in descriptor_specs],
        "descriptor_audit": descriptor_audit,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": final,
    }


def _decision(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision")
    if not isinstance(decision, dict):
        return {
            "status": None,
            "passed": False,
            "primary_gap": "final_decision_missing",
            "authorized_next_work": None,
        }
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "primary_gap": decision.get("primary_gap"),
        "authorized_next_work": decision.get("authorized_next_work"),
    }


def _sources_ready(source_gates: dict[str, dict[str, Any]]) -> bool:
    return bool(
        source_gates["observability_limit"]["status"] == LIMIT_READY_STATUS
        and source_gates["observability_limit"]["passed"]
        and source_gates["observable_separability"]["status"]
        == OBSERVABLE_REJECT_STATUS
        and not source_gates["observable_separability"]["passed"]
        and source_gates["observable_bottleneck"]["status"]
        == OBSERVABLE_BOTTLENECK_READY_STATUS
        and source_gates["observable_bottleneck"]["passed"]
    )


def _source_gap(source_gates: dict[str, dict[str, Any]]) -> str:
    if source_gates["observability_limit"]["status"] != LIMIT_READY_STATUS:
        return "observability_limit_not_recorded"
    if not source_gates["observability_limit"]["passed"]:
        return "observability_limit_not_passed"
    if (
        source_gates["observable_separability"]["status"]
        != OBSERVABLE_REJECT_STATUS
    ):
        return "observable_single_field_separability_not_rejected"
    if source_gates["observable_separability"]["passed"]:
        return "observable_single_field_separability_already_promising"
    if (
        source_gates["observable_bottleneck"]["status"]
        != OBSERVABLE_BOTTLENECK_READY_STATUS
    ):
        return "observable_bottleneck_not_diagnosed"
    if not source_gates["observable_bottleneck"]["passed"]:
        return "observable_bottleneck_not_passed"
    return "source_gates_not_ready"


def _descriptor_audit(
    descriptor_specs: tuple[InteractionDescriptorSpec, ...],
) -> dict[str, Any]:
    available = set(OBSERVABLE_FIELDS)
    rejected_names = {spec.name for spec in REJECTED_OBSERVABLE_FEATURE_SPECS}
    errors: list[str] = []
    warnings: list[str] = []
    names = [spec.name for spec in descriptor_specs]
    if len(names) != len(set(names)):
        errors.append("descriptor names must be unique")
    for spec in descriptor_specs:
        missing = sorted(set(spec.required_fields) - available)
        if missing:
            errors.append(f"{spec.name} missing observable fields {missing}")
        if spec.name in rejected_names:
            errors.append(f"{spec.name} reuses a rejected single-field descriptor name")
        if spec.interaction_degree < 2:
            errors.append(f"{spec.name} is not an interaction descriptor")
        if spec.uses_future_outcomes:
            errors.append(f"{spec.name} uses future outcomes")
        if not spec.default_off:
            errors.append(f"{spec.name} is not default-off")
        if not spec.candidate_level:
            warnings.append(f"{spec.name} is not candidate-level")
    return {
        "errors": errors,
        "warnings": warnings,
        "passed": not errors,
        "descriptor_count": len(descriptor_specs),
        "required_fields": sorted(
            {field for spec in descriptor_specs for field in spec.required_fields}
        ),
        "all_required_fields_available": not any(
            set(spec.required_fields) - available for spec in descriptor_specs
        ),
        "all_names_new_vs_rejected_single_field_descriptors": not any(
            spec.name in rejected_names for spec in descriptor_specs
        ),
        "all_default_off": all(spec.default_off for spec in descriptor_specs),
        "all_no_future_outcomes": all(
            not spec.uses_future_outcomes for spec in descriptor_specs
        ),
        "min_interaction_degree": min(
            (spec.interaction_degree for spec in descriptor_specs),
            default=0,
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Observable Interaction Descriptor Preflight",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- primary gap: `{decision['primary_gap']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Source Gates",
        "",
        "```json",
        json.dumps(report["source_gates"], indent=2, sort_keys=True),
        "```",
        "",
        "## Descriptor Audit",
        "",
        "```json",
        json.dumps(report["descriptor_audit"], indent=2, sort_keys=True),
        "```",
        "",
        "## Proposed Descriptors",
        "",
        "| Name | Required Fields | Interaction Degree |",
        "| --- | --- | ---: |",
    ]
    for spec in report["proposed_descriptors"]:
        fields = ", ".join(f"`{field}`" for field in spec["required_fields"])
        lines.append(f"| `{spec['name']}` | {fields} | {spec['interaction_degree']} |")
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
