#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


READY_STATUS = "selector_label_weight_preflight_ready"
BLOCKED_STATUS = "selector_label_weight_preflight_blocked"
SOURCE_STATUS = "current_selector_gap_open"
SOURCE_NEXT_WORK = "selector_label_weight_design_preflight"
AUTHORIZED_NEXT_WORK = "offline_convex_selector_training_plan_design_only"

DEFAULT_REQUIRED_BUCKETS = (
    "normal",
    "traffic_light",
    "red_light_turn",
    "sharp_turn",
    "npc_interaction",
    "dense_scene",
    "lane_change_or_merge",
)

BLOCKED_ACTIONS = (
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "full36_authorized",
    "Full36_authorized",
    "formal_seeds_authorized",
    "camp_retraining_authorized",
    "CAMP_retraining_authorized",
    "training_execution_authorized",
    "dp_modification_authorized",
    "DP_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only preflight for DP-CAMP selector label and convex weight "
            "training. It consumes existing oracle/gap reports and does not "
            "train, replay, or change an online selector."
        )
    )
    parser.add_argument("--selector_oracle_gap_json", type=Path, required=True)
    parser.add_argument("--safety_cost_oracle_json", type=Path, required=True)
    parser.add_argument("--selector_eval_json", type=Path, default=None)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selector_eval = (
        None if args.selector_eval_json is None else _load_json(args.selector_eval_json)
    )
    report = build_report(
        selector_oracle_gap=_load_json(args.selector_oracle_gap_json),
        safety_cost_oracle=_load_json(args.safety_cost_oracle_json),
        selector_eval=selector_eval,
        label=args.label,
        paths={
            "selector_oracle_gap_json": str(args.selector_oracle_gap_json),
            "safety_cost_oracle_json": str(args.safety_cost_oracle_json),
            "selector_eval_json": (
                None if args.selector_eval_json is None else str(args.selector_eval_json)
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
    selector_oracle_gap: dict[str, Any],
    safety_cost_oracle: dict[str, Any],
    selector_eval: dict[str, Any] | None = None,
    label: str | None = None,
    paths: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    source_checks = [
        *_selector_gap_checks(selector_oracle_gap),
        *_oracle_checks(safety_cost_oracle),
        *_selector_eval_checks(selector_eval),
    ]
    math_checks = _math_contract_checks()
    passed = all(check["passed"] for check in [*source_checks, *math_checks])
    final_decision = _final_decision(passed)
    return {
        "analysis": {
            "name": "dp_camp_selector_label_weight_preflight_v1",
            "label": label,
            "role": (
                "design-only gate for offline selector labels and convex CAMP "
                "weight training over fixed DP candidate records"
            ),
            "training": False,
            "training_execution": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "paths": paths or {},
            "math_boundary": (
                "DP remains a frozen black-box finite-candidate generator. "
                "The preflight only authorizes writing a training plan where "
                "candidate atoms/features are fixed current-tick constants and "
                "CAMP scores remain affine score_k(w)=a_k^T w. Simplex, L2, "
                "and CVaR-style master terms remain convex. Candidate outcomes "
                "may define offline labels only and are forbidden as online "
                "runtime features. This finite-candidate selector is not a "
                "DP-side classical Benders decomposition unless a valid "
                "master/subproblem, dual, and cut construction is provided."
            ),
        },
        "required_buckets": list(DEFAULT_REQUIRED_BUCKETS),
        "source_checks": source_checks,
        "math_checks": math_checks,
        "label_contract": _label_contract(),
        "optimization_contract": _optimization_contract(),
        "forbidden_contract": _forbidden_contract(),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "final_decision": final_decision,
    }


def _selector_gap_checks(report: dict[str, Any]) -> list[dict[str, Any]]:
    decision = report.get("final_decision") or {}
    return [
        _check_equal(
            "selector_gap_status_current",
            decision.get("status"),
            SOURCE_STATUS,
        ),
        _check_equal(
            "selector_gap_authorizes_this_preflight",
            decision.get("authorized_next_work"),
            SOURCE_NEXT_WORK,
        ),
        _check_equal("selector_gap_not_passed", decision.get("passed"), False),
        _check_equal("selector_gap_oracle_passed", decision.get("oracle_passed"), True),
        _check_equal(
            "selector_gap_evaluated_same_as_logged",
            decision.get("evaluated_same_as_logged"),
            True,
        ),
        _check_equal(
            "selector_gap_evaluated_proof_not_passed",
            decision.get("evaluated_passed_proof_protocol_v2"),
            False,
        ),
        _check_equal(
            "selector_gap_not_closed",
            decision.get("evaluated_gap_closed"),
            False,
        ),
        *_blocked_action_checks(decision, "selector_gap"),
    ]


def _oracle_checks(report: dict[str, Any]) -> list[dict[str, Any]]:
    formal_seed_logs = int(_get(report, "logs", "formal_seed_logs") or 0)
    missing = list(_get(report, "coverage_gaps", "missing_required_buckets") or [])
    buckets = _bucket_names(report.get("by_bucket") or [])
    missing_buckets = sorted(set(DEFAULT_REQUIRED_BUCKETS) - buckets)
    return [
        _check_equal(
            "safety_cost_oracle_opportunity_gate_passed",
            _get(report, "opportunity_gate", "passed"),
            True,
        ),
        _check_equal("safety_cost_oracle_no_formal_seed_logs", formal_seed_logs, 0),
        _check_empty("safety_cost_oracle_no_missing_required_buckets", missing),
        _check_empty("safety_cost_oracle_covers_required_buckets", missing_buckets),
        _check_positive("safety_cost_oracle_has_records", _get(report, "records", "total")),
        _check_positive("safety_cost_oracle_has_logs", _get(report, "logs", "total")),
    ]


def _selector_eval_checks(report: dict[str, Any] | None) -> list[dict[str, Any]]:
    if report is None:
        return [
            {
                "name": "selector_eval_optional",
                "passed": True,
                "note": "selector_eval_json not provided; source is optional",
            }
        ]
    formal_seed_logs = int(_get(report, "logs", "formal_seed_logs") or 0)
    missing = list(_get(report, "coverage_gaps", "missing_required_buckets") or [])
    changed_rate = _number(_get(report, "selector_comparison", "changed_record_rate"))
    mean_delta = _number(
        _get(report, "selector_comparison", "evaluated_minus_logged_cost_mean")
    )
    return [
        _check_equal("selector_eval_no_formal_seed_logs", formal_seed_logs, 0),
        _check_empty("selector_eval_no_missing_required_buckets", missing),
        _check_nonnegative("selector_eval_changed_rate_present", changed_rate),
        _check_equal("selector_eval_current_matches_logged", changed_rate, 0.0),
        _check_equal("selector_eval_mean_delta_zero", mean_delta, 0.0),
    ]


def _math_contract_checks() -> list[dict[str, Any]]:
    return [
        {
            "name": "offline_labels_only",
            "passed": True,
            "reason": (
                "hard-guarded oracle outcomes may be labels after replay, but "
                "must never be online inputs"
            ),
        },
        {
            "name": "affine_score_preserved",
            "passed": True,
            "reason": "candidate score remains score_k(w)=a_k^T w",
        },
        {
            "name": "convex_training_families_available",
            "passed": True,
            "reason": (
                "softmax cross-entropy over logits -a_k^T w and pairwise hinge "
                "losses are convex in w for fixed candidate coefficients"
            ),
        },
        {
            "name": "finite_selector_not_classical_benders",
            "passed": True,
            "reason": (
                "the next step is a finite-candidate selector training plan, "
                "not a DP-side Benders master/subproblem construction"
            ),
        },
    ]


def _label_contract() -> dict[str, Any]:
    return {
        "target": "hard_guarded_oracle_selected_candidate",
        "source": "offline candidate_closed_loop_outcomes from fixed DP candidate logs",
        "online_runtime_feature_allowed": False,
        "formal_seeds_allowed": False,
        "records_without_guarded_oracle": (
            "must be handled by a predeclared mask or fallback class in the "
            "training plan; labels must not be fabricated post hoc"
        ),
        "required_bucket_coverage": list(DEFAULT_REQUIRED_BUCKETS),
        "no_future_outcome_leakage": True,
    }


def _optimization_contract() -> dict[str, Any]:
    return {
        "score_convention": (
            "CAMP selects lower scores; for multiclass cross-entropy use "
            "logits_k=-a_k^T w so the oracle target has larger logit."
        ),
        "families": [
            {
                "name": "simplex_linear_softmax_cross_entropy",
                "objective": (
                    "sum fixed nonnegative example weights times softmax "
                    "cross-entropy over logits -a_k^T w, plus optional L2"
                ),
                "constraints": "w >= 0, sum(w) = 1",
                "convexity": (
                    "logits are affine in w for fixed candidate atoms; "
                    "cross-entropy composed with affine logits is convex; "
                    "simplex and L2 terms are convex"
                ),
            },
            {
                "name": "simplex_pairwise_hinge_ranking",
                "objective": (
                    "sum max(0, margin + score_target - score_alternative) "
                    "over fixed candidate pairs"
                ),
                "constraints": "w >= 0, sum(w) = 1",
                "convexity": (
                    "hinge of an affine expression is convex; nonnegative "
                    "fixed weights and convex regularizers preserve convexity"
                ),
            },
            {
                "name": "bucket_or_run_cvar_robust_loss",
                "objective": (
                    "empirical convex loss plus optional CVaR epigraph over "
                    "fixed run or bucket losses"
                ),
                "constraints": "simplex weights and CVaR epigraph variables",
                "convexity": (
                    "CVaR epigraph over convex per-example losses is convex "
                    "when group weights and buckets are predeclared constants"
                ),
            },
        ],
    }


def _forbidden_contract() -> dict[str, Any]:
    return {
        "dp_modification": True,
        "dp_retraining_or_tuning": True,
        "online_selector_promotion": True,
        "full36_or_formal_seeds": True,
        "nonconvex_neural_selector": True,
        "future_outcome_runtime_features": True,
        "post_hoc_bucket_weight_tuning_after_eval": True,
        "atom_schema_change_without_no_leak_gate": True,
        "classical_benders_claim_without_dual_and_cuts": True,
    }


def _final_decision(passed: bool) -> dict[str, Any]:
    decision = {
        "status": READY_STATUS if passed else BLOCKED_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "offline_convex_selector_training_plan_authorized": passed,
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
    if passed:
        decision["next_step"] = (
            "Write an offline convex selector training plan with fixed inputs, "
            "label masks, loss, constraints, split policy, robust bucket "
            "weighting, artifact schema, tests, and accept/reject gates."
        )
    else:
        decision["next_step"] = (
            "Repair the source oracle/gap evidence before writing any training "
            "plan, training script, replay command, or online selector path."
        )
    return decision


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Selector Label/Weight Preflight",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        f"- training execution authorized: `{decision['training_execution_authorized']}`",
        f"- CAMP retraining authorized: `{decision['camp_retraining_authorized']}`",
        "",
        "## Source Checks",
        "",
        "| Check | Passed | Detail |",
        "| --- | --- | --- |",
    ]
    for check in report["source_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"{_detail(check)} |"
        )
    lines.extend(["", "## Math Checks", "", "| Check | Passed | Reason |", "| --- | --- | --- |"])
    for check in report["math_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"{check.get('reason', '')} |"
        )
    lines.extend(
        [
            "",
            "## Label Contract",
            "",
            f"- target: `{report['label_contract']['target']}`",
            f"- source: `{report['label_contract']['source']}`",
            "- online runtime feature allowed: "
            f"`{report['label_contract']['online_runtime_feature_allowed']}`",
            "- records without guarded oracle: "
            f"{report['label_contract']['records_without_guarded_oracle']}",
            "",
            "## Convex Optimization Families",
            "",
        ]
    )
    for family in report["optimization_contract"]["families"]:
        lines.extend(
            [
                f"### {family['name']}",
                "",
                f"- objective: {family['objective']}",
                f"- constraints: {family['constraints']}",
                f"- convexity: {family['convexity']}",
                "",
            ]
        )
    lines.extend(["## Forbidden Actions", ""])
    for action, forbidden in report["forbidden_contract"].items():
        lines.append(f"- `{action}` = `{forbidden}`")
    lines.extend(["", "## Mathematical Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _blocked_action_checks(
    decision: dict[str, Any],
    prefix: str,
) -> list[dict[str, Any]]:
    return [
        _check_equal(f"{prefix}_{name}_false", decision.get(name, False), False)
        for name in BLOCKED_ACTIONS
    ]


def _check_equal(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": actual == expected,
        "actual": actual,
        "expected": expected,
    }


def _check_empty(name: str, values: list[Any]) -> dict[str, Any]:
    return {"name": name, "passed": not values, "values": values}


def _check_positive(name: str, value: Any) -> dict[str, Any]:
    number = _number(value)
    return {"name": name, "passed": number is not None and number > 0, "actual": value}


def _check_nonnegative(name: str, value: Any) -> dict[str, Any]:
    number = _number(value)
    return {"name": name, "passed": number is not None and number >= 0, "actual": value}


def _bucket_names(rows: list[Any]) -> set[str]:
    return {str(row.get("bucket")) for row in rows if isinstance(row, dict)}


def _detail(check: dict[str, Any]) -> str:
    if "note" in check:
        return str(check["note"])
    if "values" in check:
        return ", ".join(str(value) for value in check["values"]) or "none"
    if "expected" in check:
        return f"actual=`{check.get('actual')}`, expected=`{check.get('expected')}`"
    if "actual" in check:
        return f"actual=`{check.get('actual')}`"
    return ""


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _get(data: Any, *path: str) -> Any:
    current = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


if __name__ == "__main__":
    main()
