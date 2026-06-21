#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SOURCE_INVENTORY_STATUS = "external_source_visibility_inventory_has_design_candidate"
ROUTE_SPEED_GAP_STATUS = "external_context_materiality_gap_diagnosed"
SIGNAL_COUNTERFACTUAL_STATUS = "external_context_atom_outcome_counterfactual_ready"
ALTERNATIVE_SEARCH_STATUS = "external_context_alternative_atom_search_rejected"

READY_STATUS = "post_external_context_source_route_closed"
BLOCKED_STATUS = "post_external_context_source_route_closure_blocked"
AUTHORIZED_NEXT_WORK = "scenario_objective_redesign_or_pause_only"

REQUIRED_SOURCE_CANDIDATES = (
    "traffic_signal_phase_timing_or_right_of_way_state",
    "route_speed_limit_and_control_context",
)
ROUTE_SPEED_CLOSURE_GAPS = (
    "route_speed_context_available_but_no_candidate_excess",
    "route_speed_availability_constant",
    "nonmaterial_constant_speed_limit",
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
            "Read-only closure gate after external-context source discovery. "
            "It consumes the source visibility inventory plus route-speed, "
            "signal, and alternative-atom negative evidence."
        )
    )
    parser.add_argument("--source_inventory_json", type=Path, required=True)
    parser.add_argument("--route_speed_gap_json", type=Path, required=True)
    parser.add_argument("--signal_counterfactual_json", type=Path, required=True)
    parser.add_argument("--alternative_search_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        source_inventory=_load_json(args.source_inventory_json),
        route_speed_gap=_load_json(args.route_speed_gap_json),
        signal_counterfactual=_load_json(args.signal_counterfactual_json),
        alternative_search=_load_json(args.alternative_search_json),
        label=args.label,
        paths={
            "source_inventory_json": str(args.source_inventory_json),
            "route_speed_gap_json": str(args.route_speed_gap_json),
            "signal_counterfactual_json": str(args.signal_counterfactual_json),
            "alternative_search_json": str(args.alternative_search_json),
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


def build_report(
    *,
    source_inventory: dict[str, Any],
    route_speed_gap: dict[str, Any],
    signal_counterfactual: dict[str, Any],
    alternative_search: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source = _source_summary(source_inventory)
    route_speed = _route_speed_summary(route_speed_gap)
    signal = _signal_summary(signal_counterfactual)
    alternative = _alternative_summary(alternative_search)
    checks = [
        *_source_checks(source),
        *_route_speed_checks(route_speed),
        *_signal_checks(signal),
        *_alternative_checks(alternative),
    ]
    decision = _decision(checks)
    return {
        "analysis": {
            "name": "dp_camp_post_external_context_source_closure_v1",
            "label": label,
            "role": (
                "read-only closure gate for the external-context source route "
                "after route-speed and signal/right-of-way evidence failed to "
                "produce a deployable no-leak selector certificate"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used_for_runtime_features": False,
            "paths": paths or {},
            "math_boundary": (
                "This gate reads prior JSON artifacts only. It creates no atom, "
                "runs no DP replay, trains no weights, and changes no selector. "
                "Any future runtime CAMP feature must still be a fixed "
                "current-tick finite-candidate coefficient a_k, nonnegative, "
                "hinged, or signed-split, so score_k(w)=a_k^T w remains affine "
                "and the simplex/CVaR/L2 master remains convex. No DP-side "
                "classical Benders master/subproblem, dual, or cut is claimed."
            ),
        },
        "source_inventory_summary": source,
        "route_speed_summary": route_speed,
        "signal_summary": signal,
        "alternative_search_summary": alternative,
        "closure_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _source_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    candidates = list(decision.get("design_candidate_names") or [])
    rejected = report.get("rejected_visible_sources")
    if not isinstance(rejected, list):
        rejected = []
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "design_candidate_names": candidates,
        "missing_required_candidates": [
            name for name in REQUIRED_SOURCE_CANDIDATES if name not in candidates
        ],
        "blocked_action_conflicts": _blocked_conflicts(decision),
        "rejected_visible_sources": [
            row.get("name")
            for row in rejected
            if isinstance(row, dict) and row.get("name")
        ],
    }


def _route_speed_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    gap_names = list(decision.get("gap_names") or [])
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "gap_names": gap_names,
        "has_all_closure_gaps": all(name in gap_names for name in ROUTE_SPEED_CLOSURE_GAPS),
        "blocked_action_conflicts": _blocked_conflicts(decision),
    }


def _signal_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    summary = report.get("summary") or {}
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "promotion_authorized": bool(decision.get("promotion_authorized")),
        "tiny_counterfactual_noninferior": bool(
            decision.get("tiny_counterfactual_noninferior")
        ),
        "guarded_tiny_counterfactual_noninferior": bool(
            decision.get("guarded_tiny_counterfactual_noninferior")
        ),
        "selected_preserving_noninferior": bool(
            decision.get("selected_preserving_guarded_tiny_counterfactual_noninferior")
        ),
        "selected_preserving_changed_records": int(
            summary.get("selected_preserving_guarded_changed_records", -1)
        ),
        "selected_preserving_better_records": int(
            summary.get("selected_preserving_guarded_atom_best_better_records", -1)
        ),
        "guarded_changed_records": int(summary.get("guarded_changed_records", -1)),
        "guarded_delta_mean": summary.get("guarded_atom_best_minus_selected_cost_mean"),
        "blocked_action_conflicts": _blocked_conflicts(decision),
    }


def _alternative_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    ranked = report.get("ranked_candidates")
    if not isinstance(ranked, list):
        ranked = []
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "primary_gap": decision.get("primary_gap"),
        "passing_candidates": list(decision.get("passing_candidates") or []),
        "best_changed_records": max(
            [int(row.get("changed_records", 0)) for row in ranked if isinstance(row, dict)]
            or [0]
        ),
        "best_changed_all_gate_records": max(
            [
                int(row.get("changed_all_gate_records", 0))
                for row in ranked
                if isinstance(row, dict)
            ]
            or [0]
        ),
        "blocked_action_conflicts": _blocked_conflicts(decision),
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_inventory_status", source["status"], SOURCE_INVENTORY_STATUS),
        _check_equal("source_inventory_passed", source["passed"], True),
        _check_empty("source_inventory_has_required_candidates", source["missing_required_candidates"]),
        _check_empty("source_inventory_no_blocked_actions", source["blocked_action_conflicts"]),
    ]


def _route_speed_checks(route_speed: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("route_speed_gap_status", route_speed["status"], ROUTE_SPEED_GAP_STATUS),
        _check_equal("route_speed_gap_diagnosed", route_speed["passed"], True),
        _check_equal("route_speed_has_closure_gaps", route_speed["has_all_closure_gaps"], True),
        _check_empty("route_speed_no_blocked_actions", route_speed["blocked_action_conflicts"]),
    ]


def _signal_checks(signal: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("signal_counterfactual_status", signal["status"], SIGNAL_COUNTERFACTUAL_STATUS),
        _check_equal("signal_counterfactual_passed", signal["passed"], True),
        _check_equal("signal_promotion_not_authorized", signal["promotion_authorized"], False),
        _check_equal("signal_raw_tiny_not_noninferior", signal["tiny_counterfactual_noninferior"], False),
        _check_equal(
            "signal_guarded_tiny_not_noninferior",
            signal["guarded_tiny_counterfactual_noninferior"],
            False,
        ),
        _check_equal(
            "signal_selected_preserving_changes_zero_records",
            signal["selected_preserving_changed_records"],
            0,
        ),
        _check_equal(
            "signal_selected_preserving_improves_zero_records",
            signal["selected_preserving_better_records"],
            0,
        ),
        _check_empty("signal_no_blocked_actions", signal["blocked_action_conflicts"]),
    ]


def _alternative_checks(alternative: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("alternative_search_status", alternative["status"], ALTERNATIVE_SEARCH_STATUS),
        _check_equal("alternative_search_not_passed", alternative["passed"], False),
        _check_equal(
            "alternative_search_gap",
            alternative["primary_gap"],
            "no_alternative_external_context_atom_certificate_found",
        ),
        _check_empty("alternative_search_no_passing_candidates", alternative["passing_candidates"]),
        _check_equal("alternative_search_changes_zero_records", alternative["best_changed_records"], 0),
        _check_equal(
            "alternative_search_all_gate_zero_records",
            alternative["best_changed_all_gate_records"],
            0,
        ),
        _check_empty("alternative_no_blocked_actions", alternative["blocked_action_conflicts"]),
    ]


def _decision(checks: list[dict[str, Any]]) -> dict[str, Any]:
    passed = all(check["passed"] for check in checks)
    return {
        "status": READY_STATUS if passed else BLOCKED_STATUS,
        "passed": passed,
        "external_context_source_route_closed": passed,
        "current_camp_dp_selector_route_rejected": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "next_step": (
            "Do not reopen external-context signal/right-of-way or route-speed "
            "atomization from current evidence. Continue only with "
            "scenario/objective redesign or keep the current selector route paused."
            if passed
            else "Repair or refresh the failed external-context evidence before closure."
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Post External-Context Source Closure",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- External-context source route closed: `{decision['external_context_source_route_closed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Source Inventory",
        "",
        f"- Status: `{report['source_inventory_summary']['status']}`",
        f"- Design candidates: `{report['source_inventory_summary']['design_candidate_names']}`",
        "",
        "## Route-Speed Evidence",
        "",
        f"- Status: `{report['route_speed_summary']['status']}`",
        f"- Gaps: `{report['route_speed_summary']['gap_names']}`",
        "",
        "## Signal Evidence",
        "",
        f"- Status: `{report['signal_summary']['status']}`",
        f"- Promotion authorized: `{report['signal_summary']['promotion_authorized']}`",
        f"- Selected-preserving changed records: `{report['signal_summary']['selected_preserving_changed_records']}`",
        f"- Selected-preserving better records: `{report['signal_summary']['selected_preserving_better_records']}`",
        "",
        "## Alternative Atom Search",
        "",
        f"- Status: `{report['alternative_search_summary']['status']}`",
        f"- Primary gap: `{report['alternative_search_summary']['primary_gap']}`",
        f"- Passing candidates: `{report['alternative_search_summary']['passing_candidates']}`",
        f"- Best changed records: `{report['alternative_search_summary']['best_changed_records']}`",
        "",
        "## Closure Checks",
        "",
        "| Check | Passed | Detail |",
        "| --- | --- | --- |",
    ]
    for check in report["closure_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | {_check_detail(check)} |"
        )
    lines.extend(["", "## Mathematical Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


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
    return f"`observed={check.get('observed')}; expected={check.get('expected')}`"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
