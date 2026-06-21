#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SOURCE_STATUS = "current_tick_no_leak_atom_support_inventory_no_unclosed_fields"
SOURCE_NEXT_WORK = "proof_objective_v2_or_default_off_logging_preflight_design_only"

READY_STATUS = "post_inventory_next_design_plan_ready"
BLOCKED_STATUS = "post_inventory_next_design_plan_blocked"
AUTHORIZED_NEXT_WORK = "predeclare_default_off_missing_candidate_state_logging_preflight_only"

MISSING_STATE_FAMILIES = (
    "candidate_lane_topology",
    "candidate_traffic_light_path_relation",
    "route_curvature_turn_context",
    "neighbor_interaction_clearance",
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
            "Plan-only next-design gate after the current-tick no-leak atom "
            "support inventory finds no unclosed candidate fields."
        )
    )
    parser.add_argument("--support_inventory_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        support_inventory=_load_json(args.support_inventory_json),
        label=args.label,
        paths={"support_inventory_json": str(args.support_inventory_json)},
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
    support_inventory: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source = _source_gate(support_inventory)
    checks = _plan_checks(source)
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_post_inventory_next_design_plan_v1",
            "label": label,
            "role": (
                "design-only gate after existing logs expose no unclosed "
                "candidate-level current-tick atom support"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_leakage": False,
            "paths": paths or {},
            "math_boundary": (
                "DP remains a frozen black-box candidate generator. This plan "
                "does not add atoms, run replay, train CAMP, modify DP, or "
                "claim proof. It only authorizes a design preflight for "
                "default-off current-tick candidate-state logging. Any later "
                "atom must be a fixed finite-candidate coefficient a_k, "
                "nonnegative or represented by nonnegative signed parts, so "
                "score_k(w)=a_k^T w remains affine and the simplex/CVaR/L2 "
                "master remains convex. This is not classical Benders."
            ),
        },
        "source_inventory_gate": source,
        "plan_checks": checks,
        "rejected_routes": _rejected_routes(),
        "design_options": _design_options(),
        "default_off_logging_contract": _default_off_logging_contract(),
        "proof_objective_contract": _proof_objective_contract(),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed),
    }


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    final = report.get("final_decision") or {}
    admissible = list(final.get("admissible_unclosed_candidate_families") or [])
    partial = list(final.get("partial_candidate_families") or [])
    existing = list(final.get("available_existing_or_closed_proxy_families") or [])
    conflicts = [key for key in BLOCKED_ACTIONS if bool(final.get(key))]
    return {
        "status": final.get("status"),
        "passed": (
            final.get("status") == SOURCE_STATUS
            and final.get("authorized_next_work") == SOURCE_NEXT_WORK
            and not admissible
            and not conflicts
        ),
        "authorized_next_work": final.get("authorized_next_work"),
        "primary_gap": final.get("primary_gap"),
        "admissible_unclosed_candidate_families": admissible,
        "partial_candidate_families": partial,
        "available_existing_or_closed_proxy_families": existing,
        "blocked_action_conflicts": conflicts,
    }


def _plan_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "name": "source_inventory_rejects_existing_logs",
            "passed": source["status"] == SOURCE_STATUS,
            "actual": source["status"],
            "expected": SOURCE_STATUS,
        },
        {
            "name": "source_inventory_authorizes_design_only",
            "passed": source["authorized_next_work"] == SOURCE_NEXT_WORK,
            "actual": source["authorized_next_work"],
            "expected": SOURCE_NEXT_WORK,
        },
        {
            "name": "no_admissible_current_log_fields",
            "passed": not source["admissible_unclosed_candidate_families"],
            "admissible": source["admissible_unclosed_candidate_families"],
        },
        {
            "name": "no_blocked_action_conflicts",
            "passed": not source["blocked_action_conflicts"],
            "conflicts": source["blocked_action_conflicts"],
        },
    ]


def _rejected_routes() -> list[dict[str, str]]:
    return [
        {
            "name": "train_new_camp_weights_from_current_logs",
            "reason": (
                "The current logs expose no unclosed candidate-level atom "
                "support; training would reuse exhausted proxy families."
            ),
        },
        {
            "name": "new_atom_schema_from_existing_log_fields",
            "reason": (
                "The support inventory found no admissible unclosed current-tick "
                "candidate state family."
            ),
        },
        {
            "name": "proof_objective_only_as_performance_claim",
            "reason": (
                "A proof-objective redesign can clarify gates, but cannot by "
                "itself create runtime selector information or prove CAMP "
                "beats DP Top-1."
            ),
        },
        {
            "name": "direct_replay_or_full36",
            "reason": "No deployable no-leak selector hypothesis exists yet.",
        },
    ]


def _design_options() -> list[dict[str, Any]]:
    return [
        {
            "name": "default_off_missing_candidate_state_logging_preflight",
            "priority": 1,
            "recommended_first": True,
            "status": "authorized_design_only",
            "purpose": (
                "Predeclare logging for missing candidate-level runtime state "
                "families before proposing a new atom schema."
            ),
            "families": list(MISSING_STATE_FAMILIES),
        },
        {
            "name": "proof_objective_v2_refinement",
            "priority": 2,
            "recommended_first": False,
            "status": "allowed_design_only_not_performance_evidence",
            "purpose": (
                "Clarify score, buckets, comparators, and nondegradation gates "
                "without claiming selector improvement."
            ),
        },
    ]


def _default_off_logging_contract() -> dict[str, Any]:
    return {
        "must_be": [
            "default-off",
            "selection-effect-free",
            "current-tick only",
            "candidate-level where used for atoms",
            "deterministic for fixed DP candidates and map/context",
            "validated for finite values and exact baseline equivalence",
        ],
        "candidate_state_families": list(MISSING_STATE_FAMILIES),
        "required_payload_metadata": [
            "schema_version",
            "enabled",
            "default_off",
            "selection_effect",
            "future_outcome_leakage",
            "candidate_count",
            "field_shapes",
            "finite_checks",
            "latency_ms",
        ],
        "must_not_include": [
            "candidate_closed_loop_outcomes",
            "future collision/red/near-miss/completion labels",
            "DP weight or source changes",
            "online selector behavior changes",
        ],
    }


def _proof_objective_contract() -> dict[str, Any]:
    return {
        "allowed": [
            "predeclare SafetyCost or successor claim rule",
            "predeclare scenario buckets and comparators",
            "predeclare nondegradation gates",
            "record why proof-only work cannot substitute for runtime support",
        ],
        "not_allowed": [
            "claiming CAMP improvement without selector evidence",
            "using future outcomes as runtime features",
            "reopening rejected atom/proxy families without new source evidence",
        ],
    }


def _final_decision(passed: bool) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else BLOCKED_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "recommended_first_action": (
            "default_off_missing_candidate_state_logging_preflight"
            if passed
            else "repair_support_inventory_source"
        ),
        **{key: False for key in BLOCKED_ACTIONS},
        "next_step": (
            "Write a design-only default-off logging preflight for missing "
            "candidate-state families."
            if passed
            else "Repair or rerun the support inventory source gate."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    source = report["source_inventory_gate"]
    lines = [
        "# Post-Inventory Next Design Plan",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Recommended first action: `{decision['recommended_first_action']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Source Inventory",
        "",
        f"- Status: `{source['status']}`",
        f"- Primary gap: `{source['primary_gap']}`",
        f"- Admissible unclosed families: `{', '.join(source['admissible_unclosed_candidate_families']) or 'none'}`",
        f"- Existing/closed proxies: `{', '.join(source['available_existing_or_closed_proxy_families']) or 'none'}`",
        "",
        "## Rejected Routes",
        "",
    ]
    for route in report["rejected_routes"]:
        lines.append(f"- `{route['name']}`: {route['reason']}")
    lines.extend(["", "## Design Options", ""])
    for option in report["design_options"]:
        lines.append(
            f"- `{option['name']}`: priority `{option['priority']}`, "
            f"recommended_first=`{option['recommended_first']}`, "
            f"status=`{option['status']}`. {option['purpose']}"
        )
    lines.extend(["", "## Default-Off Logging Contract", ""])
    for item in report["default_off_logging_contract"]["must_be"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This is not training, not replay, not selector promotion, and not "
            "a classical Benders decomposition.",
            "",
        ]
    )
    return "\n".join(lines)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
