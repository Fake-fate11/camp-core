#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SUPPORT_INSUFFICIENT = "mode_seeking_failure_source_candidate_support_insufficient"
REWARD_GATE_SUSPECT = "mode_seeking_failure_source_reward_gate_suspect"
AVAILABILITY_REJECTED = "mode_seeking_candidate_availability_rejected"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only design gate after a mode-seeking DP candidate-generation "
            "failure. It consumes existing JSON diagnostics and predeclares the "
            "next allowed candidate-support design boundary."
        )
    )
    parser.add_argument("--availability_json", type=Path, required=True)
    parser.add_argument("--failure_source_json", type=Path, required=True)
    parser.add_argument("--next_design_preflight_json", type=Path, default=None)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        availability=_load_json(args.availability_json),
        failure_source=_load_json(args.failure_source_json),
        next_design_preflight=(
            None
            if args.next_design_preflight_json is None
            else _load_json(args.next_design_preflight_json)
        ),
        label=args.label,
        paths={
            "availability_json": str(args.availability_json),
            "failure_source_json": str(args.failure_source_json),
            "next_design_preflight_json": _path_or_none(
                args.next_design_preflight_json
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
    availability: dict[str, Any],
    failure_source: dict[str, Any],
    next_design_preflight: dict[str, Any] | None = None,
    label: str | None = None,
    paths: dict[str, Any] | None = None,
) -> dict[str, Any]:
    availability_summary = _availability_summary(availability)
    failure_summary = _failure_source_summary(failure_source)
    preflight_summary = _preflight_summary(next_design_preflight)
    source_authorization_conflicts = _authorization_conflicts(
        availability,
        failure_source,
    )
    route_families = _route_families(
        availability_summary,
        failure_summary,
        preflight_summary,
    )
    decision = _decision(
        availability_summary=availability_summary,
        failure_summary=failure_summary,
        source_authorization_conflicts=source_authorization_conflicts,
    )
    return {
        "analysis": {
            "name": "dp_camp_candidate_generation_support_design_gate_v1",
            "label": label,
            "role": (
                "read-only triage gate for the next DP-CAMP candidate-generation "
                "support design after route/lane guidance failed"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_leakage": False,
            "math_boundary": (
                "DP remains a frozen black-box candidate generator. This gate "
                "does not generate trajectories, change DP or CAMP weights, add "
                "atoms, or construct a DP-side master/subproblem. Any next "
                "candidate-support design must produce a fixed finite "
                "current-tick candidate set with outcome-free metadata; CAMP "
                "scores remain affine a_k^T w and the simplex/CVaR/L2 master "
                "remains convex for that fixed set. This is not classical "
                "Benders decomposition."
            ),
            "paths": paths or {},
        },
        "source_summaries": {
            "availability": availability_summary,
            "failure_source": failure_summary,
            "next_design_preflight": preflight_summary,
        },
        "route_families": route_families,
        "next_design_requirements": _next_design_requirements(),
        "blocked_actions": _blocked_actions(),
        "source_authorization_conflicts": source_authorization_conflicts,
        "final_decision": decision,
    }


def _availability_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    return {
        "status": decision.get("status"),
        "candidate0_preserved": _deep_get(
            report,
            ("candidate0_preservation", "passed"),
            _deep_get(report, ("final_decision", "gates", "candidate0_preserved")),
        ),
        "candidate0_structural_preservation_contract": _deep_get(
            report,
            ("final_decision", "gates", "candidate0_structural_preservation_contract"),
        ),
        "non_top1_dense_lane_change_support_pass": _deep_get(
            report,
            ("final_decision", "gates", "non_top1_dense_lane_change_support_pass"),
        ),
        "endpoint_pairwise_mean_pass": _deep_get(
            report,
            ("final_decision", "gates", "endpoint_pairwise_mean_pass"),
        ),
        "endpoint_gain_pass": _deep_get(
            report,
            ("final_decision", "gates", "endpoint_gain_pass"),
        ),
        "latency_p95_pass": _deep_get(
            report,
            ("final_decision", "gates", "latency_p95_pass"),
        ),
        "latency_p95_ms": _first_number(
            _deep_get(report, ("latency", "candidate", "p95_ms")),
            _deep_get(report, ("latency", "guided", "p95_ms")),
            _deep_get(report, ("aggregate", "guided_latency_p95_ms")),
            _deep_get(report, ("final_decision", "guided_latency_p95_ms")),
        ),
    }


def _failure_source_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    aggregate = report.get("aggregate") or {}
    gates = aggregate.get("gates") or {}
    return {
        "status": decision.get("status"),
        "reward_gate_suspect": bool(decision.get("reward_gate_suspect")),
        "geometry_or_tracker_support_insufficient": bool(
            decision.get("geometry_or_tracker_support_insufficient")
        ),
        "latency_blocked": bool(decision.get("latency_blocked")),
        "contract_ok": bool(decision.get("contract_ok")),
        "formal_seeds_absent": bool(decision.get("formal_seeds_absent")),
        "candidate0_preservation_max_abs_xy_m": _first_number(
            aggregate.get("candidate0_preservation_max_abs_xy_m")
        ),
        "candidate_reward_feasible_total": _first_number(
            aggregate.get("candidate_reward_feasible_total")
        ),
        "combined_tracker_support_records": _first_number(
            aggregate.get("combined_tracker_support_records")
        ),
        "endpoint_pairwise_mean_gain_m": _first_number(
            aggregate.get("endpoint_pairwise_mean_gain_m")
        ),
        "latency_p95_ms": _first_number(aggregate.get("latency_p95_ms")),
        "gates": gates,
    }


def _preflight_summary(report: dict[str, Any] | None) -> dict[str, Any]:
    if report is None:
        return {
            "status": None,
            "conditional_paths": [],
            "rejected_paths": [],
        }
    decision = report.get("final_decision") or {}
    routes = [
        route for route in report.get("design_routes", []) if isinstance(route, dict)
    ]
    return {
        "status": decision.get("status"),
        "conditional_paths": [
            route.get("name")
            for route in routes
            if route.get("status") == "conditional_next_design"
        ],
        "rejected_paths": [
            route.get("name") for route in routes if route.get("status") == "rejected"
        ],
    }


def _route_families(
    availability: dict[str, Any],
    failure: dict[str, Any],
    preflight: dict[str, Any],
) -> list[dict[str, Any]]:
    current_guidance_rejected = (
        availability["status"] == AVAILABILITY_REJECTED
        and failure["status"] == SUPPORT_INSUFFICIENT
    )
    route_families = [
        {
            "name": "current_route_lane_guidance",
            "status": "rejected" if current_guidance_rejected else "inconclusive",
            "reason": (
                "candidate0 preservation is solved, but endpoint diversity, "
                "PerfectTracker proxy support, reward feasibility, and latency "
                "all fail on the existing dense lane-change smoke"
                if current_guidance_rejected
                else "source diagnostics do not yet prove support insufficiency"
            ),
        },
        {
            "name": "selector_threshold_or_weight_retraining",
            "status": "blocked",
            "reason": (
                "the source failure is candidate-generation support and latency, "
                "not CAMP scoring or robust-master convexity"
            ),
        },
        {
            "name": "closed_loop_or_full36_before_offline_gate",
            "status": "blocked",
            "reason": "no offline availability or latency gate is passing",
        },
    ]
    for path in preflight["rejected_paths"]:
        route_families.append(
            {
                "name": str(path),
                "status": "rejected_by_prior_preflight",
                "reason": "already rejected in the next-design preflight artifact",
            }
        )
    return route_families


def _next_design_requirements() -> dict[str, Any]:
    return {
        "authorized_next_work": "predeclared_offline_design_gate_only",
        "must_preserve": [
            "fixed DP weights and source",
            "candidate0 or explicit first-step PerfectTracker execution behavior",
            "CAMP atom schema and affine score a_k^T w",
            "formal-seed exclusion",
            "fail-closed metadata for any default-off diagnostic",
        ],
        "must_improve_or_explain": [
            "non-Top1 dense lane-change support under progress/speed/comfort budgets",
            "endpoint or mode diversity beyond the rejected route/lane guidance",
            "hard-feasibility and DP reward/red-light recomputation for transformed candidates",
            "credible p95 latency margin before any paired replay",
        ],
        "must_not_repeat": [
            "simple K/noise scaling",
            "current route-centerline/lane-keeping guidance config",
            "selector threshold tuning over the exhausted descriptor family",
            "CAMP retraining without a passed offline no-leak gate",
        ],
        "minimum_gate_thresholds": {
            "candidate0_preservation_max_abs_xy_m": 1e-6,
            "min_endpoint_pairwise_mean_m": 0.50,
            "min_endpoint_pairwise_gain_vs_rejected_m": 0.25,
            "min_mode_count_mean": 2.0,
            "non_top1_dense_lane_change_support_rate_min": 0.25,
            "progress_loss_budget_m": 0.10,
            "target_speed_loss_budget_mps": 0.20,
            "jerk_worse_budget_mps3": 0.05,
            "lateral_worse_budget_mps2": 0.05,
            "selection_latency_p95_limit_ms": 100.0,
        },
    }


def _blocked_actions() -> dict[str, bool]:
    return {
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
    }


def _authorization_conflicts(*reports: dict[str, Any]) -> list[str]:
    blocked_keys = _blocked_actions().keys()
    conflicts: list[str] = []
    for index, report in enumerate(reports):
        decision = report.get("final_decision") or {}
        for key in blocked_keys:
            if decision.get(key):
                conflicts.append(f"source_{index}:{key}")
    return conflicts


def _decision(
    *,
    availability_summary: dict[str, Any],
    failure_summary: dict[str, Any],
    source_authorization_conflicts: list[str],
) -> dict[str, Any]:
    if source_authorization_conflicts:
        status = "candidate_generation_support_gate_source_conflict"
        next_step = "Resolve source diagnostic authorization conflicts before continuing."
    elif failure_summary["status"] == SUPPORT_INSUFFICIENT:
        status = "candidate_generation_support_gate_requires_new_design"
        next_step = (
            "Write a design-specific offline gate for a materially new "
            "candidate-generation or postprocess support mechanism before "
            "running any replay."
        )
    elif failure_summary["status"] == REWARD_GATE_SUSPECT:
        status = "candidate_generation_support_gate_requires_reward_gate_audit"
        next_step = (
            "Do not design a new generator yet; first audit whether the DP "
            "reward feasibility gate is over-rejecting otherwise supported "
            "candidates."
        )
    elif availability_summary["status"] != AVAILABILITY_REJECTED:
        status = "candidate_generation_support_gate_inconclusive"
        next_step = "Run or inspect the availability diagnostic before choosing a design."
    else:
        status = "candidate_generation_support_gate_inconclusive"
        next_step = "Inspect the failure-source diagnostic before choosing a design."
    return {
        "status": status,
        "source_authorization_conflicts": source_authorization_conflicts,
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "next_step": next_step,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    failure = report["source_summaries"]["failure_source"]
    availability = report["source_summaries"]["availability"]
    lines = [
        "# DP CAMP Candidate-Generation Support Design Gate",
        "",
        f"- Status: `{decision['status']}`",
        f"- Availability status: `{availability['status']}`",
        f"- Failure-source status: `{failure['status']}`",
        f"- Reward gate suspect: `{failure['reward_gate_suspect']}`",
        f"- Geometry/tracker insufficient: `{failure['geometry_or_tracker_support_insufficient']}`",
        f"- Latency blocked: `{failure['latency_blocked']}`",
        "",
        "## Route Families",
        "",
    ]
    for route in report["route_families"]:
        lines.append(
            f"- `{route['name']}`: `{route['status']}` - {route['reason']}"
        )
    requirements = report["next_design_requirements"]
    lines.extend(
        [
            "",
            "## Next Design Requirements",
            "",
            f"- Authorized next work: `{requirements['authorized_next_work']}`",
            "- Must preserve:",
        ]
    )
    for item in requirements["must_preserve"]:
        lines.append(f"  - {item}")
    lines.append("- Must improve or explain:")
    for item in requirements["must_improve_or_explain"]:
        lines.append(f"  - {item}")
    lines.append("- Must not repeat:")
    for item in requirements["must_not_repeat"]:
        lines.append(f"  - {item}")
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


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _path_or_none(path: Path | None) -> str | None:
    return None if path is None else str(path)


def _deep_get(
    mapping: dict[str, Any],
    keys: tuple[str, ...],
    default: Any = None,
) -> Any:
    value: Any = mapping
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return default
        value = value[key]
    return value


def _first_number(*values: Any) -> float | None:
    for value in values:
        if isinstance(value, bool) or value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number == number and number not in (float("inf"), float("-inf")):
            return number
    return None


if __name__ == "__main__":
    main()
