#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SOURCE_STATUS = "offline_convex_selector_training_failure_diagnosed"
SOURCE_NEXT_WORK = "offline_convex_objective_and_label_sensitivity_plan_only"

READY_STATUS = "offline_convex_objective_label_sensitivity_plan_ready"
BLOCKED_STATUS = "offline_convex_objective_label_sensitivity_plan_blocked"
AUTHORIZED_NEXT_WORK = "implement_objective_label_sensitivity_dry_run_wrapper_only"

REQUIRED_TRAINING_TOKENS = (
    "--label_source",
    "safety_cost_v1_hard_guarded",
    "--alpha",
    "--l2_reg",
    "--min_atom_weight",
    "solve_robust_margin_cutting_plane",
    "project_simplex_rows",
)
REQUIRED_EVAL_TOKENS = (
    "selector_comparison",
    "weighted_component_delta_mean",
    "run_level_evaluated_minus_logged_cost_ci",
    "--fail_on_formal_seeds",
)
REQUIRED_PROOF_TOKENS = (
    "safety_cost_trained_selector_vs_top1",
    "safety_cost_trained_selector_gap_closed",
    "formal_seeds_authorized",
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
            "Plan-only objective/label sensitivity gate after a failed offline "
            "convex DP-CAMP selector dry run. This emits a predeclared finite "
            "experiment contract; it does not train or run Diffusion Planner."
        )
    )
    parser.add_argument("--diagnosis_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--training_source",
        type=Path,
        default=Path("scripts/integrations/train_diffusion_planner_robust_camp.py"),
    )
    parser.add_argument(
        "--eval_source",
        type=Path,
        default=Path("scripts/integrations/evaluate_diffusion_planner_camp_safety_cost.py"),
    )
    parser.add_argument(
        "--proof_source",
        type=Path,
        default=Path("scripts/integrations/summarize_diffusion_planner_camp_safety_cost_proof.py"),
    )
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        diagnosis=_load_json(args.diagnosis_json),
        label=args.label,
        training_source=args.training_source,
        eval_source=args.eval_source,
        proof_source=args.proof_source,
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
    training_source: Path,
    eval_source: Path,
    proof_source: Path,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source_checks = [
        *_diagnosis_checks(diagnosis),
        _token_check("training_source_supports_existing_objective_knobs", training_source, REQUIRED_TRAINING_TOKENS),
        _token_check("eval_source_reports_logged_selector_regressions", eval_source, REQUIRED_EVAL_TOKENS),
        _token_check("proof_source_reports_bucket_gates", proof_source, REQUIRED_PROOF_TOKENS),
    ]
    diagnosis_summary = _diagnosis_summary(diagnosis)
    rejected_routes = _rejected_routes(diagnosis_summary)
    plan_checks = _plan_checks(diagnosis_summary, rejected_routes)
    passed = all(check["passed"] for check in [*source_checks, *plan_checks])
    return {
        "analysis": {
            "name": "dp_camp_offline_convex_objective_label_sensitivity_plan_v1",
            "label": label,
            "role": (
                "plan-only gate for a finite objective/label sensitivity dry-run "
                "wrapper over existing non-formal DP candidate logs"
            ),
            "training": False,
            "training_execution": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "paths": {
                **(paths or {}),
                "training_source": str(training_source),
                "eval_source": str(eval_source),
                "proof_source": str(proof_source),
            },
            "math_boundary": (
                "The next sensitivity wrapper may run only offline convex CAMP "
                "weight training over fixed DP candidate logs. DP remains a "
                "black-box candidate generator. Candidate features are finite "
                "current-tick constants; selector scores remain affine "
                "score_k(w)=a_k^T w; simplex constraints, L2 regularization, and "
                "mean/CVaR risk remain convex. Closed-loop outcomes remain "
                "offline labels/evaluation targets and must not become online "
                "selector inputs. This plan is not a DP-side classical Benders "
                "claim."
            ),
        },
        "source_checks": source_checks,
        "diagnosis_summary": diagnosis_summary,
        "rejected_routes": rejected_routes,
        "plan_checks": plan_checks,
        "predeclared_sensitivity_plan": _sensitivity_plan(),
        "accept_reject_gates": _accept_reject_gates(),
        "wrapper_requirements": _wrapper_requirements(),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed),
    }


def _diagnosis_checks(diagnosis: dict[str, Any]) -> list[dict[str, Any]]:
    decision = diagnosis.get("final_decision") or {}
    return [
        _check_equal("diagnosis_status_ready", decision.get("status"), SOURCE_STATUS),
        _check_equal("diagnosis_passed", decision.get("passed"), True),
        _check_equal("diagnosis_rejected_failed_selector", decision.get("dry_run_selector_rejected"), True),
        _check_equal(
            "diagnosis_authorizes_plan_only",
            decision.get("authorized_next_work"),
            SOURCE_NEXT_WORK,
        ),
        *_blocked_action_checks(decision, "diagnosis"),
    ]


def _diagnosis_summary(diagnosis: dict[str, Any]) -> dict[str, Any]:
    selector = diagnosis.get("selector_regression") or {}
    proof = diagnosis.get("proof_failures") or {}
    training = diagnosis.get("training_summary") or {}
    hypotheses = diagnosis.get("failure_hypotheses") or []
    return {
        "changed_record_rate": selector.get("changed_record_rate"),
        "evaluated_minus_logged_cost_mean": selector.get("evaluated_minus_logged_cost_mean"),
        "evaluated_minus_logged_ci_high": _get(
            selector,
            "run_level_evaluated_minus_logged_cost_ci",
            "ci95_high",
        ),
        "regression_components": selector.get("regression_components") or [],
        "top_weights": training.get("top_weights") or [],
        "top1_bucket_failures": _get(
            proof,
            "safety_cost_trained_selector_vs_top1",
            "bucket_failures",
        )
        or {},
        "oracle_gap_bucket_failures": _get(
            proof,
            "safety_cost_trained_selector_gap_closed",
            "bucket_failures",
        )
        or {},
        "failure_hypotheses": [
            str(item.get("name")) for item in hypotheses if isinstance(item, dict)
        ],
    }


def _rejected_routes(summary: dict[str, Any]) -> list[dict[str, str]]:
    routes = [
        {
            "name": "rerun_same_hard_guarded_cvar_selector",
            "reason": (
                "The source dry run already converged but failed critical "
                "bucket Top-1 gates, oracle-gap gates, and logged-selector "
                "nonworse evidence."
            ),
        },
        {
            "name": "overall_mean_only_acceptance",
            "reason": (
                "Overall CAMP-minus-Top-1 mean was negative while required "
                "traffic-light, red-light-turn, and sharp-turn bucket gates failed."
            ),
        },
        {
            "name": "progress_lane_hard_threshold_tuning_without_new_evidence",
            "reason": (
                "Earlier progress/lane-hard and interaction routes were "
                "rejected or limited; the next route must introduce a "
                "predeclared objective/label sensitivity contract instead of "
                "retuning old thresholds."
            ),
        },
        {
            "name": "collision_regression_ignored",
            "reason": (
                "The latest diagnosis identified collision and near-miss as "
                "positive selector-vs-logged SafetyCost regressions."
            ),
        },
    ]
    if not summary["regression_components"]:
        routes.append(
            {
                "name": "component_regression_free_claim",
                "reason": "The source diagnosis did not provide component evidence strong enough for this claim.",
            }
        )
    return routes


def _plan_checks(
    summary: dict[str, Any],
    rejected_routes: list[dict[str, str]],
) -> list[dict[str, Any]]:
    return [
        {
            "name": "top1_bucket_failures_are_explicit",
            "passed": bool(summary["top1_bucket_failures"]),
            "bucket_failures": summary["top1_bucket_failures"],
        },
        {
            "name": "oracle_gap_failures_are_explicit",
            "passed": bool(summary["oracle_gap_bucket_failures"]),
            "bucket_failures": summary["oracle_gap_bucket_failures"],
        },
        {
            "name": "logged_selector_regression_gate_required",
            "passed": summary["evaluated_minus_logged_ci_high"] is not None
            and float(summary["evaluated_minus_logged_ci_high"]) > 0.0,
            "ci95_high": summary["evaluated_minus_logged_ci_high"],
            "reason": (
                "A positive CI high in the failed dry run requires the next "
                "sensitivity wrapper to reject variants that are not nonworse "
                "or explicitly bounded against the logged selector."
            ),
        },
        {
            "name": "collision_or_near_miss_regression_requires_component_gate",
            "passed": any(
                row.get("name") in {"collision", "near_miss"}
                and float(row.get("value", 0.0)) > 0.0
                for row in summary["regression_components"]
                if isinstance(row, dict)
            ),
            "regression_components": summary["regression_components"][:5],
        },
        {
            "name": "rejected_routes_declared",
            "passed": len(rejected_routes) >= 4,
            "routes": [route["name"] for route in rejected_routes],
        },
    ]


def _sensitivity_plan() -> dict[str, Any]:
    return {
        "scope": (
            "finite predeclared offline dry-run variants over the existing "
            "non-formal input manifest only"
        ),
        "control_variant": {
            "name": "control_reproduce_failed_35fedb8",
            "purpose": (
                "sanity check only; matching the failed selector is expected and "
                "cannot be accepted as an improvement"
            ),
            "parameters": {
                "label_source": "safety_cost_v1_hard_guarded",
                "risk_type": "cvar",
                "alpha": 0.9,
                "l2_reg": 0.0001,
                "min_atom_weight": [],
            },
        },
        "candidate_variants": [
            {
                "name": "tail_alpha_0p95",
                "parameters": {
                    "label_source": "safety_cost_v1_hard_guarded",
                    "risk_type": "cvar",
                    "alpha": 0.95,
                    "l2_reg": 0.0001,
                    "min_atom_weight": [],
                },
                "hypothesis": "stronger tail risk may reduce critical-bucket failures without changing atoms",
            },
            {
                "name": "tail_alpha_0p95_l2_1e3",
                "parameters": {
                    "label_source": "safety_cost_v1_hard_guarded",
                    "risk_type": "cvar",
                    "alpha": 0.95,
                    "l2_reg": 0.001,
                    "min_atom_weight": [],
                },
                "hypothesis": "more regularization may reduce red/stop weight concentration",
            },
            {
                "name": "safety_guard_floor",
                "parameters": {
                    "label_source": "safety_cost_v1_hard_guarded",
                    "risk_type": "cvar",
                    "alpha": 0.95,
                    "l2_reg": 0.001,
                    "min_atom_weight": [
                        "clearance=0.02",
                        "planned_lateral_acceleration_cost=0.04",
                        "dp_prior_jerk_excess_cost=0.02",
                    ],
                },
                "hypothesis": (
                    "simplex lower bounds on already-online atoms may reduce "
                    "collision/near-miss/lateral regressions while preserving "
                    "affine scoring"
                ),
            },
            {
                "name": "balanced_comfort_progress_floor",
                "parameters": {
                    "label_source": "safety_cost_v1_hard_guarded",
                    "risk_type": "cvar",
                    "alpha": 0.95,
                    "l2_reg": 0.001,
                    "min_atom_weight": [
                        "progress_shortfall=0.03",
                        "planned_lateral_acceleration_cost=0.03",
                        "dp_prior_jerk_excess_cost=0.02",
                        "clearance=0.02",
                    ],
                },
                "hypothesis": (
                    "bounded mass away from red/stop atoms may protect progress, "
                    "comfort, and hard-context components"
                ),
            },
        ],
        "deferred_not_in_this_gate": [
            {
                "name": "new_atom_schema",
                "reason": "requires separate atom admissibility and no-leak proof before training",
            },
            {
                "name": "bucket_weighted_master",
                "reason": (
                    "current source support must be designed and tested before "
                    "claiming a convex objective change"
                ),
            },
            {
                "name": "outcome_component_as_online_feature",
                "reason": "future outcome leakage; forbidden",
            },
        ],
    }


def _accept_reject_gates() -> dict[str, Any]:
    return {
        "must_pass_before_any_closed_loop": [
            "formal_seed_logs == 0",
            "DP commit unchanged",
            "control variant reproduces the failed selector within declared tolerance",
            "candidate variant has all required bucket CAMP-minus-Top1 CI highs < 0",
            "candidate variant has all required oracle-gap CI highs <= 0 or a predeclared strictly smaller gap with no bucket regression",
            "evaluated-minus-logged SafetyCost CI high <= 0",
            "collision, near_miss, lane_violation, and realized_red_light weighted component deltas <= 0",
            "fallback rate does not increase",
            "selection/evaluation latency accounting is present if a wrapper records runtime",
        ],
        "reject_if": [
            "any required bucket passes only by hiding records or dropping formal-seed checks",
            "overall mean improves while traffic_light/red_light_turn/sharp_turn fail",
            "collision or near_miss regression remains positive",
            "variant relies on candidate_closed_loop_outcomes as online selector input",
            "variant requires DP code, DP weights, DP candidate generation, or formal seeds",
        ],
        "evidence_required": [
            "training_summary.json",
            "atom_scales_dp_static.json",
            "offline_weights_dp_static.npy",
            "selector_eval.json",
            "camp_vs_top1_safety_cost_proof.json",
            "sensitivity_summary.json with per-variant accept/reject status",
        ],
    }


def _wrapper_requirements() -> dict[str, Any]:
    return {
        "next_wrapper_must": [
            "consume only the accepted non-formal input manifest",
            "run the control and candidate variants as separate output directories",
            "pass --fail_on_formal_seeds during selector evaluation",
            "collect per-variant training/eval/proof return codes and artifact SHA-256 values",
            "mark every variant rejected unless all predeclared gates pass",
            "leave closed-loop replay, Full36, formal seeds, online selector promotion, and CAMP retraining disabled",
        ],
        "source_changes_allowed_next": [
            "wrapper orchestration and tests only",
            "no DP changes",
            "no new atom schema",
            "no online selector behavior change",
        ],
    }


def _final_decision(passed: bool) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else BLOCKED_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
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
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["diagnosis_summary"]
    plan = report["predeclared_sensitivity_plan"]
    lines = [
        "# Offline Convex Objective/Label Sensitivity Plan",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        f"- training execution authorized: `{decision['training_execution_authorized']}`",
        f"- closed-loop replay authorized: `{decision['closed_loop_replay_authorized']}`",
        f"- formal seeds authorized: `{decision['formal_seeds_authorized']}`",
        "",
        "## Diagnosis Inputs",
        "",
        f"- evaluated-minus-logged CI high: `{summary['evaluated_minus_logged_ci_high']}`",
        f"- Top-1 bucket failures: `{summary['top1_bucket_failures']}`",
        f"- oracle-gap bucket failures: `{summary['oracle_gap_bucket_failures']}`",
        "",
        "## Source Checks",
        "",
        "| Check | Passed |",
        "| --- | --- |",
    ]
    for check in report["source_checks"]:
        lines.append(f"| `{check['name']}` | `{check['passed']}` |")
    lines.extend(["", "## Rejected Routes", ""])
    for route in report["rejected_routes"]:
        lines.append(f"- `{route['name']}`: {route['reason']}")
    lines.extend(["", "## Predeclared Variants", ""])
    control = plan["control_variant"]
    lines.append(f"- `{control['name']}`: {control['purpose']}")
    for variant in plan["candidate_variants"]:
        lines.append(
            f"- `{variant['name']}`: {variant['hypothesis']}; "
            f"parameters=`{json.dumps(variant['parameters'], sort_keys=True)}`"
        )
    lines.extend(["", "## Accept/Reject Gates", ""])
    for item in report["accept_reject_gates"]["must_pass_before_any_closed_loop"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Mathematical Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _token_check(name: str, path: Path, tokens: tuple[str, ...]) -> dict[str, Any]:
    text = _read_text(path)
    missing = [token for token in tokens if token not in text]
    return {
        "name": name,
        "passed": not missing,
        "path": str(path),
        "missing_tokens": missing,
    }


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


def _read_text(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8-sig")


def _get(data: Any, *path: str) -> Any:
    current = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


if __name__ == "__main__":
    main()
