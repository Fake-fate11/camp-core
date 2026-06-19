#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


MODE_ROUTE = "new_mode_seeking_candidate_generation"
SAME_MODE_ROUTE = "simple_k_noise_or_same_mode_generator"
READY_STATUS = "mode_seeking_candidate_design_gate_ready"
BLOCKED_STATUS = "mode_seeking_candidate_design_gate_blocked"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only design gate for a default-off mode-seeking candidate-set "
            "diagnostic after the DP-CAMP next-design preflight. It does not "
            "run Diffusion Planner, train CAMP, or change online selection."
        )
    )
    parser.add_argument("--next_design_preflight_json", type=Path, required=True)
    parser.add_argument("--candidate_generation_controls_json", type=Path, default=None)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        next_design_preflight=_load_json(args.next_design_preflight_json),
        candidate_generation_controls=(
            None
            if args.candidate_generation_controls_json is None
            else _load_json(args.candidate_generation_controls_json)
        ),
        label=args.label,
        paths={
            "next_design_preflight_json": str(args.next_design_preflight_json),
            "candidate_generation_controls_json": _path_or_none(
                args.candidate_generation_controls_json
            ),
        },
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")


def build_report(
    *,
    next_design_preflight: dict[str, Any],
    candidate_generation_controls: dict[str, Any] | None = None,
    label: str | None = None,
    paths: dict[str, Any] | None = None,
) -> dict[str, Any]:
    routes = {
        route.get("name"): route
        for route in next_design_preflight.get("design_routes", [])
        if isinstance(route, dict)
    }
    mode_route = routes.get(MODE_ROUTE) or {}
    same_mode_route = routes.get(SAME_MODE_ROUTE) or {}
    controls = _control_summary(candidate_generation_controls)
    preconditions = _preconditions(mode_route, same_mode_route, controls)
    decision = _decision(preconditions)
    return {
        "analysis": {
            "name": "dp_camp_mode_seeking_candidate_design_gate_v1",
            "label": label,
            "role": (
                "predeclared design gate for implementing a default-off "
                "mode-seeking DP candidate-set diagnostic"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_leakage": False,
            "math_boundary": (
                "DP remains a frozen black-box trajectory candidate generator. "
                "A mode-seeking diagnostic may only change the finite candidate "
                "set produced at the current tick under fixed DP weights. CAMP "
                "runtime atoms remain current-tick finite-candidate quantities; "
                "scores remain affine a_k^T w; the simplex/CVaR/L2 robust "
                "master remains convex. This gate is not classical Benders "
                "decomposition and makes no trajectory-coordinate convexity "
                "claim."
            ),
            "paths": paths or {},
        },
        "source_statuses": {
            "next_design_preflight": _decision_status(next_design_preflight),
            "mode_route": mode_route.get("status"),
            "same_mode_route": same_mode_route.get("status"),
            "candidate_generation_controls": controls["decision"],
        },
        "preconditions": preconditions,
        "design_contract": _design_contract(),
        "candidate_availability_gate": _availability_gate(),
        "final_decision": decision,
    }


def _preconditions(
    mode_route: dict[str, Any],
    same_mode_route: dict[str, Any],
    controls: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "name": "mode_route_is_conditional",
            "passed": mode_route.get("status") == "conditional_next_design",
            "evidence": mode_route.get("status"),
        },
        {
            "name": "same_mode_variants_rejected",
            "passed": same_mode_route.get("status") == "rejected",
            "evidence": same_mode_route.get("status"),
        },
        {
            "name": "official_guidance_available",
            "passed": controls["official_guidance_available"],
            "evidence": controls["official_guidance_available"],
        },
        {
            "name": "prototype_support_available",
            "passed": controls["prototype_support_available"],
            "evidence": controls["prototype_support_available"],
        },
        {
            "name": "current_runner_guidance_disabled",
            "passed": controls["current_runner_guidance_disabled"],
            "evidence": controls["current_runner_guidance_disabled"],
        },
        {
            "name": "no_dp_source_modification_required",
            "passed": not controls["dp_source_modification_required"],
            "evidence": controls["dp_source_modification_required"],
        },
        {
            "name": "no_camp_atom_schema_change_required",
            "passed": not controls["camp_atom_schema_change_required"],
            "evidence": controls["camp_atom_schema_change_required"],
        },
    ]


def _design_contract() -> dict[str, Any]:
    return {
        "candidate_set_variant": "default_off_mode_seeking_guidance_or_prototype",
        "fixed_dp_weights_required": True,
        "dp_source_modification_allowed": False,
        "camp_weight_training_allowed": False,
        "camp_atom_schema_change_allowed": False,
        "default_off_cli_required": True,
        "metadata_required": [
            "candidate_generation_contract",
            "mode_seeking_enabled",
            "guidance_type",
            "guidance_scale",
            "prototype_or_anchor_source",
            "candidate0_preservation_max_abs_xy_m",
        ],
        "baseline_preservation": {
            "candidate0_must_match_unguided_top1": True,
            "candidate0_max_abs_xy_m": 1e-6,
        },
        "formal_seeds_forbidden": True,
        "runtime_math_boundary": (
            "For any fixed generated candidate set, CAMP sees only finite "
            "current-tick candidate features. Candidate generation is outside "
            "the convex master; selector scoring remains affine in w."
        ),
    }


def _availability_gate() -> dict[str, Any]:
    return {
        "authorized_next_experiment": (
            "default_off_candidate_availability_and_diversity_diagnostic_only"
        ),
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "outcome_labels_allowed": "evaluation_only_after_outcome_free_availability_passes",
        "outcome_free_requirements": {
            "min_endpoint_pairwise_mean_m": 0.50,
            "min_endpoint_pairwise_gain_vs_best_rejected_m": 0.25,
            "min_mode_count_mean": 2.0,
            "candidate0_preservation_max_abs_xy_m": 1e-6,
            "non_top1_dense_lane_change_support_rate_min": 0.25,
            "progress_loss_budget_m": 0.10,
            "target_speed_loss_budget_mps": 0.20,
            "jerk_worse_budget_mps3": 0.05,
            "lateral_worse_budget_mps2": 0.05,
        },
        "latency_guard": {
            "must_report_generation_and_selection_p95_ms": True,
            "closed_loop_p95_ms_limit_before_replay": 100.0,
            "must_leave_positive_margin_before_nonformal_smoke": True,
        },
        "failure_rules": [
            "reject if candidate0 is not preserved",
            "reject if endpoint/mode spread remains same-mode",
            "reject if dense lane-change support is only Top-1 dependent",
            "reject if latency has no credible p95 margin",
            "reject if any formal seed is present",
        ],
    }


def _decision(preconditions: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [item["name"] for item in preconditions if not item["passed"]]
    ready = not failed
    return {
        "status": READY_STATUS if ready else BLOCKED_STATUS,
        "failed_preconditions": failed,
        "implementation_authorized": ready,
        "authorized_implementation": (
            "default_off_candidate_availability_diagnostic"
            if ready
            else None
        ),
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "next_step": (
            "Implement only a default-off candidate availability/diversity "
            "diagnostic with metadata and baseline preservation checks."
            if ready
            else "Do not implement the mode-seeking diagnostic until failed "
            "preconditions are resolved."
        ),
    }


def _control_summary(report: dict[str, Any] | None) -> dict[str, Any]:
    if report is None:
        return {
            "decision": None,
            "official_guidance_available": False,
            "prototype_support_available": False,
            "current_runner_guidance_disabled": False,
            "dp_source_modification_required": True,
            "camp_atom_schema_change_required": True,
        }
    admissibility = report.get("admissibility") or {}
    next_gate = report.get("next_gate") or {}
    return {
        "decision": next_gate.get("decision"),
        "official_guidance_available": bool(
            admissibility.get("official_guidance_available")
        ),
        "prototype_support_available": bool(
            admissibility.get("prototype_support_available")
        ),
        "current_runner_guidance_disabled": bool(
            admissibility.get("current_runner_guidance_disabled")
        ),
        "dp_source_modification_required": bool(
            admissibility.get("dp_source_modification_required")
        ),
        "camp_atom_schema_change_required": bool(
            admissibility.get("camp_atom_schema_change_required")
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    gate = report["candidate_availability_gate"]
    lines = [
        "# DP CAMP Mode-Seeking Candidate Design Gate",
        "",
        "This is a read-only design gate. It does not run Diffusion Planner, train CAMP, change online selection, run Full36, or use formal seeds.",
        "",
        "## Verdict",
        "",
        f"- Status: `{decision['status']}`",
        f"- Implementation authorized: `{decision['implementation_authorized']}`",
        f"- Authorized implementation: `{decision['authorized_implementation']}`",
        f"- Closed-loop smoke authorized: `{decision['closed_loop_smoke_authorized']}`",
        f"- CAMP retraining authorized: `{decision['camp_retraining_authorized']}`",
        "",
        "Failed preconditions:",
    ]
    failed = decision["failed_preconditions"]
    if failed:
        lines.extend(f"- `{item}`" for item in failed)
    else:
        lines.append("- `none`")
    lines.extend(
        [
            "",
            "## Preconditions",
            "",
            "| Name | Passed | Evidence |",
            "| --- | --- | --- |",
        ]
    )
    for item in report["preconditions"]:
        lines.append(
            f"| `{item['name']}` | `{item['passed']}` | `{item['evidence']}` |"
        )
    lines.extend(
        [
            "",
            "## Candidate Availability Gate",
            "",
            f"- Authorized next experiment: `{gate['authorized_next_experiment']}`",
            f"- Outcome labels: `{gate['outcome_labels_allowed']}`",
            f"- Endpoint spread minimum: `{gate['outcome_free_requirements']['min_endpoint_pairwise_mean_m']}` m",
            f"- Mode-count mean minimum: `{gate['outcome_free_requirements']['min_mode_count_mean']}`",
            f"- Non-Top1 dense lane-change support minimum: `{gate['outcome_free_requirements']['non_top1_dense_lane_change_support_rate_min']}`",
            "",
            "Failure rules:",
        ]
    )
    for rule in gate["failure_rules"]:
        lines.append(f"- {rule}")
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            f"Next step: {decision['next_step']}",
            "",
        ]
    )
    return "\n".join(lines)


def _decision_status(report: dict[str, Any]) -> str | None:
    decision = report.get("final_decision") or {}
    status = decision.get("status")
    return str(status) if status is not None else None


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _path_or_none(path: Path | None) -> str | None:
    return None if path is None else str(path)


if __name__ == "__main__":
    main()
