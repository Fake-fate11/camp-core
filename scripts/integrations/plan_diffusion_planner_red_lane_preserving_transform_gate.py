#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


SUPPORT_GATE_READY = "candidate_generation_support_gate_requires_new_design"
READY_STATUS = "red_lane_preserving_transform_gate_ready"
BLOCKED_STATUS = "red_lane_preserving_transform_gate_blocked"
CONFLICT_STATUS = "red_lane_preserving_transform_gate_source_conflict"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only design gate for a red/lane-preserving transformed "
            "candidate mechanism after the H-anchor splice family failed. It "
            "consumes existing diagnostics only and does not run DP."
        )
    )
    parser.add_argument("--candidate_support_gate_json", type=Path, required=True)
    parser.add_argument("--splice_reason_json", type=Path, required=True)
    parser.add_argument("--h_anchor_grid_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        candidate_support_gate=_load_json(args.candidate_support_gate_json),
        splice_reason=_load_json(args.splice_reason_json),
        h_anchor_grid=_load_json(args.h_anchor_grid_json),
        label=args.label,
        paths={
            "candidate_support_gate_json": str(args.candidate_support_gate_json),
            "splice_reason_json": str(args.splice_reason_json),
            "h_anchor_grid_json": str(args.h_anchor_grid_json),
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
    candidate_support_gate: dict[str, Any],
    splice_reason: dict[str, Any],
    h_anchor_grid: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    support = _support_summary(candidate_support_gate)
    reason = _splice_reason_summary(splice_reason)
    grid = _grid_summary(h_anchor_grid)
    conflicts = _authorization_conflicts(candidate_support_gate, splice_reason, h_anchor_grid)
    preconditions = _preconditions(support, reason, grid)
    decision = _decision(conflicts, preconditions)
    return {
        "analysis": {
            "name": "dp_camp_red_lane_preserving_transform_design_gate_v1",
            "label": label,
            "role": (
                "read-only gate for a materially new transformed-candidate "
                "screen that targets the red/lane hard-feasibility failure"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_leakage": False,
            "math_boundary": (
                "This gate does not optimize trajectory coordinates or construct "
                "a DP-side Benders subproblem. It only authorizes a future "
                "offline recompute screen over fixed current-tick snapshots. If "
                "a transformed candidate is later added, it is a deterministic "
                "finite candidate-set transform; CAMP still sees fixed finite "
                "candidate atoms and scores remain affine a_k^T w with the "
                "simplex/CVaR/L2 master convex for that fixed set."
            ),
            "paths": paths or {},
        },
        "source_summaries": {
            "candidate_support_gate": support,
            "splice_reason": reason,
            "h_anchor_grid": grid,
        },
        "preconditions": preconditions,
        "design_contract": _design_contract(),
        "offline_recompute_gate": _offline_recompute_gate(),
        "blocked_actions": _blocked_actions(),
        "source_authorization_conflicts": conflicts,
        "final_decision": decision,
    }


def _support_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    routes = {
        route.get("name"): route.get("status")
        for route in report.get("route_families", [])
        if isinstance(route, dict)
    }
    return {
        "status": decision.get("status"),
        "next_step": decision.get("next_step"),
        "current_route_lane_guidance": routes.get("current_route_lane_guidance"),
        "selector_threshold_or_weight_retraining": routes.get(
            "selector_threshold_or_weight_retraining"
        ),
        "closed_loop_or_full36_before_offline_gate": routes.get(
            "closed_loop_or_full36_before_offline_gate"
        ),
        "authorized_next_work": _deep_get(
            report,
            ("next_design_requirements", "authorized_next_work"),
        ),
    }


def _splice_reason_summary(report: dict[str, Any]) -> dict[str, Any]:
    records = report.get("records") or {}
    latency = report.get("latency") or {}
    target_latency = latency.get("all_target_records") or {}
    lower_reasons = records.get("lower_union_red_hard_infeasible_reason_counts") or {}
    hard_reasons = records.get("hard_infeasible_reason_counts") or {}
    no_budget_classes = records.get("no_budget_class_counts") or {}
    return {
        "analysis_name": _deep_get(report, ("analysis", "name")),
        "selection_effect_values": records.get("selection_effect_values"),
        "online_selector_change_values": records.get("online_selector_change_values"),
        "target_records": _int_or_none(records.get("target_records")),
        "changed_records": _int_or_none(records.get("changed")),
        "no_budget_records": _int_or_none(records.get("no_budget")),
        "no_hard_feasible_no_budget_records": _int_or_none(
            no_budget_classes.get("no_hard_feasible_transformed_candidates")
        ),
        "hard_infeasible_reason_counts": hard_reasons,
        "lower_union_red_hard_infeasible_reason_counts": lower_reasons,
        "red_or_lane_hard_blocker_count": int(
            _number(lower_reasons.get("dp_red_light"), 0)
            + _number(lower_reasons.get("dp_lane_crossing"), 0)
        ),
        "target_latency_p95_ms": _number(target_latency.get("p95")),
    }


def _grid_summary(report: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in report.get("rows", []) if isinstance(row, dict)]
    anchors = [int(row.get("anchor_steps")) for row in rows if row.get("anchor_steps") is not None]
    lower_red = [_number(row.get("lower_union_red_count"), 0.0) for row in rows]
    lower_hard = [
        _number(row.get("lower_union_red_hard_feasible_count"), 0.0)
        for row in rows
    ]
    lower_reasons = Counter()
    for row in rows:
        lower_reasons.update(row.get("lower_union_red_hard_infeasibility_reason_counts") or {})
    return {
        "analysis": report.get("analysis"),
        "camp_commit": report.get("camp_commit"),
        "dp_commit": report.get("dp_commit"),
        "rows": len(rows),
        "anchor_steps": sorted(set(anchors)),
        "max_lower_union_red_count": max(lower_red) if lower_red else 0.0,
        "max_lower_union_red_hard_feasible_count": max(lower_hard) if lower_hard else 0.0,
        "all_rows_zero_lower_red_hard_feasible": bool(rows)
        and max(lower_hard, default=0.0) == 0.0,
        "lower_union_red_hard_infeasibility_reason_counts": dict(lower_reasons),
        "all_shadow_changed_snapshots_zero": bool(rows)
        and all(_number(row.get("shadow_changed_snapshots"), 0.0) == 0.0 for row in rows),
    }


def _preconditions(
    support: dict[str, Any],
    reason: dict[str, Any],
    grid: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "name": "candidate_support_gate_requires_new_design",
            "passed": support["status"] == SUPPORT_GATE_READY,
            "evidence": support["status"],
        },
        {
            "name": "current_route_lane_guidance_rejected",
            "passed": support["current_route_lane_guidance"] == "rejected",
            "evidence": support["current_route_lane_guidance"],
        },
        {
            "name": "splice_shadow_was_shadow_only",
            "passed": reason["selection_effect_values"] == [False]
            and reason["online_selector_change_values"] == [False],
            "evidence": {
                "selection_effect_values": reason["selection_effect_values"],
                "online_selector_change_values": reason["online_selector_change_values"],
            },
        },
        {
            "name": "blocked_records_are_hard_feasibility_not_budget_tuning",
            "passed": (
                reason["no_budget_records"] is not None
                and reason["no_hard_feasible_no_budget_records"] is not None
                and reason["no_hard_feasible_no_budget_records"]
                >= max(1, reason["no_budget_records"] - 1)
            ),
            "evidence": {
                "no_budget_records": reason["no_budget_records"],
                "no_hard_feasible_no_budget_records": reason[
                    "no_hard_feasible_no_budget_records"
                ],
            },
        },
        {
            "name": "red_or_lane_are_primary_hard_blockers",
            "passed": reason["red_or_lane_hard_blocker_count"] > 0,
            "evidence": reason["lower_union_red_hard_infeasible_reason_counts"],
        },
        {
            "name": "h_anchor_grid_failed_lower_red_hard_feasibility",
            "passed": grid["all_rows_zero_lower_red_hard_feasible"],
            "evidence": {
                "rows": grid["rows"],
                "anchor_steps": grid["anchor_steps"],
                "max_lower_union_red_hard_feasible_count": grid[
                    "max_lower_union_red_hard_feasible_count"
                ],
            },
        },
        {
            "name": "h_anchor_grid_still_had_lower_red_materiality",
            "passed": grid["max_lower_union_red_count"] > 0,
            "evidence": grid["max_lower_union_red_count"],
        },
    ]


def _design_contract() -> dict[str, Any]:
    return {
        "design_name": "world_frame_donor_tail_bridge",
        "authorized_next_implementation": (
            "offline_world_frame_donor_tail_bridge_recompute_screen"
        ),
        "material_difference_from_rejected_h_anchor_splice": [
            (
                "after the bridge interval, the donor tail must remain in the "
                "donor/world frame rather than being translated into the "
                "selected H-anchor frame"
            ),
            (
                "the selected near-term prefix is preserved for first-step and "
                "PerfectTracker command behavior, but red/lane claims come only "
                "from recomputed DP reward and hard feasibility"
            ),
            (
                "H-anchor length tuning of the old donor-offset splice is not "
                "part of this design"
            ),
        ],
        "fixed_snapshot_inputs": [
            "selected candidate trajectory",
            "lower-red donor trajectory",
            "reward input tensors",
            "red-route points",
            "PerfectTracker current state",
        ],
        "transform_family": {
            "preserve_selected_prefix_steps": "predeclared grid, minimum includes first step",
            "donor_join_step": "predeclared grid after preserved prefix",
            "bridge": "deterministic smoothstep or C2 interpolation in world coordinates",
            "tail": "absolute donor/world-frame suffix after join",
        },
        "no_claim_without_recompute": [
            "red-light improvement",
            "lane validity",
            "hard feasibility",
            "PerfectTracker comfort",
            "closed-loop SafetyCost",
        ],
    }


def _offline_recompute_gate() -> dict[str, Any]:
    return {
        "authorized_scope": "offline_fixed_snapshot_recompute_only",
        "must_recompute": [
            "Savitzky-Golay/postprocess path used by replay",
            "DP reward hard feasibility and reasons",
            "near-horizon and full-horizon red-light costs",
            "PerfectTracker command and open-loop comfort proxies",
            "progress and smoothness losses against selected baseline",
        ],
        "minimum_acceptance": {
            "formal_seeds_present": False,
            "selection_effect": False,
            "online_selector_change": False,
            "lower_red_hard_feasible_snapshot_rate_min": 0.25,
            "lower_red_progress_feasible_snapshot_rate_min": 0.25,
            "candidate0_or_first_step_preservation_required": True,
            "must_improve_over_h_anchor_grid_lower_red_hard_feasible_count": True,
            "must_report_latency_projection": True,
        },
        "reject_if": [
            "all gains come from loosening hard feasibility",
            "red/lane hard infeasibility remains the dominant blocker",
            "latency cannot plausibly fit under the 100 ms p95 gate",
            "the transform needs DP weight/source changes",
            "the transform needs future closed-loop outcomes at selection time",
        ],
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
    blocked = _blocked_actions().keys()
    conflicts: list[str] = []
    for index, report in enumerate(reports):
        decision = report.get("final_decision") or {}
        for key in blocked:
            if decision.get(key):
                conflicts.append(f"source_{index}:{key}")
    return conflicts


def _decision(
    conflicts: list[str],
    preconditions: list[dict[str, Any]],
) -> dict[str, Any]:
    failed = [item["name"] for item in preconditions if not item["passed"]]
    if conflicts:
        status = CONFLICT_STATUS
        next_step = "Resolve source authorization conflicts before continuing."
    elif failed:
        status = BLOCKED_STATUS
        next_step = (
            "Do not implement the world-frame bridge screen until failed "
            "preconditions are resolved or the sources are inspected manually."
        )
    else:
        status = READY_STATUS
        next_step = (
            "Implement only the offline world-frame donor-tail bridge recompute "
            "screen over fixed non-formal snapshots; do not run replay."
        )
    return {
        "status": status,
        "failed_preconditions": failed,
        "source_authorization_conflicts": conflicts,
        "authorized_implementation": (
            "offline_world_frame_donor_tail_bridge_recompute_screen"
            if status == READY_STATUS
            else None
        ),
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "next_step": next_step,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    reason = report["source_summaries"]["splice_reason"]
    grid = report["source_summaries"]["h_anchor_grid"]
    lines = [
        "# DP CAMP Red/Lane-Preserving Transform Design Gate",
        "",
        f"- Status: `{decision['status']}`",
        f"- Authorized implementation: `{decision['authorized_implementation']}`",
        f"- Failed preconditions: `{decision['failed_preconditions']}`",
        "",
        "## Evidence",
        "",
        f"- Splice target records: `{reason['target_records']}`",
        f"- No-budget records: `{reason['no_budget_records']}`",
        f"- No-budget records without hard-feasible transforms: `{reason['no_hard_feasible_no_budget_records']}`",
        f"- Lower-red hard-infeasible reasons: `{reason['lower_union_red_hard_infeasible_reason_counts']}`",
        f"- H-anchor rows: `{grid['rows']}`",
        f"- H-anchor max lower-red hard-feasible count: `{grid['max_lower_union_red_hard_feasible_count']}`",
        "",
        "## Design Contract",
        "",
        f"- Design: `{report['design_contract']['design_name']}`",
        "- Differences from rejected H-anchor splice:",
    ]
    for item in report["design_contract"]["material_difference_from_rejected_h_anchor_splice"]:
        lines.append(f"  - {item}")
    lines.extend(
        [
            "",
            "## Offline Gate",
            "",
            f"- Authorized scope: `{report['offline_recompute_gate']['authorized_scope']}`",
            "- Must recompute:",
        ]
    )
    for item in report["offline_recompute_gate"]["must_recompute"]:
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


def _deep_get(mapping: dict[str, Any], keys: tuple[str, ...]) -> Any:
    value: Any = mapping
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def _number(value: Any, default: float | None = None) -> float | None:
    if isinstance(value, bool) or value is None:
        return default
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if result != result or result in (float("inf"), float("-inf")):
        return default
    return result


def _int_or_none(value: Any) -> int | None:
    number = _number(value)
    return None if number is None else int(number)


if __name__ == "__main__":
    main()
