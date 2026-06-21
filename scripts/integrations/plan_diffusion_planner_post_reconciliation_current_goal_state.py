#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


RECON_STATUS = "post_oracle_selector_route_reconciliation_paused"
RECON_NEXT_WORK = "new_current_tick_source_predeclaration_or_keep_paused_only"

SOURCE_INVENTORY_STATUS = "post_source_visibility_runtime_inventory_no_new_source_paused"
SOURCE_INVENTORY_NEXT_WORK = "keep_selector_route_paused_or_scenario_objective_redesign_only"

SCENARIO_MATRIX_STATUS = "scenario_evidence_matrix_predeclared"
CANDIDATE_READY_STATUS = "candidate_branch_oracle_input_readiness_ready"

READY_STATUS = "post_reconciliation_current_goal_state_paused"
BLOCKED_STATUS = "post_reconciliation_current_goal_state_blocked"
AUTHORIZED_NEXT_WORK = "submit_new_current_tick_source_proposal_or_keep_paused_only"

REQUIRED_BUCKETS = (
    "normal",
    "traffic_light",
    "red_light_turn",
    "sharp_turn",
    "npc_interaction",
    "dense_scene",
    "lane_change_or_merge",
)

BLOCKED_ACTIONS = (
    "training_execution_authorized",
    "camp_retraining_authorized",
    "CAMP_retraining_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "full36_authorized",
    "Full36_authorized",
    "formal_seeds_authorized",
    "dp_modification_authorized",
    "DP_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only current goal-state refresh after post-oracle "
            "reconciliation. It consolidates the latest paused route, source "
            "inventory, scenario matrix, candidate readiness, and SafetyCost "
            "oracle evidence."
        )
    )
    parser.add_argument("--reconciliation_json", type=Path, required=True)
    parser.add_argument("--source_inventory_json", type=Path, required=True)
    parser.add_argument("--scenario_matrix_json", type=Path, required=True)
    parser.add_argument("--candidate_readiness_json", type=Path, required=True)
    parser.add_argument("--safety_cost_oracle_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--require_pass", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        reconciliation=_load_json(args.reconciliation_json),
        source_inventory=_load_json(args.source_inventory_json),
        scenario_matrix=_load_json(args.scenario_matrix_json),
        candidate_readiness=_load_json(args.candidate_readiness_json),
        safety_cost_oracle=_load_json(args.safety_cost_oracle_json),
        label=args.label,
        paths={
            "reconciliation_json": str(args.reconciliation_json),
            "source_inventory_json": str(args.source_inventory_json),
            "scenario_matrix_json": str(args.scenario_matrix_json),
            "candidate_readiness_json": str(args.candidate_readiness_json),
            "safety_cost_oracle_json": str(args.safety_cost_oracle_json),
        },
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    if args.require_pass and not report["final_decision"]["passed"]:
        raise SystemExit(1)


def build_report(
    *,
    reconciliation: dict[str, Any],
    source_inventory: dict[str, Any],
    scenario_matrix: dict[str, Any],
    candidate_readiness: dict[str, Any],
    safety_cost_oracle: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    summaries = {
        "reconciliation": _reconciliation_summary(reconciliation),
        "source_inventory": _source_inventory_summary(source_inventory),
        "scenario_matrix": _scenario_summary(scenario_matrix),
        "candidate_readiness": _candidate_summary(candidate_readiness),
        "safety_cost_oracle": _oracle_summary(safety_cost_oracle),
    }
    checks = [
        *_reconciliation_checks(summaries["reconciliation"]),
        *_source_inventory_checks(summaries["source_inventory"]),
        *_scenario_checks(summaries["scenario_matrix"]),
        *_candidate_checks(summaries["candidate_readiness"]),
        *_oracle_checks(summaries["safety_cost_oracle"]),
    ]
    decision = _final_decision(checks)
    return {
        "analysis": {
            "name": "dp_camp_post_reconciliation_current_goal_state_v1",
            "label": label,
            "role": (
                "current-state ledger after the refreshed post-oracle route "
                "reconciliation, before any new source proposal"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used_for_runtime_features": False,
            "paths": paths or {},
            "math_boundary": (
                "This state refresh creates no atom, trains no weight, and "
                "runs no selector. It records that offline candidate-branch "
                "SafetyCost opportunity exists but no deployable no-leak "
                "runtime source is open. Any future source must be a fixed "
                "current-tick finite-candidate coefficient a_k, nonnegative, "
                "hinged, or signed-split, preserving score_k(w)=a_k^T w and "
                "the convex simplex/CVaR/L2 master. No DP-side classical "
                "Benders master/subproblem, dual, or valid cut is constructed."
            ),
        },
        "state_summaries": summaries,
        "goal_state": _goal_state(summaries),
        "state_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    goal = report["goal_state"]
    lines = [
        "# Post-Reconciliation Current Goal State",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Development complete: `{decision['development_gates_complete']}`",
        f"- Deployable selector exists: `{decision['deployable_camp_dp_selector_route_exists']}`",
        f"- Selector route paused: `{decision['selector_route_paused']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Goal State",
        "",
    ]
    for key, value in goal.items():
        lines.append(f"- `{key}` = `{value}`")
    lines.extend(
        [
            "",
            "## Source Summaries",
            "",
        ]
    )
    for name, summary in report["state_summaries"].items():
        lines.append(f"### {name}")
        lines.append("")
        for key, value in summary.items():
            lines.append(f"- `{key}` = `{value}`")
        lines.append("")
    lines.extend(
        [
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report["state_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.extend(["", "## Blocked Actions", ""])
    for action, value in report["blocked_actions"].items():
        lines.append(f"- `{action}` = `{value}`")
    lines.extend(["", "## Mathematical Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _reconciliation_summary(report: dict[str, Any]) -> dict[str, Any]:
    final = _dict(report.get("final_decision"))
    return {
        "status": final.get("status"),
        "passed": bool(final.get("passed")),
        "authorized_next_work": final.get("authorized_next_work"),
        "selector_route_paused": bool(final.get("selector_route_paused")),
        "deployable_route_exists": bool(
            final.get("deployable_camp_dp_selector_route_exists")
        ),
        "repeat_selector_preflight_authorized": bool(
            final.get("repeat_selector_label_weight_preflight_authorized")
        ),
        "training_execution_authorized": bool(final.get("training_execution_authorized")),
        "blocked_action_conflicts": _blocked_conflicts(final),
    }


def _source_inventory_summary(report: dict[str, Any]) -> dict[str, Any]:
    final = _dict(report.get("final_decision"))
    return {
        "status": final.get("status"),
        "passed": bool(final.get("passed")),
        "authorized_next_work": final.get("authorized_next_work"),
        "support_source_ready": bool(final.get("support_source_ready")),
        "new_runtime_source_candidates": _string_list(
            final.get("new_runtime_source_candidates")
        ),
        "blocked_action_conflicts": _blocked_conflicts(final),
    }


def _scenario_summary(report: dict[str, Any]) -> dict[str, Any]:
    final = _dict(report.get("final_decision"))
    source = _dict(report.get("matrix_source"))
    return {
        "status": final.get("status"),
        "passed": bool(final.get("passed")),
        "authorized_next_work": final.get("authorized_next_work"),
        "missing_required_buckets": _string_list(source.get("missing_required_buckets")),
        "formal_seeds": _string_list(source.get("formal_seeds")),
        "planned_run_count": source.get("planned_run_count"),
        "blocked_action_conflicts": _blocked_conflicts(final),
    }


def _candidate_summary(report: dict[str, Any]) -> dict[str, Any]:
    final = _dict(report.get("final_decision"))
    return {
        "status": final.get("status"),
        "passed": bool(final.get("passed")),
        "authorized_next_work": final.get("authorized_next_work"),
        "logs": _get(report, "readiness_summary", "logs") or _get(report, "logs", "total"),
        "records": _get(report, "readiness_summary", "records")
        or _get(report, "records", "total"),
        "missing_example_keys": _string_list(
            _get(report, "readiness_summary", "missing_example_keys")
        ),
        "blocked_action_conflicts": _blocked_conflicts(final),
    }


def _oracle_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "opportunity_gate_passed": bool(_get(report, "opportunity_gate", "passed")),
        "logs": _get(report, "logs", "total"),
        "records": _get(report, "records", "total"),
        "formal_seed_logs": int(_get(report, "logs", "formal_seed_logs") or 0),
        "missing_required_buckets": _string_list(
            _get(report, "coverage_gaps", "missing_required_buckets")
        ),
        "hard_guarded_oracle_beats_top1_rate": _get(
            report, "overall", "record_rates", "hard_guarded_oracle_beats_top1"
        )
        or _get(report, "overall", "hard_guarded_oracle_beats_top1_rate"),
        "camp_matches_hard_guarded_oracle_rate": _get(
            report, "overall", "record_rates", "camp_matches_hard_guarded_oracle"
        )
        or _get(report, "overall", "camp_matches_hard_guarded_oracle_rate"),
    }


def _goal_state(summaries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "candidate_pool_opportunity_exists": summaries["safety_cost_oracle"][
            "opportunity_gate_passed"
        ],
        "no_new_runtime_source_available": not summaries["source_inventory"][
            "new_runtime_source_candidates"
        ],
        "selector_route_paused": summaries["reconciliation"]["selector_route_paused"],
        "deployable_camp_dp_selector_route_exists": summaries["reconciliation"][
            "deployable_route_exists"
        ],
        "formal_seeds_ready": False,
        "development_gates_complete": False,
        "stale_goal_head_detected": True,
        "corrective_note": (
            "The active goal text may mention dfbc836, but current state has "
            "advanced beyond it; use the actual synchronized HEAD from git."
        ),
    }


def _reconciliation_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("reconciliation_status", summary["status"], RECON_STATUS),
        _check_equal("reconciliation_passed", summary["passed"], True),
        _check_equal("reconciliation_next_work", summary["authorized_next_work"], RECON_NEXT_WORK),
        _check_equal("reconciliation_selector_paused", summary["selector_route_paused"], True),
        _check_equal("reconciliation_deployable_route_absent", summary["deployable_route_exists"], False),
        _check_equal("reconciliation_training_not_authorized", summary["training_execution_authorized"], False),
        _check_empty("reconciliation_no_blocked_action_conflicts", summary["blocked_action_conflicts"]),
    ]


def _source_inventory_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_inventory_status", summary["status"], SOURCE_INVENTORY_STATUS),
        _check_equal("source_inventory_passed", summary["passed"], True),
        _check_equal("source_inventory_next_work", summary["authorized_next_work"], SOURCE_INVENTORY_NEXT_WORK),
        _check_empty("source_inventory_no_new_sources", summary["new_runtime_source_candidates"]),
        _check_empty("source_inventory_no_blocked_action_conflicts", summary["blocked_action_conflicts"]),
    ]


def _scenario_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("scenario_matrix_status", summary["status"], SCENARIO_MATRIX_STATUS),
        _check_equal("scenario_matrix_passed", summary["passed"], True),
        _check_empty("scenario_matrix_missing_required_buckets", summary["missing_required_buckets"]),
        _check_empty("scenario_matrix_no_formal_seeds", summary["formal_seeds"]),
    ]


def _candidate_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("candidate_readiness_status", summary["status"], CANDIDATE_READY_STATUS),
        _check_equal("candidate_readiness_passed", summary["passed"], True),
        _check_positive("candidate_readiness_logs_positive", summary["logs"]),
        _check_positive("candidate_readiness_records_positive", summary["records"]),
        _check_empty("candidate_readiness_missing_keys_empty", summary["missing_example_keys"]),
        _check_empty("candidate_readiness_no_blocked_action_conflicts", summary["blocked_action_conflicts"]),
    ]


def _oracle_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("oracle_opportunity_passed", summary["opportunity_gate_passed"], True),
        _check_positive("oracle_logs_positive", summary["logs"]),
        _check_positive("oracle_records_positive", summary["records"]),
        _check_equal("oracle_no_formal_seed_logs", summary["formal_seed_logs"], 0),
        _check_empty("oracle_missing_required_buckets_empty", summary["missing_required_buckets"]),
    ]


def _final_decision(checks: list[dict[str, Any]]) -> dict[str, Any]:
    passed = all(check["passed"] for check in checks)
    return {
        "status": READY_STATUS if passed else BLOCKED_STATUS,
        "passed": passed,
        "selector_route_paused": passed,
        "deployable_camp_dp_selector_route_exists": False,
        "development_gates_complete": False,
        "formal_seeds_ready": False,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "next_step": (
            "Keep the selector route paused unless a materially new "
            "current-tick candidate-level source proposal is supplied and "
            "screened; do not train, replay, or promote an online selector."
            if passed
            else "Repair stale or missing current-state artifacts before continuing."
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def _blocked_conflicts(decision: dict[str, Any]) -> list[str]:
    return [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": observed == expected,
        "observed": observed,
        "expected": expected,
    }


def _check_empty(name: str, observed: list[Any]) -> dict[str, Any]:
    return {
        "name": name,
        "passed": len(observed) == 0,
        "observed": observed,
        "expected": [],
    }


def _check_positive(name: str, observed: Any) -> dict[str, Any]:
    number = _number(observed)
    return {
        "name": name,
        "passed": number is not None and number > 0,
        "observed": observed,
        "expected": ">0",
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return []


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def _get(data: Any, *path: str) -> Any:
    current = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
