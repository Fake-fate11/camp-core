#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PAUSE_STATUS = "post_external_context_selector_route_paused"
PAUSE_NEXT_WORK = "new_proof_objective_or_new_current_tick_source_predeclaration_only"
PROOF_GAP_STATUS = "deployable_gap_diagnosed"
TARGETED_FAILURE_STATUS = "targeted_failure_attribution_no_current_route"
SOURCE_CLOSURE_STATUS = "post_external_context_source_route_closed"

READY_STATUS = "post_pause_deployability_proof_objective_predeclared"
BLOCKED_STATUS = "post_pause_deployability_proof_objective_blocked"
AUTHORIZED_NEXT_WORK = "new_current_tick_source_family_proposal_only"

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
            "Design-only deployability-first proof objective after the current "
            "fixed-DP CAMP selector route is paused. It reads existing artifacts "
            "and does not run DP, train CAMP, or change selection."
        )
    )
    parser.add_argument("--pause_gate_json", type=Path, required=True)
    parser.add_argument("--proof_to_deployable_gap_json", type=Path, required=True)
    parser.add_argument("--targeted_failure_attribution_json", type=Path, required=True)
    parser.add_argument("--post_external_context_closure_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        pause_gate=_load_json(args.pause_gate_json),
        proof_to_deployable_gap=_load_json(args.proof_to_deployable_gap_json),
        targeted_failure_attribution=_load_json(args.targeted_failure_attribution_json),
        post_external_context_closure=_load_json(args.post_external_context_closure_json),
        label=args.label,
        paths={
            "pause_gate_json": str(args.pause_gate_json),
            "proof_to_deployable_gap_json": str(args.proof_to_deployable_gap_json),
            "targeted_failure_attribution_json": str(
                args.targeted_failure_attribution_json
            ),
            "post_external_context_closure_json": str(
                args.post_external_context_closure_json
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
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def build_report(
    *,
    pause_gate: dict[str, Any],
    proof_to_deployable_gap: dict[str, Any],
    targeted_failure_attribution: dict[str, Any],
    post_external_context_closure: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    pause = _pause_summary(pause_gate)
    proof_gap = _proof_gap_summary(proof_to_deployable_gap)
    targeted = _targeted_failure_summary(targeted_failure_attribution)
    source_closure = _source_closure_summary(post_external_context_closure)
    objective = _objective_contract(proof_gap=proof_gap, targeted=targeted)
    checks = [
        *_pause_checks(pause),
        *_proof_gap_checks(proof_gap),
        *_targeted_checks(targeted),
        *_source_closure_checks(source_closure),
        *_objective_checks(objective),
    ]
    decision = _final_decision(checks)
    return {
        "analysis": {
            "name": "dp_camp_post_pause_deployability_proof_objective_v1",
            "label": label,
            "role": (
                "design-only proof objective that moves the post-pause route "
                "from outcome-only claims to a deployability-first safety case"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used_for_runtime_features": False,
            "paths": paths or {},
            "math_boundary": (
                "This gate defines proof obligations only. It creates no atom, "
                "does not run a selector, and does not train CAMP. Runtime CAMP "
                "inputs, if later authorized, must be current-tick fixed "
                "finite-candidate coefficients a_k, nonnegative, hinged, or "
                "signed-split, preserving score_k(w)=a_k^T w and the convex "
                "simplex/CVaR/L2 master. Offline outcomes and SafetyCost are "
                "labels for proof gates only. No DP-side classical Benders "
                "master/subproblem, dual, or valid cut is constructed."
            ),
        },
        "pause_summary": pause,
        "proof_to_deployable_gap_summary": proof_gap,
        "targeted_failure_summary": targeted,
        "post_external_context_closure_summary": source_closure,
        "deployability_first_objective": objective,
        "plan_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _pause_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "selector_route_paused": bool(decision.get("selector_route_paused")),
        "deployable_route_exists": bool(
            decision.get("deployable_camp_dp_selector_route_exists")
        ),
        "authorized_next_work": decision.get("authorized_next_work"),
        "blocked_action_conflicts": _blocked_conflicts(decision),
    }


def _proof_gap_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    mechanism = report.get("mechanism") or {}
    return {
        "status": decision.get("status"),
        "candidate_support_exists": bool(mechanism.get("candidate_support_exists")),
        "candidate_branch_selector_passes": bool(
            mechanism.get("candidate_branch_selector_passes")
        ),
        "deployable_gate_passes": bool(mechanism.get("deployable_gate_passes")),
        "root_cause_class": mechanism.get("root_cause_class"),
        "primary_blockers": list(mechanism.get("primary_blockers") or []),
        "camp_retraining_authorized": bool(decision.get("camp_retraining_authorized")),
        "online_selector_promotion_authorized": bool(
            decision.get("online_selector_promotion_authorized")
        ),
        "full36_authorized": bool(decision.get("full36_authorized")),
        "formal_seeds_authorized": bool(decision.get("formal_seeds_authorized")),
    }


def _targeted_failure_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    summary = report.get("failure_summary") or {}
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "current_route_rejected": bool(
            decision.get("current_camp_dp_selector_route_rejected")
        ),
        "candidate_pool_opportunity_confirmed": bool(
            summary.get("candidate_pool_opportunity_confirmed")
        ),
        "new_no_leak_support_missing": bool(
            summary.get("new_no_leak_support_missing_in_current_artifacts")
        ),
        "old_training_and_sensitivity_routes_closed": bool(
            summary.get("old_training_and_sensitivity_routes_closed")
        ),
        "blocked_action_conflicts": _blocked_conflicts(decision),
    }


def _source_closure_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "external_context_source_route_closed": bool(
            decision.get("external_context_source_route_closed")
        ),
        "current_route_rejected": bool(
            decision.get("current_camp_dp_selector_route_rejected")
        ),
        "blocked_action_conflicts": _blocked_conflicts(decision),
    }


def _objective_contract(
    *,
    proof_gap: dict[str, Any],
    targeted: dict[str, Any],
) -> dict[str, Any]:
    return {
        "name": "DeployabilityFirstCampDpProofObjective_v1",
        "claim_scope": (
            "CAMP is useful for fixed-DP candidate selection only if a legal "
            "no-leak runtime source exists before selection and the paired "
            "nonformal evidence improves or preserves SafetyCost versus DP Top-1."
        ),
        "source_first": True,
        "objective_only_sufficient": False,
        "observed_gap": {
            "candidate_pool_opportunity_confirmed": (
                proof_gap["candidate_support_exists"]
                or targeted["candidate_pool_opportunity_confirmed"]
            ),
            "candidate_branch_selector_passes": proof_gap[
                "candidate_branch_selector_passes"
            ],
            "deployable_gate_passes": proof_gap["deployable_gate_passes"],
            "new_no_leak_support_missing": targeted["new_no_leak_support_missing"],
            "primary_blockers": proof_gap["primary_blockers"],
        },
        "required_preconditions_before_replay": [
            "new_source_family_predeclared",
            "current_tick_visibility_proven_before_selection",
            "candidate_level_or_deterministically_joinable_shape_proven",
            "non_equivalence_to_closed_families_proven",
            "not_future_outcome_or_safetycost_proxy",
            "atomization_as_nonnegative_hinge_or_signed_split_coefficient",
            "existing_log_materiality_noninferiority_screen_passed",
            "default_off_latency_budget_predeclared",
        ],
        "paired_nonformal_claim": {
            "score": "SafetyCost_v1",
            "comparison": "CAMP_minus_DP_Top1",
            "primary_rule": (
                "all hard gates pass and ci95_high(SafetyCost_CAMP_minus_DP_Top1) < 0"
            ),
            "guard_rule": (
                "normal, overall, fallback, completion, comfort, and latency "
                "guards must be nondegrading before expansion"
            ),
            "tail_rule": "ci95_high(CVaR90_SafetyCost_CAMP_minus_DP_Top1) <= 0",
        },
        "forbidden_shortcuts": [
            "using SafetyCost or closed-loop outcomes as runtime features",
            "claiming objective redesign alone creates a deployable selector",
            "rerunning closed source families as new evidence",
            "training CAMP before a legal source certificate exists",
            "running Full36 or formal seeds before tiny paired gates pass",
            "calling finite-candidate DP selection classical Benders",
        ],
        "next_source_family_requirements": [
            "must not be route-speed, signal/right-of-way, turn-logit, DP-prior deviation, Top-1 retention, progress/lane-hard, observable interaction, route topology, mode-seeking, or any other closed family unless new non-equivalence evidence is supplied",
            "must provide candidate coefficients a_k that are finite for every candidate or fail closed",
            "must preserve affine scoring and convex CAMP master if atomized",
        ],
    }


def _pause_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("pause_status", summary["status"], PAUSE_STATUS),
        _check_equal("pause_passed", summary["passed"], True),
        _check_equal("selector_route_paused", summary["selector_route_paused"], True),
        _check_equal("deployable_route_absent", summary["deployable_route_exists"], False),
        _check_equal(
            "pause_authorizes_this_gate",
            summary["authorized_next_work"],
            PAUSE_NEXT_WORK,
        ),
        _check_empty("pause_no_blocked_actions", summary["blocked_action_conflicts"]),
    ]


def _proof_gap_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("proof_gap_status", summary["status"], PROOF_GAP_STATUS),
        _check_equal("candidate_support_exists", summary["candidate_support_exists"], True),
        _check_equal("deployable_gate_not_passing", summary["deployable_gate_passes"], False),
        _check_equal("camp_retraining_not_authorized", summary["camp_retraining_authorized"], False),
        _check_equal(
            "online_promotion_not_authorized",
            summary["online_selector_promotion_authorized"],
            False,
        ),
        _check_equal("full36_not_authorized", summary["full36_authorized"], False),
        _check_equal("formal_seeds_not_authorized", summary["formal_seeds_authorized"], False),
    ]


def _targeted_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("targeted_failure_status", summary["status"], TARGETED_FAILURE_STATUS),
        _check_equal("targeted_failure_passed", summary["passed"], True),
        _check_equal("targeted_current_route_rejected", summary["current_route_rejected"], True),
        _check_equal(
            "targeted_candidate_pool_opportunity",
            summary["candidate_pool_opportunity_confirmed"],
            True,
        ),
        _check_equal("targeted_no_new_support", summary["new_no_leak_support_missing"], True),
        _check_equal(
            "targeted_old_routes_closed",
            summary["old_training_and_sensitivity_routes_closed"],
            True,
        ),
        _check_empty("targeted_no_blocked_actions", summary["blocked_action_conflicts"]),
    ]


def _source_closure_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_closure_status", summary["status"], SOURCE_CLOSURE_STATUS),
        _check_equal("source_closure_passed", summary["passed"], True),
        _check_equal(
            "external_context_source_closed",
            summary["external_context_source_route_closed"],
            True,
        ),
        _check_equal("source_closure_route_rejected", summary["current_route_rejected"], True),
        _check_empty("source_closure_no_blocked_actions", summary["blocked_action_conflicts"]),
    ]


def _objective_checks(objective: dict[str, Any]) -> list[dict[str, Any]]:
    observed = objective["observed_gap"]
    return [
        _check_equal("objective_is_source_first", objective["source_first"], True),
        _check_equal(
            "objective_only_not_sufficient",
            objective["objective_only_sufficient"],
            False,
        ),
        _check_equal(
            "objective_records_candidate_pool_opportunity",
            observed["candidate_pool_opportunity_confirmed"],
            True,
        ),
        _check_equal(
            "objective_records_deployable_gap",
            observed["deployable_gate_passes"],
            False,
        ),
        _check_equal(
            "objective_records_missing_support",
            observed["new_no_leak_support_missing"],
            True,
        ),
    ]


def _final_decision(checks: list[dict[str, Any]]) -> dict[str, Any]:
    passed = all(check["passed"] for check in checks)
    return {
        "status": READY_STATUS if passed else BLOCKED_STATUS,
        "passed": passed,
        "deployability_first_objective_ready": passed,
        "objective_only_reopening_allowed": False,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "next_step": (
            "Predeclare a genuinely new current-tick source family, then prove "
            "visibility, non-equivalence, atomization, existing-log materiality, "
            "and fail-closed latency before any replay or training."
            if passed
            else "Repair the failed upstream evidence before predeclaring this objective."
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    objective = report["deployability_first_objective"]
    observed = objective["observed_gap"]
    lines = [
        "# Post-Pause Deployability-First Proof Objective",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Objective ready: `{decision['deployability_first_objective_ready']}`",
        f"- Objective-only reopening allowed: `{decision['objective_only_reopening_allowed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Objective Contract",
        "",
        f"- Name: `{objective['name']}`",
        f"- Claim scope: {objective['claim_scope']}",
        f"- Source first: `{objective['source_first']}`",
        f"- Objective-only sufficient: `{objective['objective_only_sufficient']}`",
        "",
        "## Observed Gap",
        "",
    ]
    for key, value in observed.items():
        lines.append(f"- `{key}` = `{value}`")
    lines.extend(["", "Preconditions before replay:", ""])
    for item in objective["required_preconditions_before_replay"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "Forbidden shortcuts:", ""])
    for item in objective["forbidden_shortcuts"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "Next source-family requirements:", ""])
    for item in objective["next_source_family_requirements"]:
        lines.append(f"- {item}")
    claim = objective["paired_nonformal_claim"]
    lines.extend(
        [
            "",
            "## Paired Nonformal Claim",
            "",
            f"- Score: `{claim['score']}`",
            f"- Comparison: `{claim['comparison']}`",
            f"- Primary rule: {claim['primary_rule']}",
            f"- Guard rule: {claim['guard_rule']}",
            f"- Tail rule: {claim['tail_rule']}",
            "",
            "## Plan Checks",
            "",
            "| Check | Passed | Detail |",
            "| --- | --- | --- |",
        ]
    )
    for check in report["plan_checks"]:
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
