#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SOURCE_STATUS = "post_bridge_proof_objective_next_design_plan_ready"
SOURCE_NEXT_WORK = "predeclare_targeted_safety_intervention_proof_objective_only"
SOURCE_RECOMMENDED_FIRST = "predeclare_targeted_safety_intervention_proof_objective"

READY_STATUS = "targeted_safety_intervention_proof_objective_predeclared"
BLOCKED_STATUS = "targeted_safety_intervention_proof_objective_blocked_by_source_gate"
AUTHORIZED_NEXT_WORK = "targeted_safety_intervention_scenario_manifest_design_only"

OVERALL_BUCKET = "overall"
NORMAL_BUCKET = "normal"
SAFETY_CRITICAL_BUCKETS = (
    "traffic_light",
    "red_light_turn",
    "sharp_turn",
    "npc_interaction",
    "dense_scene",
    "lane_change_or_merge",
)
REQUIRED_BUCKETS = (OVERALL_BUCKET, NORMAL_BUCKET, *SAFETY_CRITICAL_BUCKETS)

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
            "Predeclare the targeted safety-intervention proof objective after "
            "the post-bridge design gate. This is design-only and does not run "
            "DP, train CAMP, or change online selection."
        )
    )
    parser.add_argument("--post_bridge_plan_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        post_bridge_plan=_load_json(args.post_bridge_plan_json),
        label=args.label,
        paths={"post_bridge_plan_json": str(args.post_bridge_plan_json)},
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
    post_bridge_plan: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source = _source_gate(post_bridge_plan)
    objective = _objective_contract()
    checks = _plan_checks(source, objective)
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_targeted_safety_intervention_proof_objective_v1",
            "label": label,
            "role": (
                "design-only predeclaration of a targeted safety-intervention "
                "proof objective after the current observable descriptor route "
                "is closed"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_leakage": False,
            "paths": paths or {},
            "math_boundary": (
                "DP remains a frozen black-box finite-candidate generator. "
                "This objective is an offline proof/evaluation contract only; "
                "it does not create runtime atoms or selector inputs. If later "
                "CAMP training is separately authorized, runtime atoms must be "
                "fixed current-tick finite-candidate coefficients a_k, "
                "nonnegative or represented by nonnegative signed parts, so "
                "score_k(w)=a_k^T w remains affine and the simplex/CVaR/L2 "
                "robust master remains convex. Offline outcomes may define "
                "labels and proof gates, but must not be online features. No "
                "DP-side classical Benders master/subproblem, dual, or cut is "
                "constructed."
            ),
        },
        "source_post_bridge_gate": source,
        "objective_contract": objective,
        "plan_checks": checks,
        "closed_or_blocked_routes": _closed_or_blocked_routes(),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed),
    }


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    final = _dict(report.get("final_decision"))
    conflicts = [key for key in BLOCKED_ACTIONS if bool(final.get(key))]
    return {
        "status": final.get("status"),
        "passed": (
            final.get("status") == SOURCE_STATUS
            and bool(final.get("passed"))
            and final.get("authorized_next_work") == SOURCE_NEXT_WORK
            and final.get("recommended_first_action") == SOURCE_RECOMMENDED_FIRST
            and not conflicts
        ),
        "authorized_next_work": final.get("authorized_next_work"),
        "recommended_first_action": final.get("recommended_first_action"),
        "blocked_action_conflicts": conflicts,
    }


def _objective_contract() -> dict[str, Any]:
    return {
        "name": "TargetedSafetyInterventionObjective_v1",
        "score": {
            "name": "SafetyCost_v1",
            "direction": "lower_is_better",
            "formula": (
                "100*collision + 10*near_miss + 20*lane + 30*realized_red "
                "+ 15*planned_red + clip(jerk/10,0,10) "
                "+ 2*clip(lateral/2,0,10) + 2*clip(1-completion,0,1)"
            ),
            "component_fields": {
                "collision": "obb_collision_rate",
                "near_miss": "near_miss_rate",
                "lane": "lane_violation_rate",
                "realized_red": "red_light_violation_rate",
                "planned_red": "planned_red_light_violation_rate",
                "jerk": "mean_jerk_magnitude_mps3",
                "lateral": "mean_lateral_acceleration_mps2",
                "completion": "route_completion_rate",
            },
        },
        "required_buckets": list(REQUIRED_BUCKETS),
        "target_buckets": list(SAFETY_CRITICAL_BUCKETS),
        "guard_buckets": [OVERALL_BUCKET, NORMAL_BUCKET],
        "bucket_manifest_rules": [
            "bucket membership must be predeclared from route/config metadata",
            "filters may not inspect SafetyCost, collision, red-light, completion, jerk, or any closed-loop outcome",
            "every run belongs to overall and may belong to explicit target/guard buckets",
            "all target and guard buckets must be nonempty before any proof claim",
        ],
        "primary_claim": {
            "comparison": "CAMP_minus_DP_Top1",
            "target_aggregate": "pooled paired target buckets",
            "rule": (
                "hard_gates_pass_all_required_buckets and "
                "ci95_high(TargetSafetyCost_CAMP_minus_DP_Top1) < 0"
            ),
            "tail_rule": (
                "ci95_high(TargetSafetyCost_CVaR90_CAMP_minus_DP_Top1) <= 0"
            ),
            "interpretation": (
                "CAMP is useful as a targeted safety intervention only if it "
                "reduces SafetyCost in safety-critical buckets while guard "
                "buckets and hard-safety gates do not regress."
            ),
        },
        "guard_claims": {
            "normal_non_degradation": (
                "ci95_high(SafetyCost_normal_CAMP_minus_DP_Top1) <= 0"
            ),
            "overall_non_degradation": (
                "ci95_high(SafetyCost_overall_CAMP_minus_DP_Top1) <= 0"
            ),
            "hard_gate_scope": "overall, normal, and every target bucket",
            "completion": "paired route_completion_rate CI low >= -0.001 in every required bucket",
            "latency": "total planning-path p95 CI high <= 95 ms before any expansion",
            "fallback": "fallback rate must be reported and cannot explain the win",
        },
        "comparators": [
            "DP Top-1",
            "current logged CAMP",
            "hard-guarded candidate-branch oracle",
            "future targeted CAMP selector if separately authorized",
        ],
        "evidence_ladder": [
            {
                "gate": "targeted_scenario_manifest_design",
                "allowed": "write manifest and evidence matrix only",
                "promotion_condition": "all required target and guard buckets are covered without outcome-field filters",
            },
            {
                "gate": "targeted_candidate_branch_oracle_audit",
                "allowed": "offline nonformal outcome labels only",
                "promotion_condition": "hard-guarded oracle has target-bucket opportunity with guard nondegradation",
            },
            {
                "gate": "targeted_training_or_selector_design",
                "allowed": "only after oracle and no-leak atom gates pass",
                "promotion_condition": "runtime score stays affine and atoms are current-tick finite coefficients",
            },
            {
                "gate": "tiny_paired_nonformal_smoke",
                "allowed": "only after unit, latency, and selector-equivalence gates pass",
                "promotion_condition": "target, guard, hard-safety, fallback, and latency gates all pass",
            },
            {
                "gate": "larger_nonformal_matrix",
                "allowed": "only after tiny smoke has positive latency/safety margin",
                "promotion_condition": "predeclared target objective and CVaR gates pass",
            },
            {
                "gate": "formal_seeds",
                "allowed": "separate authorization only",
                "promotion_condition": "development gates are complete and frozen",
            },
        ],
        "runtime_no_leak_contract": [
            "closed-loop outcome labels are offline proof labels only",
            "SafetyCost values are never online selector inputs",
            "bucket filters cannot depend on outcomes",
            "candidate branch oracle choices are not runtime atoms",
            "new atoms require a separate current-tick no-leak source gate",
        ],
    }


def _plan_checks(source: dict[str, Any], objective: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "name": "source_post_bridge_plan_ready",
            "passed": source["status"] == SOURCE_STATUS,
            "actual": source["status"],
            "expected": SOURCE_STATUS,
        },
        {
            "name": "source_authorizes_targeted_objective_only",
            "passed": source["authorized_next_work"] == SOURCE_NEXT_WORK,
            "actual": source["authorized_next_work"],
            "expected": SOURCE_NEXT_WORK,
        },
        {
            "name": "source_recommended_targeted_objective",
            "passed": source["recommended_first_action"] == SOURCE_RECOMMENDED_FIRST,
            "actual": source["recommended_first_action"],
            "expected": SOURCE_RECOMMENDED_FIRST,
        },
        {
            "name": "required_buckets_include_normal_and_targets",
            "passed": all(bucket in objective["required_buckets"] for bucket in REQUIRED_BUCKETS),
            "required_buckets": objective["required_buckets"],
        },
        {
            "name": "target_buckets_exclude_normal_guard",
            "passed": NORMAL_BUCKET not in objective["target_buckets"]
            and OVERALL_BUCKET not in objective["target_buckets"],
            "target_buckets": objective["target_buckets"],
        },
        {
            "name": "guard_claims_include_normal_and_overall",
            "passed": "normal_non_degradation" in objective["guard_claims"]
            and "overall_non_degradation" in objective["guard_claims"],
            "guard_claims": sorted(objective["guard_claims"]),
        },
        {
            "name": "no_blocked_action_conflicts",
            "passed": not source["blocked_action_conflicts"],
            "conflicts": source["blocked_action_conflicts"],
        },
        {
            "name": "next_gate_is_manifest_design_not_replay",
            "passed": True,
            "authorized_next_work": AUTHORIZED_NEXT_WORK,
        },
    ]


def _closed_or_blocked_routes() -> list[dict[str, str]]:
    return [
        {
            "name": "global_safetycost_only_claim",
            "reason": (
                "A single global mean can hide safety-critical bucket failures "
                "or normal-scene regressions; it remains a reporting baseline, "
                "not the next proof objective."
            ),
        },
        {
            "name": "targeted_objective_as_selector_feature",
            "reason": (
                "SafetyCost and bucket labels are proof/evaluation constructs "
                "and cannot become online selector inputs."
            ),
        },
        {
            "name": "training_before_target_manifest_and_oracle",
            "reason": (
                "The target and guard buckets must be predeclared, then an "
                "offline hard-guarded oracle must prove opportunity first."
            ),
        },
        {
            "name": "formal_seed_or_full36_from_design_only_gate",
            "reason": "This gate is only a proof-objective predeclaration.",
        },
    ]


def _final_decision(passed: bool) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else BLOCKED_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "recommended_first_action": (
            "targeted_safety_intervention_scenario_manifest_design"
            if passed
            else "repair_post_bridge_proof_objective_source"
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    objective = report["objective_contract"]
    score = objective["score"]
    lines = [
        "# Targeted Safety-Intervention Proof Objective",
        "",
        f"- Status: `{decision['status']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Recommended first action: `{decision['recommended_first_action']}`",
        "",
        "## Score",
        "",
        f"- Name: `{score['name']}`",
        f"- Direction: `{score['direction']}`",
        f"- Formula: `{score['formula']}`",
        "",
        "## Buckets",
        "",
        f"- Required: `{', '.join(objective['required_buckets'])}`",
        f"- Targets: `{', '.join(objective['target_buckets'])}`",
        f"- Guards: `{', '.join(objective['guard_buckets'])}`",
        "",
        "## Primary Claim",
        "",
        f"- Rule: {objective['primary_claim']['rule']}",
        f"- Tail rule: {objective['primary_claim']['tail_rule']}",
        "",
        "## Guard Claims",
        "",
    ]
    for name, rule in objective["guard_claims"].items():
        lines.append(f"- `{name}`: {rule}")
    lines.extend(["", "## Evidence Ladder", ""])
    for step in objective["evidence_ladder"]:
        lines.append(
            f"- `{step['gate']}`: allowed={step['allowed']}; "
            f"promotion={step['promotion_condition']}"
        )
    lines.extend(["", "## Runtime No-Leak Contract", ""])
    for item in objective["runtime_no_leak_contract"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Plan Checks", "", "| Check | Passed |", "| --- | --- |"])
    for check in report["plan_checks"]:
        lines.append(f"| `{check['name']}` | `{check['passed']}` |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This gate does not run DP, train CAMP, promote an online selector, "
            "authorize Full36, or touch formal seeds.",
            "",
        ]
    )
    return "\n".join(lines)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
