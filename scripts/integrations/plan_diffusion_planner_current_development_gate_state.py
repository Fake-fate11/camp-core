#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SOURCE_CLOSURE_STATUS = "targeted_source_discovery_route_closed"
PROOF_PROTOCOL_STATUS = "proof_protocol_v2_predeclared"
SCENARIO_MATRIX_STATUS = "scenario_evidence_matrix_predeclared"
FAILURE_ATTRIBUTION_STATUS = "targeted_failure_attribution_no_current_route"
SUPPORT_REJECT_STATUS = "new_no_leak_targeted_support_source_not_available"

READY_STATUS = "current_development_gate_state_no_deployable_route_yet"
BLOCKED_STATUS = "current_development_gate_state_source_blocked"
AUTHORIZED_NEXT_WORK = "scenario_objective_redesign_or_external_source_discovery_only"

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
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only current development gate state for CAMP-on-fixed-DP. "
            "It summarizes passed proof/scenario/oracle gates and closed "
            "selector/source routes before the next self-iteration."
        )
    )
    parser.add_argument("--source_closure_json", type=Path, required=True)
    parser.add_argument("--proof_protocol_v2_json", type=Path, required=True)
    parser.add_argument("--scenario_evidence_matrix_json", type=Path, required=True)
    parser.add_argument("--targeted_oracle_json", type=Path, required=True)
    parser.add_argument("--targeted_failure_attribution_json", type=Path, required=True)
    parser.add_argument("--support_reject_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        source_closure=_load_json(args.source_closure_json),
        proof_protocol_v2=_load_json(args.proof_protocol_v2_json),
        scenario_evidence_matrix=_load_json(args.scenario_evidence_matrix_json),
        targeted_oracle=_load_json(args.targeted_oracle_json),
        targeted_failure_attribution=_load_json(args.targeted_failure_attribution_json),
        support_reject=_load_json(args.support_reject_json),
        label=args.label,
        paths={
            "source_closure_json": str(args.source_closure_json),
            "proof_protocol_v2_json": str(args.proof_protocol_v2_json),
            "scenario_evidence_matrix_json": str(args.scenario_evidence_matrix_json),
            "targeted_oracle_json": str(args.targeted_oracle_json),
            "targeted_failure_attribution_json": str(
                args.targeted_failure_attribution_json
            ),
            "support_reject_json": str(args.support_reject_json),
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
    source_closure: dict[str, Any],
    proof_protocol_v2: dict[str, Any],
    scenario_evidence_matrix: dict[str, Any],
    targeted_oracle: dict[str, Any],
    targeted_failure_attribution: dict[str, Any],
    support_reject: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    checks = _source_checks(
        source_closure=source_closure,
        proof_protocol_v2=proof_protocol_v2,
        scenario_evidence_matrix=scenario_evidence_matrix,
        targeted_oracle=targeted_oracle,
        targeted_failure_attribution=targeted_failure_attribution,
        support_reject=support_reject,
    )
    state = _development_state(
        source_closure=source_closure,
        proof_protocol_v2=proof_protocol_v2,
        scenario_evidence_matrix=scenario_evidence_matrix,
        targeted_oracle=targeted_oracle,
        targeted_failure_attribution=targeted_failure_attribution,
        support_reject=support_reject,
    )
    final = _final_decision(checks)
    return {
        "analysis": {
            "name": "dp_camp_current_development_gate_state_v1",
            "label": label,
            "role": (
                "read-only self-iteration ledger after source discovery closed "
                "and before any scenario/objective redesign"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "paths": paths or {},
            "math_boundary": (
                "This ledger reads existing JSON artifacts only. It does not "
                "run DP, collect labels, create atoms, train weights, or "
                "promote a selector. Runtime CAMP features must remain fixed "
                "current-tick finite-candidate coefficients and scores must "
                "stay affine score_k(w)=a_k^T w, preserving the convex "
                "simplex/CVaR/L2 master. Offline outcomes and SafetyCost labels "
                "remain evaluation labels only. No DP-side classical Benders "
                "master/subproblem, dual, or cut is constructed."
            ),
        },
        "source_checks": checks,
        "development_state": state,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": final,
    }


def _source_checks(
    *,
    source_closure: dict[str, Any],
    proof_protocol_v2: dict[str, Any],
    scenario_evidence_matrix: dict[str, Any],
    targeted_oracle: dict[str, Any],
    targeted_failure_attribution: dict[str, Any],
    support_reject: dict[str, Any],
) -> list[dict[str, Any]]:
    source_decision = source_closure.get("final_decision") or {}
    proof_decision = proof_protocol_v2.get("final_decision") or {}
    scenario_decision = scenario_evidence_matrix.get("final_decision") or {}
    scenario_matrix = scenario_evidence_matrix.get("matrix_source") or {}
    proof_protocol = proof_protocol_v2.get("protocol") or {}
    oracle_gate = targeted_oracle.get("opportunity_gate") or {}
    coverage_gaps = targeted_oracle.get("coverage_gaps") or {}
    oracle_logs = targeted_oracle.get("logs") or {}
    failure_decision = targeted_failure_attribution.get("final_decision") or {}
    failure_summary = targeted_failure_attribution.get("failure_summary") or {}
    support_decision = support_reject.get("final_decision") or {}
    return [
        _check_equal(
            "source_closure_status",
            source_decision.get("status"),
            SOURCE_CLOSURE_STATUS,
        ),
        _check_equal("source_closure_passed", source_decision.get("passed"), True),
        _check_equal(
            "source_discovery_closed",
            source_decision.get("source_discovery_closed"),
            True,
        ),
        _check_equal(
            "proof_protocol_status",
            proof_decision.get("status"),
            PROOF_PROTOCOL_STATUS,
        ),
        _check_equal("proof_protocol_passed", proof_decision.get("passed"), True),
        _check_required_buckets(
            "proof_protocol_required_buckets",
            proof_protocol.get("required_scenario_buckets") or [],
        ),
        _check_equal(
            "scenario_matrix_status",
            scenario_decision.get("status"),
            SCENARIO_MATRIX_STATUS,
        ),
        _check_equal("scenario_matrix_passed", scenario_decision.get("passed"), True),
        _check_empty(
            "scenario_matrix_missing_required_buckets",
            scenario_matrix.get("missing_required_buckets") or [],
        ),
        _check_empty(
            "scenario_matrix_formal_seeds",
            scenario_matrix.get("formal_seeds") or [],
        ),
        _check_equal("oracle_opportunity_passed", oracle_gate.get("passed"), True),
        _check_equal(
            "oracle_no_formal_seed_logs",
            oracle_logs.get("formal_seed_logs"),
            0,
        ),
        _check_empty(
            "oracle_missing_required_buckets",
            coverage_gaps.get("missing_required_buckets") or [],
        ),
        _check_equal(
            "failure_attribution_status",
            failure_decision.get("status"),
            FAILURE_ATTRIBUTION_STATUS,
        ),
        _check_equal(
            "failure_attribution_current_route_rejected",
            failure_decision.get("current_camp_dp_selector_route_rejected"),
            True,
        ),
        _check_equal(
            "failure_attribution_current_camp_failed",
            failure_summary.get("current_camp_targeted_failure_confirmed"),
            True,
        ),
        _check_equal(
            "support_reject_status",
            support_decision.get("status"),
            SUPPORT_REJECT_STATUS,
        ),
        _check_equal(
            "support_source_ready_false",
            support_decision.get("support_source_ready"),
            False,
        ),
        *_blocked_action_checks(source_decision, "source_closure"),
        *_blocked_action_checks(proof_decision, "proof_protocol"),
        *_blocked_action_checks(scenario_decision, "scenario_matrix"),
        *_blocked_action_checks(failure_decision, "failure_attribution"),
        *_blocked_action_checks(support_decision, "support_reject"),
    ]


def _development_state(
    *,
    source_closure: dict[str, Any],
    proof_protocol_v2: dict[str, Any],
    scenario_evidence_matrix: dict[str, Any],
    targeted_oracle: dict[str, Any],
    targeted_failure_attribution: dict[str, Any],
    support_reject: dict[str, Any],
) -> dict[str, Any]:
    source_decision = source_closure.get("final_decision") or {}
    proof_protocol = proof_protocol_v2.get("protocol") or {}
    scenario_matrix = scenario_evidence_matrix.get("matrix_source") or {}
    oracle_gate = targeted_oracle.get("opportunity_gate") or {}
    failure_summary = targeted_failure_attribution.get("failure_summary") or {}
    support_decision = support_reject.get("final_decision") or {}
    return {
        "passed_or_available_evidence": {
            "proof_protocol_v2_predeclared": True,
            "scenario_evidence_matrix_predeclared": True,
            "candidate_branch_oracle_opportunity_passed": bool(
                oracle_gate.get("passed")
            ),
        },
        "closed_or_rejected_routes": {
            "current_logged_camp_selector": bool(
                failure_summary.get("current_camp_targeted_failure_confirmed")
            ),
            "old_training_and_sensitivity_routes": bool(
                failure_summary.get("old_training_and_sensitivity_routes_closed")
            ),
            "no_leak_source_discovery": bool(
                source_decision.get("source_discovery_closed")
            ),
            "new_support_source_available": bool(
                support_decision.get("support_source_ready")
            ),
        },
        "proof_contract": {
            "primary_score": (proof_protocol.get("primary_score") or {}).get("name"),
            "claim_rule": (proof_protocol.get("primary_score") or {}).get(
                "claim_rule"
            ),
            "required_buckets": proof_protocol.get("required_scenario_buckets") or [],
            "scenario_planned_run_count": scenario_matrix.get("planned_run_count"),
            "scenario_bucket_counts": scenario_matrix.get("bucket_counts") or {},
        },
        "blocking_gap": (
            "candidate_pool_opportunity_exists_but_no_current_no_leak_deployable_selector_route"
        ),
        "development_gates_complete": False,
        "formal_seed_ready": False,
    }


def _final_decision(checks: list[dict[str, Any]]) -> dict[str, Any]:
    source_ready = all(check["passed"] for check in checks)
    status = READY_STATUS if source_ready else BLOCKED_STATUS
    return {
        "status": status,
        "passed": source_ready,
        "development_gates_complete": False,
        "formal_seeds_ready": False,
        "current_camp_dp_selector_route_rejected": source_ready,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if source_ready else None,
        "next_step": (
            "Do not rerun closed atom/source/training routes. Predeclare a "
            "scenario/objective redesign or external source-discovery contract, "
            "or keep the current route paused."
            if source_ready
            else "Repair failed source artifacts before continuing development-state planning."
        ),
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        **{key: False for key in BLOCKED_ACTIONS},
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    state = report["development_state"]
    contract = state["proof_contract"]
    lines = [
        "# Current DP-CAMP Development Gate State",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Development gates complete: `{decision['development_gates_complete']}`",
        f"- Formal seeds ready: `{decision['formal_seeds_ready']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Proof Contract",
        "",
        f"- Primary score: `{contract['primary_score']}`",
        f"- Claim rule: `{contract['claim_rule']}`",
        f"- Required buckets: `{', '.join(contract['required_buckets'])}`",
        f"- Planned runs: `{contract['scenario_planned_run_count']}`",
        "",
        "## Evidence State",
        "",
    ]
    for key, value in state["passed_or_available_evidence"].items():
        lines.append(f"- `{key}` = `{value}`")
    lines.extend(["", "## Closed Or Rejected Routes", ""])
    for key, value in state["closed_or_rejected_routes"].items():
        lines.append(f"- `{key}` = `{value}`")
    lines.extend(
        [
            "",
            f"Blocking gap: `{state['blocking_gap']}`",
            "",
            "## Source Checks",
            "",
            "| Check | Passed | Detail |",
            "| --- | --- | --- |",
        ]
    )
    for check in report["source_checks"]:
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


def _blocked_action_checks(decision: dict[str, Any], prefix: str) -> list[dict[str, Any]]:
    return [
        _check_equal(f"{prefix}_{name}_false", decision.get(name, False), False)
        for name in BLOCKED_ACTIONS
    ]


def _check_required_buckets(name: str, observed: list[Any]) -> dict[str, Any]:
    observed_set = {str(item) for item in observed}
    missing = [bucket for bucket in REQUIRED_BUCKETS if bucket not in observed_set]
    return {
        "name": name,
        "passed": not missing,
        "observed": list(observed),
        "expected": list(REQUIRED_BUCKETS),
        "missing": missing,
    }


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
