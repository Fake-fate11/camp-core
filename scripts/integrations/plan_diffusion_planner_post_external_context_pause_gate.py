#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEVELOPMENT_STATUS = "current_development_gate_state_no_deployable_route_yet"
DEVELOPMENT_NEXT_WORK = "scenario_objective_redesign_or_external_source_discovery_only"
CONTRACT_STATUS = "scenario_objective_redesign_boundary_and_external_source_contract_ready"
CONTRACT_NEXT_WORK = "external_source_visibility_inventory_or_pause_only"
SOURCE_CLOSURE_STATUS = "post_external_context_source_route_closed"
SOURCE_CLOSURE_NEXT_WORK = "scenario_objective_redesign_or_pause_only"

READY_STATUS = "post_external_context_selector_route_paused"
BLOCKED_STATUS = "post_external_context_pause_gate_blocked"
AUTHORIZED_NEXT_WORK = "new_proof_objective_or_new_current_tick_source_predeclaration_only"

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
            "Read-only pause gate after external-context source closure. It "
            "states whether the current CAMP-on-DP selector route must remain "
            "paused under the fixed DP boundary."
        )
    )
    parser.add_argument("--development_gate_state_json", type=Path, required=True)
    parser.add_argument("--scenario_objective_contract_json", type=Path, required=True)
    parser.add_argument("--post_external_context_closure_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        development_gate_state=_load_json(args.development_gate_state_json),
        scenario_objective_contract=_load_json(args.scenario_objective_contract_json),
        post_external_context_closure=_load_json(args.post_external_context_closure_json),
        label=args.label,
        paths={
            "development_gate_state_json": str(args.development_gate_state_json),
            "scenario_objective_contract_json": str(args.scenario_objective_contract_json),
            "post_external_context_closure_json": str(args.post_external_context_closure_json),
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
    development_gate_state: dict[str, Any],
    scenario_objective_contract: dict[str, Any],
    post_external_context_closure: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    development = _development_summary(development_gate_state)
    contract = _contract_summary(scenario_objective_contract)
    source_closure = _source_closure_summary(post_external_context_closure)
    reopening_contract = _reopening_contract()
    checks = [
        *_development_checks(development),
        *_contract_checks(contract),
        *_source_closure_checks(source_closure),
    ]
    decision = _final_decision(checks)
    return {
        "analysis": {
            "name": "dp_camp_post_external_context_pause_gate_v1",
            "label": label,
            "role": (
                "read-only pause gate after all currently inspected fixed-DP "
                "CAMP selector/source routes have failed to produce a "
                "deployable no-leak certificate"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used_for_runtime_features": False,
            "paths": paths or {},
            "math_boundary": (
                "This gate creates no atom and runs no selector. It only "
                "records that the current fixed-DP finite-candidate selector "
                "route is paused. A future runtime CAMP feature must be a "
                "current-tick finite-candidate coefficient a_k that is "
                "nonnegative, hinged, or signed-split, so score_k(w)=a_k^T w "
                "remains affine and the simplex/CVaR/L2 master remains convex. "
                "No DP-side classical Benders master/subproblem, dual, or cut "
                "is constructed or claimed."
            ),
        },
        "development_gate_summary": development,
        "scenario_objective_contract_summary": contract,
        "post_external_context_closure_summary": source_closure,
        "reopening_contract": reopening_contract,
        "pause_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _development_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "development_gates_complete": decision.get("development_gates_complete"),
        "formal_seeds_ready": decision.get("formal_seeds_ready"),
        "current_camp_dp_selector_route_rejected": bool(
            decision.get("current_camp_dp_selector_route_rejected")
        ),
        "blocked_action_conflicts": _blocked_conflicts(decision),
    }


def _contract_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    objective = report.get("objective_redesign_boundary") or {}
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "scenario_objective_redesign_only_sufficient": bool(
            decision.get("scenario_objective_redesign_only_sufficient")
        ),
        "objective_boundary_sufficient": bool(
            objective.get("objective_only_redesign_sufficient_for_deployable_route")
        ),
        "blocked_action_conflicts": _blocked_conflicts(decision),
    }


def _source_closure_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "external_context_source_route_closed": bool(
            decision.get("external_context_source_route_closed")
        ),
        "current_camp_dp_selector_route_rejected": bool(
            decision.get("current_camp_dp_selector_route_rejected")
        ),
        "failed_checks": list(decision.get("failed_checks") or []),
        "blocked_action_conflicts": _blocked_conflicts(decision),
    }


def _reopening_contract() -> dict[str, Any]:
    return {
        "status": "selector_route_reopening_requires_new_predeclared_evidence",
        "selector_route_paused": True,
        "objective_only_reopening_allowed": False,
        "allowed_next_work": [
            "proof_objective_predeclaration_only",
            "new_current_tick_candidate_level_source_predeclaration_only",
            "keep_current_selector_route_paused",
        ],
        "forbidden_without_new_gate": [
            "closed_loop_replay",
            "online_selector_promotion",
            "Full36",
            "formal_seeds",
            "CAMP_retraining",
            "DP_modification",
            "classic_Benders_claim",
        ],
        "new_source_acceptance_requirements": [
            "visible_at_current_tick_before_selection",
            "finite_candidate_level_or_deterministically_joinable_to_candidates",
            "non_equivalent_to_closed_source_or_atom_families",
            "not_a_future_outcome_label_or_safety_cost_proxy",
            "atomizable_as_nonnegative_hinge_or_signed_split_coefficient",
            "preserves_affine_score_and_convex_master",
            "default_off_latency_plan",
            "existing_log_materiality_and_noninferiority_certificate_before_replay",
        ],
        "proof_objective_boundary": (
            "A new proof objective may define better evaluation evidence, but "
            "it does not by itself create a deployable selector input."
        ),
    }


def _development_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("development_status", summary["status"], DEVELOPMENT_STATUS),
        _check_equal("development_passed", summary["passed"], True),
        _check_equal(
            "development_authorized_next_work",
            summary["authorized_next_work"],
            DEVELOPMENT_NEXT_WORK,
        ),
        _check_equal(
            "development_gates_not_complete",
            summary["development_gates_complete"],
            False,
        ),
        _check_equal("formal_seeds_not_ready", summary["formal_seeds_ready"], False),
        _check_equal(
            "development_selector_route_rejected",
            summary["current_camp_dp_selector_route_rejected"],
            True,
        ),
        _check_empty("development_no_blocked_actions", summary["blocked_action_conflicts"]),
    ]


def _contract_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("contract_status", summary["status"], CONTRACT_STATUS),
        _check_equal("contract_passed", summary["passed"], True),
        _check_equal(
            "contract_authorized_next_work",
            summary["authorized_next_work"],
            CONTRACT_NEXT_WORK,
        ),
        _check_equal(
            "objective_only_not_deployable",
            summary["scenario_objective_redesign_only_sufficient"],
            False,
        ),
        _check_equal(
            "objective_boundary_not_deployable",
            summary["objective_boundary_sufficient"],
            False,
        ),
        _check_empty("contract_no_blocked_actions", summary["blocked_action_conflicts"]),
    ]


def _source_closure_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_closure_status", summary["status"], SOURCE_CLOSURE_STATUS),
        _check_equal("source_closure_passed", summary["passed"], True),
        _check_equal(
            "source_closure_authorized_next_work",
            summary["authorized_next_work"],
            SOURCE_CLOSURE_NEXT_WORK,
        ),
        _check_equal(
            "external_context_source_route_closed",
            summary["external_context_source_route_closed"],
            True,
        ),
        _check_equal(
            "source_closure_selector_route_rejected",
            summary["current_camp_dp_selector_route_rejected"],
            True,
        ),
        _check_empty("source_closure_failed_checks_empty", summary["failed_checks"]),
        _check_empty("source_closure_no_blocked_actions", summary["blocked_action_conflicts"]),
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
        "current_camp_dp_selector_route_rejected": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "next_step": (
            "Keep the current CAMP-DP selector route paused unless a new proof "
            "objective or a genuinely new current-tick candidate-level source "
            "is predeclared and passes its own no-leak gate."
            if passed
            else "Repair the failed upstream gate before pausing or reopening this route."
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    reopening = report["reopening_contract"]
    lines = [
        "# Post External-Context CAMP-DP Pause Gate",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Selector route paused: `{decision['selector_route_paused']}`",
        "- Deployable CAMP-DP selector route exists: "
        f"`{decision['deployable_camp_dp_selector_route_exists']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Upstream Summaries",
        "",
        f"- Development gate: `{report['development_gate_summary']['status']}`",
        f"- Scenario/objective contract: `{report['scenario_objective_contract_summary']['status']}`",
        f"- External-context source closure: `{report['post_external_context_closure_summary']['status']}`",
        "",
        "## Reopening Contract",
        "",
        f"- Status: `{reopening['status']}`",
        f"- Objective-only reopening allowed: `{reopening['objective_only_reopening_allowed']}`",
        "",
        "Allowed next work:",
        "",
    ]
    for item in reopening["allowed_next_work"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "Forbidden without a new gate:", ""])
    for item in reopening["forbidden_without_new_gate"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "New source acceptance requirements:", ""])
    for item in reopening["new_source_acceptance_requirements"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "## Pause Checks",
            "",
            "| Check | Passed | Detail |",
            "| --- | --- | --- |",
        ]
    )
    for check in report["pause_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | {_check_detail(check)} |"
        )
    lines.extend(["", "## Blocked Actions", ""])
    for action in BLOCKED_ACTIONS:
        lines.append(f"- `{action}` = `{decision[action]}`")
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
