#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SOURCE_STATUS = "offline_convex_objective_label_sensitivity_results_diagnosed"
SOURCE_NEXT_WORK = "predeclare_no_leak_atom_or_proof_objective_redesign_plan_only"

READY_STATUS = "no_leak_atom_or_proof_objective_redesign_plan_ready"
BLOCKED_STATUS = "no_leak_atom_or_proof_objective_redesign_plan_blocked"
AUTHORIZED_NEXT_WORK = "current_tick_no_leak_atom_support_inventory_preflight_only"

REQUIRED_PERSISTENT_FAILURES = frozenset(
    {
        "component_nonpositive_collision",
        "component_nonpositive_near_miss",
        "logged_selector_nonworse_ci_high",
        "oracle_gap_gate_passed",
        "top1_bucket_gate_passed",
    }
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
            "Plan-only no-leak atom/proof-objective redesign gate after the "
            "offline convex objective/label sensitivity route is rejected. It "
            "does not train CAMP, run Diffusion Planner, run replay, or change "
            "online selection."
        )
    )
    parser.add_argument("--diagnosis_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        diagnosis=_load_json(args.diagnosis_json),
        label=args.label,
        paths={"diagnosis_json": str(args.diagnosis_json)},
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
    diagnosis: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source_checks = _source_checks(diagnosis)
    sensitivity_summary = _sensitivity_summary(diagnosis)
    plan_checks = _plan_checks(sensitivity_summary)
    passed = all(check["passed"] for check in [*source_checks, *plan_checks])
    final = _final_decision(passed)
    return {
        "analysis": {
            "name": "dp_camp_no_leak_atom_or_proof_objective_redesign_plan_v1",
            "label": label,
            "role": (
                "plan-only redesign gate after objective/label sensitivity "
                "fails to provide a credible nonworse direction"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_leakage": False,
            "paths": paths or {},
            "math_boundary": (
                "DP remains a fixed black-box candidate generator. Runtime "
                "CAMP inputs must be finite current-tick candidate quantities. "
                "A new atom may enter CAMP only as a fixed coefficient a_k, "
                "preferably nonnegative or split into nonnegative signed parts, "
                "so score_k(w)=a_k^T w remains affine and the simplex/CVaR/L2 "
                "master remains convex. Offline closed-loop outcomes may be "
                "used only as labels or evaluation evidence. This gate does not "
                "construct a DP-side classical Benders master/subproblem, dual, "
                "or cut, and it makes no trajectory-coordinate convexity claim."
            ),
        },
        "source_checks": source_checks,
        "sensitivity_summary": sensitivity_summary,
        "rejected_routes": _rejected_routes(),
        "atom_admissibility_contract": _atom_admissibility_contract(),
        "proof_objective_contract": _proof_objective_contract(),
        "redesign_options": _redesign_options(),
        "plan_checks": plan_checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": final,
    }


def _source_checks(diagnosis: dict[str, Any]) -> list[dict[str, Any]]:
    decision = diagnosis.get("final_decision") or {}
    route = diagnosis.get("route_diagnosis") or {}
    comparison = diagnosis.get("comparison_summary") or {}
    checks = [
        _check_equal("diagnosis_status_ready", decision.get("status"), SOURCE_STATUS),
        _check_equal("diagnosis_passed", decision.get("passed"), True),
        _check_equal(
            "sensitivity_route_rejected",
            decision.get("sensitivity_route_rejected"),
            True,
        ),
        _check_equal(
            "no_credible_direction_candidates",
            decision.get("credible_direction_candidates") or [],
            [],
        ),
        _check_equal(
            "comparison_has_no_credible_direction_candidates",
            comparison.get("credible_direction_candidates") or [],
            [],
        ),
        _check_equal(
            "diagnosis_authorizes_redesign_plan_only",
            decision.get("authorized_next_work"),
            SOURCE_NEXT_WORK,
        ),
        _check_equal(
            "route_diagnosis_rejects_sensitivity",
            route.get("sensitivity_route_rejected"),
            True,
        ),
        *_blocked_action_checks(decision, "diagnosis"),
    ]
    return checks


def _sensitivity_summary(diagnosis: dict[str, Any]) -> dict[str, Any]:
    route = diagnosis.get("route_diagnosis") or {}
    comparison = diagnosis.get("comparison_summary") or {}
    return {
        "persistent_failed_checks": sorted(
            str(item) for item in route.get("persistent_failed_checks") or []
        ),
        "missing_required_persistent_failures": sorted(
            REQUIRED_PERSISTENT_FAILURES
            - set(str(item) for item in route.get("persistent_failed_checks") or [])
        ),
        "best_by_logged_nonworse_ci_high": comparison.get(
            "best_by_logged_nonworse_ci_high"
        ),
        "best_by_collision_delta": comparison.get("best_by_collision_delta"),
        "best_by_near_miss_delta": comparison.get("best_by_near_miss_delta"),
        "top1_failure_counts": comparison.get("top1_failure_counts") or {},
        "oracle_gap_failure_counts": comparison.get("oracle_gap_failure_counts") or {},
        "credible_direction_candidates": comparison.get(
            "credible_direction_candidates"
        )
        or [],
    }


def _plan_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "name": "required_persistent_failures_present",
            "passed": not summary["missing_required_persistent_failures"],
            "missing": summary["missing_required_persistent_failures"],
        },
        {
            "name": "top1_failures_remain_broad",
            "passed": bool(summary["top1_failure_counts"]),
            "top1_failure_counts": summary["top1_failure_counts"],
        },
        {
            "name": "oracle_gap_failures_remain_broad",
            "passed": bool(summary["oracle_gap_failure_counts"]),
            "oracle_gap_failure_counts": summary["oracle_gap_failure_counts"],
        },
        {
            "name": "no_weight_sensitivity_direction_to_extend",
            "passed": not summary["credible_direction_candidates"],
            "credible_direction_candidates": summary["credible_direction_candidates"],
        },
        {
            "name": "next_step_is_preflight_not_training_or_replay",
            "passed": True,
            "authorized_next_work": AUTHORIZED_NEXT_WORK,
        },
    ]


def _rejected_routes() -> list[dict[str, str]]:
    return [
        {
            "name": "alpha_l2_simplex_floor_sensitivity",
            "reason": (
                "The completed objective/label sensitivity diagnosis found no "
                "credible nonworse direction across the tested convex knobs."
            ),
        },
        {
            "name": "overall_mean_only_acceptance",
            "reason": (
                "Critical Top-1 bucket and oracle-gap failures remain, so an "
                "overall mean improvement cannot authorize replay or promotion."
            ),
        },
        {
            "name": "future_outcome_online_feature",
            "reason": (
                "Closed-loop outcomes are offline labels/evaluation evidence "
                "only and would leak future information if used online."
            ),
        },
        {
            "name": "direct_closed_loop_replay_from_sensitivity",
            "reason": (
                "The source route rejected all variants; replay would spend "
                "budget without a legal no-leak selector hypothesis."
            ),
        },
        {
            "name": "dp_change_or_retraining",
            "reason": "DP is fixed and must remain a black-box candidate generator.",
        },
        {
            "name": "classic_benders_claim_for_finite_selector",
            "reason": (
                "No master/subproblem, dual, or valid cut construction exists "
                "for the DP-side finite-candidate selector in this gate."
            ),
        },
    ]


def _atom_admissibility_contract() -> dict[str, Any]:
    return {
        "required_properties": [
            "available at the current tick before selection",
            "defined per finite DP candidate",
            "independent of posterior closed-loop outcomes",
            "numeric, deterministic for fixed logs, and auditable",
            "nonnegative, or explicitly represented as nonnegative signed parts",
            "compatible with score_k(w)=a_k^T w after normalization",
        ],
        "must_document_for_each_atom": [
            "source field or computation",
            "candidate-level shape",
            "no-leak argument",
            "nonnegativity or signed-split argument",
            "normalization and clipping rule",
            "why the simplex/CVaR/L2 master remains convex",
        ],
        "not_allowed": [
            "closed-loop realized collision, red-light, near-miss, comfort, or completion outcomes as runtime atoms",
            "trajectory-coordinate optimization convexity claims",
            "DP model or weight changes",
        ],
    }


def _proof_objective_contract() -> dict[str, Any]:
    return {
        "score": {
            "name": "SafetyCost_v1_or_predeclared_successor",
            "direction": "lower_is_better",
            "claim_rule": (
                "CAMP selector must be nonworse or better than DP Top-1 with "
                "bucket-wise hard-component gates and reported tail risk"
            ),
        },
        "comparators": [
            "DP Top-1",
            "current logged CAMP",
            "hard-guarded candidate-branch oracle",
        ],
        "required_buckets": [
            "normal",
            "traffic_light",
            "red_light_turn",
            "sharp_turn",
            "npc_interaction",
            "dense_scene",
            "lane_change_or_merge",
        ],
        "blocked_until_preflight_passes": [
            "CAMP retraining",
            "closed-loop replay",
            "online selector promotion",
            "Full36",
            "formal seeds",
        ],
    }


def _redesign_options() -> list[dict[str, Any]]:
    return [
        {
            "name": "support_inventory_refresh",
            "priority": 1,
            "recommended_first": True,
            "status": "authorized_preflight_only",
            "purpose": (
                "Inventory current-tick candidate fields and source tensors "
                "before proposing any new atom family."
            ),
            "acceptance": [
                "lists every candidate-level no-leak source field considered",
                "marks each field as closed, unavailable, or admissible for atom preflight",
                "does not train, replay, or change selector behavior",
            ],
        },
        {
            "name": "no_leak_atom_schema_preflight",
            "priority": 2,
            "recommended_first": False,
            "status": "conditional_after_support_inventory",
            "purpose": (
                "Define a materially new current-tick atom family only if the "
                "inventory finds admissible support not already closed."
            ),
            "acceptance": [
                "each atom satisfies the admissibility contract",
                "new score remains affine in CAMP weights",
                "no future outcome field enters runtime selection",
            ],
        },
        {
            "name": "proof_objective_v2_design",
            "priority": 3,
            "recommended_first": False,
            "status": "design_only",
            "purpose": (
                "Redesign the offline proof/claim contract without changing "
                "runtime features if the atom inventory remains exhausted."
            ),
            "acceptance": [
                "keeps DP Top-1 and current CAMP comparators",
                "uses posterior outcomes only as offline labels",
                "declares bucket-wise hard gates before any experiment",
            ],
        },
    ]


def _final_decision(passed: bool) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else BLOCKED_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "recommended_first_action": (
            "support_inventory_refresh" if passed else "repair_source_diagnosis"
        ),
        "training_execution_authorized": False,
        "camp_retraining_authorized": False,
        "CAMP_retraining_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "closed_loop_replay_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "full36_authorized": False,
        "Full36_authorized": False,
        "formal_seeds_authorized": False,
        "dp_modification_authorized": False,
        "DP_modification_authorized": False,
        "classic_benders_claim_authorized": False,
        "next_step": (
            "Run a current-tick no-leak atom support inventory preflight."
            if passed
            else "Repair or rerun the source sensitivity diagnosis before redesign."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["sensitivity_summary"]
    lines = [
        "# No-Leak Atom or Proof-Objective Redesign Plan",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        f"- recommended first action: `{decision['recommended_first_action']}`",
        f"- closed-loop replay authorized: `{decision['closed_loop_replay_authorized']}`",
        f"- CAMP retraining authorized: `{decision['camp_retraining_authorized']}`",
        f"- formal seeds authorized: `{decision['formal_seeds_authorized']}`",
        "",
        "## Source Diagnosis Summary",
        "",
        f"- persistent failed checks: `{', '.join(summary['persistent_failed_checks'])}`",
        f"- missing required failed checks: `{', '.join(summary['missing_required_persistent_failures']) or 'none'}`",
        f"- credible direction candidates: `{', '.join(summary['credible_direction_candidates']) or 'none'}`",
        f"- Top-1 failure counts: `{summary['top1_failure_counts']}`",
        f"- oracle-gap failure counts: `{summary['oracle_gap_failure_counts']}`",
        "",
        "## Rejected Routes",
        "",
    ]
    for route in report["rejected_routes"]:
        lines.append(f"- `{route['name']}`: {route['reason']}")
    lines.extend(["", "## Redesign Options", ""])
    for option in report["redesign_options"]:
        lines.append(
            f"- `{option['name']}`: priority `{option['priority']}`, "
            f"status `{option['status']}`, recommended_first="
            f"`{option['recommended_first']}`. {option['purpose']}"
        )
    lines.extend(
        [
            "",
            "## Atom Admissibility Contract",
            "",
        ]
    )
    for item in report["atom_admissibility_contract"]["required_properties"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Proof Objective Contract",
            "",
            f"- score: `{report['proof_objective_contract']['score']['name']}`",
            f"- claim rule: {report['proof_objective_contract']['score']['claim_rule']}",
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


def _blocked_action_checks(decision: dict[str, Any], prefix: str) -> list[dict[str, Any]]:
    return [
        _check_equal(f"{prefix}_{name}_false", decision.get(name), False)
        for name in BLOCKED_ACTIONS
        if name in decision
    ]


def _check_equal(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": actual == expected,
        "actual": actual,
        "expected": expected,
    }


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
