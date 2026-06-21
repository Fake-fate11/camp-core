#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SOURCE_STATUS = "current_development_gate_state_no_deployable_route_yet"
SOURCE_NEXT_WORK = "scenario_objective_redesign_or_external_source_discovery_only"

READY_STATUS = "scenario_objective_redesign_boundary_and_external_source_contract_ready"
BLOCKED_STATUS = "scenario_objective_redesign_or_external_source_contract_blocked"
AUTHORIZED_NEXT_WORK = "external_source_visibility_inventory_or_pause_only"

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
            "Design-only boundary after the current development ledger. It "
            "separates objective/scenario proof redesign from the external "
            "source visibility contract needed for a deployable CAMP route."
        )
    )
    parser.add_argument("--development_gate_state_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        development_gate_state=_load_json(args.development_gate_state_json),
        label=args.label,
        paths={"development_gate_state_json": str(args.development_gate_state_json)},
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
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source = _source_gate(development_gate_state)
    objective_boundary = _objective_boundary(development_gate_state)
    external_contract = _external_source_contract()
    checks = _plan_checks(source, objective_boundary, external_contract)
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_scenario_objective_redesign_or_external_source_contract_v1",
            "label": label,
            "role": (
                "design-only gate that prevents objective-only redesign from "
                "being mistaken for deployable selector evidence, and "
                "predeclares the external source visibility contract"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "paths": paths or {},
            "math_boundary": (
                "This gate reads only the current development ledger. It does "
                "not run DP, collect labels, create atoms, train weights, or "
                "promote a selector. Objective/scenario redesign is proof "
                "metadata only. Any future runtime feature must be a fixed "
                "current-tick finite-candidate coefficient a_k, nonnegative or "
                "signed-split, preserving affine score_k(w)=a_k^T w and the "
                "convex simplex/CVaR/L2 master. No DP-side classical Benders "
                "master/subproblem, dual, or cut is constructed."
            ),
        },
        "source_gate": source,
        "objective_redesign_boundary": objective_boundary,
        "external_source_visibility_contract": external_contract,
        "plan_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed),
    }


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    final = report.get("final_decision") or {}
    state = report.get("development_state") or {}
    proof = state.get("proof_contract") or {}
    conflicts = [key for key in BLOCKED_ACTIONS if bool(final.get(key))]
    required_buckets = list(proof.get("required_buckets") or [])
    missing_buckets = [bucket for bucket in REQUIRED_BUCKETS if bucket not in required_buckets]
    return {
        "status": final.get("status"),
        "passed": (
            final.get("status") == SOURCE_STATUS
            and bool(final.get("passed"))
            and final.get("authorized_next_work") == SOURCE_NEXT_WORK
            and final.get("development_gates_complete") is False
            and final.get("formal_seeds_ready") is False
            and final.get("current_camp_dp_selector_route_rejected") is True
            and not conflicts
            and not missing_buckets
        ),
        "authorized_next_work": final.get("authorized_next_work"),
        "development_gates_complete": final.get("development_gates_complete"),
        "formal_seeds_ready": final.get("formal_seeds_ready"),
        "blocking_gap": state.get("blocking_gap"),
        "primary_score": proof.get("primary_score"),
        "claim_rule": proof.get("claim_rule"),
        "required_buckets": required_buckets,
        "missing_required_buckets": missing_buckets,
        "blocked_action_conflicts": conflicts,
    }


def _objective_boundary(report: dict[str, Any]) -> dict[str, Any]:
    state = report.get("development_state") or {}
    proof = state.get("proof_contract") or {}
    return {
        "objective_only_redesign_sufficient_for_deployable_route": False,
        "reason": (
            "Scenario/objective definitions can make the proof stricter and "
            "more interpretable, but they do not create a no-leak runtime "
            "candidate feature or a deployable selector."
        ),
        "current_primary_score": proof.get("primary_score"),
        "current_claim_rule": proof.get("claim_rule"),
        "required_buckets": proof.get("required_buckets") or [],
        "allowed_changes": [
            "stricter target-bucket and guard-bucket reporting",
            "stricter CVaR/tail-risk reporting",
            "predeclared scenario labels using route/config metadata only",
            "clearer latency/fallback/comfort promotion gates",
            "external source discovery criteria before any atom proposal",
        ],
        "forbidden_changes": [
            "dropping DP Top-1 or current CAMP comparators",
            "dropping normal or overall non-degradation guards",
            "weakening hard safety components to pass existing results",
            "using closed-loop outcomes or SafetyCost as runtime selector inputs",
            "changing DP weights, DP source, or formal seeds",
            "renaming finite-candidate ranking as classical Benders",
        ],
        "next_objective_work_allowed": "documentation_or_contract_only",
    }


def _external_source_contract() -> dict[str, Any]:
    return {
        "status": "external_source_visibility_contract_predeclared",
        "ready_for_visibility_inventory": True,
        "required_properties": [
            "current_tick_available_before_selection",
            "candidate_level_or_candidate_context_joinable",
            "finite_and_deterministic_for_fixed_tick",
            "not_a_closed_score_family_or_proxy",
            "not_future_outcome_label",
            "does_not_require_dp_modification_or_retraining",
            "latency_measurable_default_off",
            "atomizable_as_nonnegative_or_signed_split_coefficient",
            "preserves_affine_score_and_convex_master",
        ],
        "hypothesis_families_to_audit_without_assuming_availability": [
            {
                "name": "traffic_signal_phase_timing_or_right_of_way",
                "examples": [
                    "time_to_phase_change_if_exposed",
                    "candidate_arrival_time_to_control_line",
                    "right_of_way_state_at_candidate_control_line",
                ],
                "caution": (
                    "only admissible if exposed at the current tick before "
                    "selection without using future simulator outcomes"
                ),
            },
            {
                "name": "dp_native_candidate_prior_or_uncertainty",
                "examples": [
                    "candidate_log_probability_if_visible",
                    "candidate_score_if_visible",
                    "denoising_residual_if_visible",
                ],
                "caution": (
                    "only admissible if visible at the wrapper boundary "
                    "without DP source modification and not already closed"
                ),
            },
            {
                "name": "map_or_route_control_context_not_already_closed",
                "examples": [
                    "control_line_relation_not_equivalent_to_red_stop_distance",
                    "speed_limit_or_regulatory_context_if_candidate_level",
                ],
                "caution": (
                    "must be proven not equivalent to closed traffic, route, "
                    "or observable interaction families"
                ),
            },
        ],
        "inventory_acceptance_checks": [
            "all inspected sources are listed with path, visibility, candidate shape, and latency plan",
            "closed or equivalent families are explicitly rejected",
            "any accepted source has a no-leak argument and atomization sketch",
            "no replay, training, online selector, Full36, or formal seed is authorized",
        ],
    }


def _plan_checks(
    source: dict[str, Any],
    objective_boundary: dict[str, Any],
    external_contract: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status_ready", source["status"], SOURCE_STATUS),
        _check_equal(
            "source_authorizes_this_gate",
            source["authorized_next_work"],
            SOURCE_NEXT_WORK,
        ),
        _check_equal(
            "source_development_gates_not_complete",
            source["development_gates_complete"],
            False,
        ),
        _check_equal("source_formal_seeds_not_ready", source["formal_seeds_ready"], False),
        _check_empty("source_no_blocked_action_conflicts", source["blocked_action_conflicts"]),
        _check_empty("source_no_missing_required_buckets", source["missing_required_buckets"]),
        _check_equal(
            "objective_only_not_sufficient",
            objective_boundary["objective_only_redesign_sufficient_for_deployable_route"],
            False,
        ),
        _check_equal(
            "external_contract_ready",
            external_contract["ready_for_visibility_inventory"],
            True,
        ),
        {
            "name": "next_step_is_source_inventory_or_pause_not_replay",
            "passed": True,
            "observed": AUTHORIZED_NEXT_WORK,
            "expected": AUTHORIZED_NEXT_WORK,
        },
    ]


def _final_decision(passed: bool) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else BLOCKED_STATUS,
        "passed": passed,
        "scenario_objective_redesign_only_sufficient": False,
        "external_source_contract_ready": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "next_step": (
            "Run a read-only external source visibility inventory, or keep the "
            "current CAMP-DP selector route paused. Do not train or replay."
            if passed
            else "Repair the current development gate state before contract design."
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    objective = report["objective_redesign_boundary"]
    contract = report["external_source_visibility_contract"]
    lines = [
        "# Scenario/Objective Redesign Or External Source Contract",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        "- Scenario/objective-only sufficient: "
        f"`{decision['scenario_objective_redesign_only_sufficient']}`",
        f"- External source contract ready: `{decision['external_source_contract_ready']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Source Gate",
        "",
        f"- Status: `{report['source_gate']['status']}`",
        f"- Passed: `{report['source_gate']['passed']}`",
        f"- Blocking gap: `{report['source_gate']['blocking_gap']}`",
        f"- Primary score: `{report['source_gate']['primary_score']}`",
        "",
        "## Objective Boundary",
        "",
        f"- Objective-only sufficient: `{objective['objective_only_redesign_sufficient_for_deployable_route']}`",
        f"- Reason: {objective['reason']}",
        "",
        "Allowed changes:",
        "",
    ]
    for item in objective["allowed_changes"]:
        lines.append(f"- {item}")
    lines.extend(["", "Forbidden changes:", ""])
    for item in objective["forbidden_changes"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## External Source Contract",
            "",
            f"- Status: `{contract['status']}`",
            "",
            "Required properties:",
            "",
        ]
    )
    for item in contract["required_properties"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "Hypothesis families to audit:", ""])
    for family in contract["hypothesis_families_to_audit_without_assuming_availability"]:
        lines.append(
            f"- `{family['name']}`: examples={family['examples']}; caution={family['caution']}"
        )
    lines.extend(["", "## Plan Checks", "", "| Check | Passed | Detail |", "| --- | --- | --- |"])
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
