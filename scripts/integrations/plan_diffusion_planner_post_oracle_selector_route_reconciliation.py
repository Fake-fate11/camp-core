#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


POST_ORACLE_STATUS = "post_oracle_deployable_gap_current_selector_misses_oracle"
POST_ORACLE_NEXT_WORK = "selector_label_weight_design_preflight_only"

SOURCE_INVENTORY_STATUS = "post_source_visibility_runtime_inventory_no_new_source_paused"
SOURCE_INVENTORY_NEXT_WORK = "keep_selector_route_paused_or_scenario_objective_redesign_only"

PAUSE_STATUS = "post_external_context_selector_route_paused"
PAUSE_NEXT_WORK = "new_proof_objective_or_new_current_tick_source_predeclaration_only"

READY_STATUS = "post_oracle_selector_route_reconciliation_paused"
BLOCKED_STATUS = "post_oracle_selector_route_reconciliation_blocked"
AUTHORIZED_NEXT_WORK = "new_current_tick_source_predeclaration_or_keep_paused_only"

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
            "Read-only reconciliation gate after a refreshed post-oracle gap. "
            "It prevents an offline oracle-opportunity result from reopening "
            "an already paused CAMP-on-DP selector route when no new no-leak "
            "runtime source is available."
        )
    )
    parser.add_argument("--post_oracle_gap_json", type=Path, required=True)
    parser.add_argument("--source_inventory_json", type=Path, required=True)
    parser.add_argument("--pause_gate_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--require_pass", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        post_oracle_gap=_load_json(args.post_oracle_gap_json),
        source_inventory=_load_json(args.source_inventory_json),
        pause_gate=_load_json(args.pause_gate_json),
        label=args.label,
        paths={
            "post_oracle_gap_json": str(args.post_oracle_gap_json),
            "source_inventory_json": str(args.source_inventory_json),
            "pause_gate_json": str(args.pause_gate_json),
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
    post_oracle_gap: dict[str, Any],
    source_inventory: dict[str, Any],
    pause_gate: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    post_oracle = _post_oracle_summary(post_oracle_gap)
    source = _source_inventory_summary(source_inventory)
    pause = _pause_summary(pause_gate)
    checks = [
        *_post_oracle_checks(post_oracle),
        *_source_inventory_checks(source),
        *_pause_checks(pause),
    ]
    decision = _final_decision(checks)
    return {
        "analysis": {
            "name": "dp_camp_post_oracle_selector_route_reconciliation_v1",
            "label": label,
            "role": (
                "read-only reconciliation between refreshed offline oracle "
                "opportunity and previously closed or paused deployable "
                "selector/source routes"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used_for_runtime_features": False,
            "paths": paths or {},
            "math_boundary": (
                "The post-oracle artifact may use closed-loop outcomes only as "
                "offline labels/evidence. It cannot become a runtime feature "
                "and cannot reopen a selector route without a new current-tick "
                "candidate-level source. Any future CAMP atom must be a fixed "
                "finite-candidate coefficient a_k, nonnegative, hinged, or "
                "signed-split, preserving score_k(w)=a_k^T w and the convex "
                "simplex/CVaR/L2 master. This gate constructs no DP-side "
                "classical Benders master/subproblem, dual, or valid cut."
            ),
        },
        "post_oracle_gap_summary": post_oracle,
        "source_inventory_summary": source,
        "pause_gate_summary": pause,
        "reconciliation_contract": _reconciliation_contract(),
        "reconciliation_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    contract = report["reconciliation_contract"]
    lines = [
        "# Post-Oracle Selector Route Reconciliation",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Selector route paused: `{decision['selector_route_paused']}`",
        "- Repeat selector label/weight preflight authorized: "
        f"`{decision['repeat_selector_label_weight_preflight_authorized']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Upstream Summaries",
        "",
        f"- Post-oracle gap: `{report['post_oracle_gap_summary']['status']}`",
        f"- Source inventory: `{report['source_inventory_summary']['status']}`",
        f"- Pause gate: `{report['pause_gate_summary']['status']}`",
        "",
        "## Reconciliation Contract",
        "",
        f"- Oracle opportunity is deployable input: `{contract['oracle_opportunity_is_deployable_input']}`",
        f"- No-new-source keeps route paused: `{contract['no_new_source_keeps_route_paused']}`",
        f"- Repeat old selector training path allowed: `{contract['repeat_old_selector_training_path_allowed']}`",
        "",
        "Allowed next work:",
        "",
    ]
    lines.extend(f"- `{item}`" for item in contract["allowed_next_work"])
    lines.extend(["", "Forbidden without new gate:", ""])
    lines.extend(f"- `{item}`" for item in contract["forbidden_without_new_gate"])
    lines.extend(
        [
            "",
            "## Checks",
            "",
            "| Check | Passed | Detail |",
            "| --- | --- | --- |",
        ]
    )
    for check in report["reconciliation_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | {_check_detail(check)} |"
        )
    lines.extend(["", "## Blocked Actions", ""])
    for action, value in report["blocked_actions"].items():
        lines.append(f"- `{action}` = `{value}`")
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


def _post_oracle_summary(report: dict[str, Any]) -> dict[str, Any]:
    final = _dict(report.get("final_decision"))
    return {
        "status": final.get("status"),
        "passed": bool(final.get("passed")),
        "authorized_next_work": final.get("authorized_next_work"),
        "current_selector_gap_closed": bool(final.get("current_selector_gap_closed")),
        "oracle_passed": bool(final.get("oracle_passed")),
        "source_inventory_passed": bool(final.get("source_inventory_passed")),
        "reasons": _string_list(final.get("reasons")),
        "blocked_action_conflicts": _blocked_conflicts(final),
    }


def _source_inventory_summary(report: dict[str, Any]) -> dict[str, Any]:
    final = _dict(report.get("final_decision"))
    new_candidates = _string_list(final.get("new_runtime_source_candidates"))
    return {
        "status": final.get("status"),
        "passed": bool(final.get("passed")),
        "authorized_next_work": final.get("authorized_next_work"),
        "no_new_runtime_source": not new_candidates,
        "new_runtime_source_candidates": new_candidates,
        "blocked_action_conflicts": _blocked_conflicts(final),
    }


def _pause_summary(report: dict[str, Any]) -> dict[str, Any]:
    final = _dict(report.get("final_decision"))
    return {
        "status": final.get("status"),
        "passed": bool(final.get("passed")),
        "authorized_next_work": final.get("authorized_next_work"),
        "selector_route_paused": bool(final.get("selector_route_paused")),
        "deployable_camp_dp_selector_route_exists": bool(
            final.get("deployable_camp_dp_selector_route_exists")
        ),
        "current_camp_dp_selector_route_rejected": bool(
            final.get("current_camp_dp_selector_route_rejected")
        ),
        "blocked_action_conflicts": _blocked_conflicts(final),
    }


def _post_oracle_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("post_oracle_status_gap_open", summary["status"], POST_ORACLE_STATUS),
        _check_equal("post_oracle_passed", summary["passed"], True),
        _check_equal(
            "post_oracle_authorizes_only_old_preflight_label",
            summary["authorized_next_work"],
            POST_ORACLE_NEXT_WORK,
        ),
        _check_equal("post_oracle_selector_gap_not_closed", summary["current_selector_gap_closed"], False),
        _check_equal("post_oracle_oracle_passed", summary["oracle_passed"], True),
        _check_empty("post_oracle_no_blocked_action_conflicts", summary["blocked_action_conflicts"]),
    ]


def _source_inventory_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_inventory_status_no_new_source", summary["status"], SOURCE_INVENTORY_STATUS),
        _check_equal("source_inventory_passed", summary["passed"], True),
        _check_equal(
            "source_inventory_authorizes_pause_only",
            summary["authorized_next_work"],
            SOURCE_INVENTORY_NEXT_WORK,
        ),
        _check_equal("source_inventory_no_new_runtime_source", summary["no_new_runtime_source"], True),
        _check_empty("source_inventory_new_candidates_empty", summary["new_runtime_source_candidates"]),
        _check_empty("source_inventory_no_blocked_action_conflicts", summary["blocked_action_conflicts"]),
    ]


def _pause_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("pause_gate_status_paused", summary["status"], PAUSE_STATUS),
        _check_equal("pause_gate_passed", summary["passed"], True),
        _check_equal("pause_gate_authorized_next_work", summary["authorized_next_work"], PAUSE_NEXT_WORK),
        _check_equal("pause_gate_selector_route_paused", summary["selector_route_paused"], True),
        _check_equal(
            "pause_gate_no_deployable_selector_route",
            summary["deployable_camp_dp_selector_route_exists"],
            False,
        ),
        _check_equal(
            "pause_gate_current_route_rejected",
            summary["current_camp_dp_selector_route_rejected"],
            True,
        ),
        _check_empty("pause_gate_no_blocked_action_conflicts", summary["blocked_action_conflicts"]),
    ]


def _reconciliation_contract() -> dict[str, Any]:
    return {
        "oracle_opportunity_is_deployable_input": False,
        "no_new_source_keeps_route_paused": True,
        "repeat_old_selector_training_path_allowed": False,
        "reason": (
            "A refreshed offline oracle opportunity is not a new runtime "
            "candidate feature. Without a new no-leak source, repeating the "
            "old label/weight or offline convex selector route would not "
            "address the deployability gap."
        ),
        "allowed_next_work": [
            "new_current_tick_candidate_level_source_predeclaration_only",
            "new_proof_objective_predeclaration_only",
            "keep_current_selector_route_paused",
        ],
        "forbidden_without_new_gate": [
            "repeat_selector_label_weight_preflight_as_if_new",
            "offline_convex_selector_training_execution",
            "CAMP_retraining",
            "closed_loop_smoke_or_replay",
            "online_selector_promotion",
            "Full36",
            "formal_seeds",
            "DP_modification_or_retraining",
            "DP_side_classical_Benders_claim",
        ],
    }


def _final_decision(checks: list[dict[str, Any]]) -> dict[str, Any]:
    passed = all(check["passed"] for check in checks)
    return {
        "status": READY_STATUS if passed else BLOCKED_STATUS,
        "passed": passed,
        "selector_route_paused": passed,
        "deployable_camp_dp_selector_route_exists": False,
        "repeat_selector_label_weight_preflight_authorized": False,
        "offline_convex_selector_training_authorized": False,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "next_step": (
            "Keep the current selector route paused. Continue only with a new "
            "current-tick candidate-level source predeclaration or a proof "
            "objective predeclaration; do not repeat the old label/weight path."
            if passed
            else "Repair the upstream post-oracle, source-inventory, or pause gate evidence before reconciling this route."
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


def _check_detail(check: dict[str, Any]) -> str:
    if "expected" in check:
        return f"`observed={check.get('observed')}; expected={check.get('expected')}`"
    return ""


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


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
