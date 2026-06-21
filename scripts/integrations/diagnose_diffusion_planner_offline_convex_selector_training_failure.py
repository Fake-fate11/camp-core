#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np


SOURCE_STATUS = "offline_convex_selector_training_dry_run_complete"
SOURCE_NEXT_WORK = "diagnose_offline_convex_selector_training_failure_modes"
PROOF_INCOMPLETE_STATUS = "proof_incomplete"

READY_STATUS = "offline_convex_selector_training_failure_diagnosed"
BLOCKED_STATUS = "offline_convex_selector_training_failure_diagnosis_blocked"
AUTHORIZED_NEXT_WORK = "offline_convex_objective_and_label_sensitivity_plan_only"

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
            "Diagnose a failed offline convex DP-CAMP selector training dry run. "
            "This is read-only: it does not train, run DP, replay closed loop, "
            "or promote a selector."
        )
    )
    parser.add_argument("--dry_run_json", type=Path, required=True)
    parser.add_argument("--training_summary", type=Path, required=True)
    parser.add_argument("--selector_eval_json", type=Path, required=True)
    parser.add_argument("--proof_json", type=Path, required=True)
    parser.add_argument("--static_weights", type=Path, default=None)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    weights = None
    if args.static_weights is not None:
        weights = np.asarray(np.load(args.static_weights), dtype=np.float64)
    report = build_report(
        dry_run=_load_json(args.dry_run_json),
        training_summary=_load_json(args.training_summary),
        selector_eval=_load_json(args.selector_eval_json),
        proof=_load_json(args.proof_json),
        static_weights=weights,
        label=args.label,
        paths={
            "dry_run_json": str(args.dry_run_json),
            "training_summary": str(args.training_summary),
            "selector_eval_json": str(args.selector_eval_json),
            "proof_json": str(args.proof_json),
            "static_weights": None if args.static_weights is None else str(args.static_weights),
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
    dry_run: dict[str, Any],
    training_summary: dict[str, Any],
    selector_eval: dict[str, Any],
    proof: dict[str, Any],
    static_weights: np.ndarray | None = None,
    label: str | None = None,
    paths: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    source_checks = _source_checks(dry_run, selector_eval, proof)
    passed = all(check["passed"] for check in source_checks)
    comparison = selector_eval.get("selector_comparison") or {}
    evaluated = selector_eval.get("evaluated_selector") or {}
    gates = proof.get("gates") or {}

    proof_failures = _proof_failures(gates)
    bucket_diagnosis = _bucket_diagnosis(
        comparison=comparison,
        evaluated=evaluated,
        proof_failures=proof_failures,
    )
    regression_components = _ranked_positive(
        comparison.get("weighted_component_delta_mean") or {}
    )
    improvement_components = _ranked_negative(
        comparison.get("weighted_component_delta_mean") or {}
    )
    when_worse = comparison.get("when_evaluated_worse") or {}
    top_weights = _top_weights(training_summary, static_weights)
    report = {
        "analysis": {
            "name": "dp_camp_offline_convex_selector_training_failure_diagnosis_v1",
            "label": label,
            "role": (
                "read-only diagnosis of a failed offline convex selector dry run; "
                "the output authorizes only the next plan-only iteration"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "paths": paths or {},
            "math_boundary": (
                "DP remains a fixed black-box candidate generator. This diagnosis "
                "uses only existing non-formal offline artifacts. Candidate atoms "
                "are treated as fixed finite constants and CAMP scoring remains "
                "affine a_k^T w under the simplex/CVaR/L2 convex master. This "
                "report does not construct a DP-side classical Benders "
                "master/subproblem/dual/cut system and must not be cited as one."
            ),
        },
        "source_checks": source_checks,
        "training_summary": _training_summary(training_summary, top_weights),
        "selector_regression": {
            "changed_record_rate": comparison.get("changed_record_rate"),
            "evaluated_minus_logged_cost_mean": comparison.get(
                "evaluated_minus_logged_cost_mean"
            ),
            "run_level_evaluated_minus_logged_cost_ci": comparison.get(
                "run_level_evaluated_minus_logged_cost_ci"
            )
            or {},
            "cost_delta_record_rates": comparison.get("cost_delta_record_rates") or {},
            "regression_components": regression_components,
            "improvement_components": improvement_components,
            "when_evaluated_worse": {
                "records": when_worse.get("records"),
                "regression_components": _ranked_positive(
                    when_worse.get("weighted_component_delta_mean") or {}
                ),
                "atom_pressure": _ranked_by_abs(
                    when_worse.get("selected_atom_delta_mean") or {}
                ),
            },
        },
        "proof_failures": proof_failures,
        "bucket_diagnosis": bucket_diagnosis,
        "failure_hypotheses": _failure_hypotheses(
            top_weights=top_weights,
            regression_components=regression_components,
            comparison=comparison,
            proof_failures=proof_failures,
        ),
        "self_iteration_contract": _self_iteration_contract(),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed),
    }
    return report


def _source_checks(
    dry_run: dict[str, Any],
    selector_eval: dict[str, Any],
    proof: dict[str, Any],
) -> list[dict[str, Any]]:
    dry_decision = dry_run.get("final_decision") or {}
    proof_decision = proof.get("final_decision") or {}
    selector_logs = selector_eval.get("logs") or {}
    return [
        _check_equal("dry_run_status_complete", dry_decision.get("status"), SOURCE_STATUS),
        _check_equal("dry_run_passed", dry_decision.get("passed"), True),
        _check_equal(
            "dry_run_authorizes_failure_diagnosis",
            dry_decision.get("authorized_next_work"),
            SOURCE_NEXT_WORK,
        ),
        _check_equal(
            "dry_run_candidate_branch_proof_failed",
            dry_decision.get("candidate_branch_proof_passed"),
            False,
        ),
        _check_equal(
            "proof_status_incomplete",
            proof_decision.get("status"),
            PROOF_INCOMPLETE_STATUS,
        ),
        _check_equal(
            "proof_candidate_branch_failed",
            proof_decision.get("safety_cost_trained_selector_candidate_branch_proof"),
            False,
        ),
        _check_equal(
            "selector_eval_has_no_formal_seed_logs",
            selector_logs.get("formal_seed_logs"),
            0,
        ),
    ]


def _training_summary(
    training_summary: dict[str, Any],
    top_weights: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "converged": training_summary.get("converged"),
        "final_master_gap": training_summary.get("final_master_gap"),
        "input_records": training_summary.get("input_records"),
        "num_records_after_hard_guarded_feasibility": training_summary.get(
            "num_records_after_hard_guarded_feasibility"
        ),
        "dropped_records_without_eligible_candidate": training_summary.get(
            "dropped_records_without_eligible_candidate"
        ),
        "train": training_summary.get("train") or {},
        "val": training_summary.get("val") or {},
        "top_weights": top_weights,
    }


def _top_weights(
    training_summary: dict[str, Any],
    static_weights: np.ndarray | None,
    *,
    limit: int = 12,
) -> list[dict[str, Any]]:
    if static_weights is None:
        return []
    atom_names = training_summary.get("atom_names")
    if not isinstance(atom_names, list):
        atom_names = _get(training_summary, "atom_scales", "atom_names")
    if not isinstance(atom_names, list):
        atom_names = [f"atom_{idx}" for idx in range(static_weights.size)]
    rows = []
    for idx, value in enumerate(static_weights.tolist()):
        if abs(float(value)) <= 0.0:
            continue
        rows.append(
            {
                "atom": str(atom_names[idx]) if idx < len(atom_names) else f"atom_{idx}",
                "index": idx,
                "weight": float(value),
            }
        )
    rows.sort(key=lambda item: abs(float(item["weight"])), reverse=True)
    return rows[:limit]


def _proof_failures(gates: dict[str, Any]) -> dict[str, Any]:
    top1_gate = gates.get("safety_cost_trained_selector_vs_top1") or {}
    gap_gate = gates.get("safety_cost_trained_selector_gap_closed") or {}
    return {
        "safety_cost_trained_selector_vs_top1": {
            "passed": top1_gate.get("passed"),
            "overall_ci_high": top1_gate.get("overall_ci_high"),
            "bucket_failures": top1_gate.get("bucket_failures") or {},
        },
        "safety_cost_trained_selector_gap_closed": {
            "passed": gap_gate.get("passed"),
            "overall_ci_high": gap_gate.get("overall_ci_high"),
            "bucket_failures": gap_gate.get("bucket_failures") or {},
        },
    }


def _bucket_diagnosis(
    *,
    comparison: dict[str, Any],
    evaluated: dict[str, Any],
    proof_failures: dict[str, Any],
) -> list[dict[str, Any]]:
    comparison_rows = _rows_by_bucket(comparison.get("by_bucket") or [])
    evaluated_rows = _rows_by_bucket(evaluated.get("by_bucket") or [])
    top1_failures = (
        proof_failures["safety_cost_trained_selector_vs_top1"]["bucket_failures"]
        or {}
    )
    gap_failures = (
        proof_failures["safety_cost_trained_selector_gap_closed"]["bucket_failures"]
        or {}
    )
    names = _ordered_bucket_names(
        set(comparison_rows) | set(evaluated_rows) | set(top1_failures) | set(gap_failures)
    )
    rows = []
    for bucket in names:
        comparison_row = comparison_rows.get(bucket) or {}
        evaluated_row = evaluated_rows.get(bucket) or {}
        run_ci = comparison_row.get("run_level_evaluated_minus_logged_cost_ci") or {}
        top1_ci = _ci_high(evaluated_row, "camp_minus_top1")
        cvar_top1_ci = _cvar_ci_high(evaluated_row, "camp_minus_top1")
        gap_ci = _ci_high(evaluated_row, "camp_minus_hard_guarded_oracle")
        rows.append(
            {
                "bucket": bucket,
                "records": comparison_row.get("records") or evaluated_row.get("records"),
                "changed_record_rate": comparison_row.get("changed_record_rate"),
                "evaluated_minus_logged_cost_mean": comparison_row.get(
                    "evaluated_minus_logged_cost_mean"
                ),
                "evaluated_minus_logged_cost_ci_high": run_ci.get("ci95_high"),
                "camp_minus_top1_ci_high": top1_ci,
                "cvar90_camp_minus_top1_ci_high": cvar_top1_ci,
                "camp_minus_hard_guarded_oracle_ci_high": gap_ci,
                "top1_gate_failed": bucket in top1_failures,
                "gap_gate_failed": bucket in gap_failures,
                "regression_components": _ranked_positive(
                    comparison_row.get("weighted_component_delta_mean") or {}
                ),
                "atom_pressure": _ranked_by_abs(
                    comparison_row.get("selected_atom_delta_mean") or {}
                ),
                "candidate_pool_coverage": evaluated_row.get("candidate_pool_coverage")
                or {},
                "failure_modes": evaluated_row.get("failure_mode_rates")
                or evaluated_row.get("failure_modes")
                or {},
            }
        )
    return rows


def _failure_hypotheses(
    *,
    top_weights: list[dict[str, Any]],
    regression_components: list[dict[str, Any]],
    comparison: dict[str, Any],
    proof_failures: dict[str, Any],
) -> list[dict[str, Any]]:
    hypotheses: list[dict[str, Any]] = []
    top_weight_map = {row["atom"]: float(row["weight"]) for row in top_weights}
    red_stop_weight = top_weight_map.get("planned_red_light_cost", 0.0) + top_weight_map.get(
        "red_stopping_margin_cost",
        0.0,
    )
    if red_stop_weight >= 0.75:
        hypotheses.append(
            {
                "name": "weight_mass_concentrated_on_red_stop_atoms",
                "evidence": {"red_stop_weight": red_stop_weight, "top_weights": top_weights[:5]},
                "next_check": (
                    "Plan-only sensitivity should test whether bucket-balanced "
                    "hard labels or additional non-red hard components reduce "
                    "critical-bucket regressions without changing the CAMP convex "
                    "score form."
                ),
            }
        )
    if regression_components:
        hypotheses.append(
            {
                "name": "trained_selector_worsens_weighted_safety_components_vs_logged",
                "evidence": {"top_regressions": regression_components[:5]},
                "next_check": (
                    "Inspect whether the robust margin objective permits collision, "
                    "near-miss, or route-shortfall regressions while optimizing the "
                    "dominant atoms; do this over the existing manifest first."
                ),
            }
        )
    run_ci_high = _get(
        comparison,
        "run_level_evaluated_minus_logged_cost_ci",
        "ci95_high",
    )
    if run_ci_high is not None and float(run_ci_high) > 0.0:
        hypotheses.append(
            {
                "name": "trained_selector_not_nonworse_than_logged_selector",
                "evidence": {
                    "evaluated_minus_logged_cost_mean": comparison.get(
                        "evaluated_minus_logged_cost_mean"
                    ),
                    "ci95_high": run_ci_high,
                },
                "next_check": (
                    "Any next objective must predeclare logged-selector nonworse "
                    "or bounded-regression gates before another training dry run."
                ),
            }
        )
    top1_failures = proof_failures["safety_cost_trained_selector_vs_top1"][
        "bucket_failures"
    ]
    if top1_failures:
        hypotheses.append(
            {
                "name": "critical_bucket_top1_gate_failure",
                "evidence": {"bucket_failures": top1_failures},
                "next_check": (
                    "Next plan must report bucket-wise constraints and validation "
                    "splits; an overall negative mean is insufficient."
                ),
            }
        )
    gap_failures = proof_failures["safety_cost_trained_selector_gap_closed"][
        "bucket_failures"
    ]
    if gap_failures:
        hypotheses.append(
            {
                "name": "hard_guarded_oracle_gap_remains_open",
                "evidence": {"bucket_failures": gap_failures},
                "next_check": (
                    "Treat this as objective/label/atom-alignment work, not a DP "
                    "retraining request. DP candidate support already contains "
                    "oracle opportunities in the source proof."
                ),
            }
        )
    return hypotheses


def _self_iteration_contract() -> dict[str, Any]:
    return {
        "loop": [
            "status_audit",
            "read_latest_diagnosis_and_reject_repeated_routes",
            "plan_objective_or_label_sensitivity_only",
            "prove_math_boundary_for_any_change",
            "implement_minimal_plan_gate_if_justified",
            "run_targeted_tests",
            "run_existing_manifest_dry_run_only_after_plan_gate",
            "update_audit_doc",
            "commit_push_sync",
            "recompute_accept_reject_and_next_authorized_work",
        ],
        "accept_next_gate_only_if": [
            "formal_seed_logs_remain_zero",
            "DP_commit_and_candidate_generation_unchanged",
            "CAMP_score_remains_affine_in_w",
            "simplex_CVaR_L2_master_remains_convex",
            "no_future_outcome_fields_are_online_inputs",
            "bucket_wise_top1_and_gap_gates_are_predeclared",
        ],
        "reject_next_route_if": [
            "it_changes_DP_or_retrains_DP",
            "it_uses_candidate_closed_loop_outcome_as_online_feature",
            "it_claims_classical_Benders_without_master_subproblem_dual_and_valid_cuts",
            "it_improves_only_overall_mean_while_required_buckets_fail",
            "it_runs_closed_loop_or_formal_seeds_before_candidate_branch_gates_pass",
        ],
    }


def _final_decision(passed: bool) -> dict[str, Any]:
    status = READY_STATUS if passed else BLOCKED_STATUS
    return {
        "status": status,
        "passed": passed,
        "dry_run_selector_rejected": passed,
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
    selector = report["selector_regression"]
    proof = report["proof_failures"]
    lines = [
        "# Offline Convex Selector Training Failure Diagnosis",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- dry-run selector rejected: `{decision['dry_run_selector_rejected']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        f"- training execution authorized: `{decision['training_execution_authorized']}`",
        f"- closed-loop replay authorized: `{decision['closed_loop_replay_authorized']}`",
        f"- formal seeds authorized: `{decision['formal_seeds_authorized']}`",
        "",
        "## Source Checks",
        "",
        "| Check | Passed | Actual | Expected |",
        "| --- | --- | --- | --- |",
    ]
    for check in report["source_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('actual')}` | `{check.get('expected')}` |"
        )
    lines.extend(
        [
            "",
            "## Selector Regression",
            "",
            f"- changed record rate: `{selector['changed_record_rate']}`",
            f"- evaluated-minus-logged mean: `{selector['evaluated_minus_logged_cost_mean']}`",
            "- evaluated-minus-logged CI high: "
            f"`{selector['run_level_evaluated_minus_logged_cost_ci'].get('ci95_high')}`",
            "",
            "Top weighted SafetyCost regressions:",
            "",
        ]
    )
    lines.extend(_ranked_lines(selector["regression_components"]))
    lines.extend(
        [
            "",
            "## Failed Proof Gates",
            "",
            "| Gate | Passed | Overall CI high | Bucket failures |",
            "| --- | --- | ---: | --- |",
        ]
    )
    for name, gate in proof.items():
        lines.append(
            f"| `{name}` | `{gate['passed']}` | `{gate['overall_ci_high']}` | "
            f"{_bucket_failure_text(gate['bucket_failures'])} |"
        )
    lines.extend(
        [
            "",
            "## Bucket Diagnosis",
            "",
            "| Bucket | Records | Changed | Eval-Logged CI High | Top-1 CI High | Gap CI High | Top Regressions |",
            "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in report["bucket_diagnosis"]:
        lines.append(
            f"| `{row['bucket']}` | `{row['records']}` | "
            f"`{row['changed_record_rate']}` | "
            f"`{row['evaluated_minus_logged_cost_ci_high']}` | "
            f"`{row['camp_minus_top1_ci_high']}` | "
            f"`{row['camp_minus_hard_guarded_oracle_ci_high']}` | "
            f"{_ranked_inline(row['regression_components'][:3])} |"
        )
    lines.extend(
        [
            "",
            "## Failure Hypotheses",
            "",
        ]
    )
    for item in report["failure_hypotheses"]:
        lines.extend(
            [
                f"### {item['name']}",
                "",
                f"- evidence: `{json.dumps(item['evidence'], sort_keys=True)}`",
                f"- next check: {item['next_check']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Self-Iteration Contract",
            "",
            "Loop:",
            "",
        ]
    )
    for step in report["self_iteration_contract"]["loop"]:
        lines.append(f"- `{step}`")
    lines.extend(["", "Reject next route if:", ""])
    for item in report["self_iteration_contract"]["reject_next_route_if"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Mathematical Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _ranked_lines(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["- none"]
    return [f"- `{row['name']}`: `{row['value']}`" for row in rows[:8]]


def _ranked_inline(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "`none`"
    return ", ".join(f"`{row['name']}={row['value']}`" for row in rows)


def _bucket_failure_text(failures: dict[str, Any]) -> str:
    if not failures:
        return "`none`"
    return ", ".join(f"`{name}={value}`" for name, value in failures.items())


def _ranked_positive(values: dict[str, Any]) -> list[dict[str, Any]]:
    return _ranked(values, predicate=lambda value: value > 0.0, key=lambda value: value)


def _ranked_negative(values: dict[str, Any]) -> list[dict[str, Any]]:
    return _ranked(values, predicate=lambda value: value < 0.0, key=lambda value: abs(value))


def _ranked_by_abs(values: dict[str, Any]) -> list[dict[str, Any]]:
    return _ranked(values, predicate=lambda _value: True, key=lambda value: abs(value))


def _ranked(
    values: dict[str, Any],
    *,
    predicate: Any,
    key: Any,
) -> list[dict[str, Any]]:
    rows = []
    for name, value in values.items():
        if value is None:
            continue
        numeric = float(value)
        if predicate(numeric):
            rows.append({"name": str(name), "value": numeric})
    rows.sort(key=lambda row: key(float(row["value"])), reverse=True)
    return rows


def _rows_by_bucket(rows: Any) -> dict[str, dict[str, Any]]:
    if isinstance(rows, dict):
        return {
            str(name): dict(row)
            for name, row in rows.items()
            if isinstance(row, dict)
        }
    result = {}
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            bucket = row.get("bucket")
            if bucket is not None:
                result[str(bucket)] = row
    return result


def _ordered_bucket_names(names: Iterable[str]) -> list[str]:
    order = (
        "overall",
        "normal",
        "traffic_light",
        "red_light_turn",
        "sharp_turn",
        "npc_interaction",
        "dense_scene",
        "lane_change_or_merge",
    )
    name_set = {str(name) for name in names}
    result = [name for name in order if name in name_set]
    result.extend(sorted(name for name in name_set if name not in result))
    return result


def _ci_high(entry: dict[str, Any], key: str) -> Any:
    return _get(entry, "run_level_delta_ci", key, "ci95_high")


def _cvar_ci_high(entry: dict[str, Any], key: str) -> Any:
    return _get(entry, "cvar90_run_level_delta_ci", key, "ci95_high")


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


def _get(data: Any, *path: str) -> Any:
    current = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


if __name__ == "__main__":
    main()
