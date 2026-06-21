#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np


SOURCE_STATUS = "offline_convex_objective_label_sensitivity_dry_run_complete"
SOURCE_NEXT_WORK = "diagnose_objective_label_sensitivity_results"

READY_STATUS = "offline_convex_objective_label_sensitivity_results_diagnosed"
BLOCKED_STATUS = "offline_convex_objective_label_sensitivity_results_diagnosis_blocked"
REDESIGN_NEXT_WORK = "predeclare_no_leak_atom_or_proof_objective_redesign_plan_only"
TARGETED_NEXT_WORK = "predeclare_targeted_objective_label_sensitivity_extension_plan_only"

PRIMARY_HARD_COMPONENTS = (
    "collision",
    "near_miss",
    "lane_violation",
    "realized_red_light",
    "red_light_violation",
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
            "Read-only diagnosis for a completed offline objective/label "
            "sensitivity wrapper. It reads linked training/eval/proof artifacts "
            "and decides whether the sensitivity route has any credible "
            "direction before new design work."
        )
    )
    parser.add_argument("--sensitivity_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        sensitivity=_load_json(args.sensitivity_json),
        label=args.label,
        paths={"sensitivity_json": str(args.sensitivity_json)},
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
    sensitivity: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source_checks = _source_checks(sensitivity)
    artifact_checks = _artifact_checks(sensitivity)
    variant_diagnostics = _variant_diagnostics(sensitivity)
    control = next(
        (row for row in variant_diagnostics if row["role"] == "control"),
        None,
    )
    candidate_diagnostics = [
        _attach_direction(row, control)
        for row in variant_diagnostics
        if row["role"] == "candidate"
    ]
    all_diagnostics = [
        row if row["role"] == "control" else next(
            item for item in candidate_diagnostics if item["name"] == row["name"]
        )
        for row in variant_diagnostics
    ]
    credible = [
        row["name"]
        for row in candidate_diagnostics
        if row["direction_vs_control"]["credible_direction"]
    ]
    passed = all(check["passed"] for check in [*source_checks, *artifact_checks])
    route_rejected = passed and not credible
    final = _final_decision(
        passed=passed,
        route_rejected=route_rejected,
        credible_candidates=credible,
    )
    return {
        "analysis": {
            "name": "dp_camp_offline_convex_objective_label_sensitivity_results_diagnosis_v1",
            "label": label,
            "role": (
                "read-only diagnosis of completed offline objective/label "
                "sensitivity variants"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "paths": paths or {},
            "math_boundary": (
                "This diagnosis reads only existing offline sensitivity "
                "artifacts. DP remains a fixed black-box candidate generator. "
                "Candidate atoms are fixed logged current-tick constants; CAMP "
                "scores remain affine score_k(w)=a_k^T w; simplex/CVaR/L2 "
                "training remains the convex object. Closed-loop outcomes are "
                "offline labels/evaluation targets only. No DP-side classical "
                "Benders construction is claimed."
            ),
        },
        "source_checks": source_checks,
        "artifact_checks": artifact_checks,
        "variant_diagnostics": all_diagnostics,
        "comparison_summary": _comparison_summary(candidate_diagnostics),
        "route_diagnosis": _route_diagnosis(
            route_rejected=route_rejected,
            credible_candidates=credible,
            candidate_diagnostics=candidate_diagnostics,
        ),
        "blocked_actions": {name: False for name in BLOCKED_ACTIONS},
        "final_decision": final,
    }


def _source_checks(sensitivity: dict[str, Any]) -> list[dict[str, Any]]:
    decision = sensitivity.get("final_decision") or {}
    summary = sensitivity.get("summary") or {}
    return [
        _check_equal("sensitivity_status_complete", decision.get("status"), SOURCE_STATUS),
        _check_equal("sensitivity_passed", decision.get("passed"), True),
        _check_equal(
            "sensitivity_authorizes_diagnosis",
            decision.get("authorized_next_work"),
            SOURCE_NEXT_WORK,
        ),
        _check_equal("no_accepted_variants", decision.get("accepted_variants") or [], []),
        _check_equal(
            "summary_has_no_accepted_variants",
            summary.get("accepted_for_next_review") or [],
            [],
        ),
        _check_equal(
            "all_variants_complete",
            summary.get("variants_complete"),
            summary.get("variants_total"),
        ),
        *_blocked_action_checks(decision, "sensitivity"),
    ]


def _artifact_checks(sensitivity: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    required = (
        "training_summary_json",
        "selector_eval_json",
        "camp_vs_top1_safety_cost_proof_json",
        "offline_weights_dp_static",
    )
    for variant in sensitivity.get("variants") or []:
        if not isinstance(variant, dict):
            continue
        name = str(variant.get("name"))
        artifacts = variant.get("artifacts") or {}
        for key in required:
            path = _artifact_path(artifacts, key)
            checks.append(
                {
                    "name": f"{name}_{key}_exists",
                    "passed": path is not None and path.is_file(),
                    "path": None if path is None else str(path),
                }
            )
    if not checks:
        checks.append(
            {
                "name": "variants_present",
                "passed": False,
                "reason": "sensitivity report has no variant entries",
            }
        )
    return checks


def _variant_diagnostics(sensitivity: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for variant in sensitivity.get("variants") or []:
        if not isinstance(variant, dict):
            continue
        rows.append(_variant_diagnostic(variant))
    return rows


def _variant_diagnostic(variant: dict[str, Any]) -> dict[str, Any]:
    artifacts = variant.get("artifacts") or {}
    training = _safe_json_artifact(artifacts, "training_summary_json")
    selector_eval = _safe_json_artifact(artifacts, "selector_eval_json")
    proof = _safe_json_artifact(artifacts, "camp_vs_top1_safety_cost_proof_json")
    weights_path = _artifact_path(artifacts, "offline_weights_dp_static")
    weights = _top_weights(training, weights_path)
    comparison = selector_eval.get("selector_comparison") or {}
    weighted_delta = comparison.get("weighted_component_delta_mean") or {}
    proof_gates = proof.get("gates") or {}
    top1_gate = proof_gates.get("safety_cost_trained_selector_vs_top1") or {}
    gap_gate = proof_gates.get("safety_cost_trained_selector_gap_closed") or {}
    acceptance = variant.get("acceptance_gate") or {}
    failed_checks = [
        check.get("name")
        for check in acceptance.get("checks") or []
        if isinstance(check, dict) and check.get("passed") is not True
    ]
    return {
        "name": str(variant.get("name")),
        "role": str(variant.get("role")),
        "accepted_for_next_review": bool(variant.get("accepted_for_next_review")),
        "status": variant.get("status"),
        "parameters": variant.get("parameters") or {},
        "failed_acceptance_checks": failed_checks,
        "training": {
            "converged": training.get("converged"),
            "final_master_gap": training.get("final_master_gap"),
            "train": training.get("train") or training.get("train_metrics") or {},
            "val": training.get("val") or training.get("val_metrics") or {},
            "top_weights": weights,
        },
        "selector_regression": {
            "changed_record_rate": comparison.get("changed_record_rate"),
            "evaluated_minus_logged_cost_mean": comparison.get(
                "evaluated_minus_logged_cost_mean"
            ),
            "evaluated_minus_logged_ci_high": _get(
                comparison,
                "run_level_evaluated_minus_logged_cost_ci",
                "ci95_high",
            ),
            "positive_hard_component_deltas": _positive_hard_components(weighted_delta),
            "weighted_component_delta_mean": {
                key: weighted_delta.get(key)
                for key in (
                    "collision",
                    "near_miss",
                    "lane_violation",
                    "realized_red_light",
                    "red_light_violation",
                    "route_shortfall",
                    "mean_jerk",
                    "mean_lateral_acceleration",
                )
                if key in weighted_delta
            },
        },
        "proof": {
            "top1_gate_passed": top1_gate.get("passed"),
            "top1_overall_ci_high": top1_gate.get("overall_ci_high"),
            "top1_bucket_failures": top1_gate.get("bucket_failures") or {},
            "oracle_gap_gate_passed": gap_gate.get("passed"),
            "oracle_gap_overall_ci_high": gap_gate.get("overall_ci_high"),
            "oracle_gap_bucket_failures": gap_gate.get("bucket_failures") or {},
        },
    }


def _attach_direction(row: dict[str, Any], control: dict[str, Any] | None) -> dict[str, Any]:
    if control is None:
        row["direction_vs_control"] = {
            "credible_direction": False,
            "reason": "missing_control_variant",
        }
        return row
    c_sel = control["selector_regression"]
    r_sel = row["selector_regression"]
    c_proof = control["proof"]
    r_proof = row["proof"]
    deltas = {
        "evaluated_minus_logged_ci_high": _delta(
            r_sel.get("evaluated_minus_logged_ci_high"),
            c_sel.get("evaluated_minus_logged_ci_high"),
        ),
        "collision": _delta(
            _component_value(r_sel, "collision"),
            _component_value(c_sel, "collision"),
        ),
        "near_miss": _delta(
            _component_value(r_sel, "near_miss"),
            _component_value(c_sel, "near_miss"),
        ),
        "top1_bucket_failure_count": (
            len(r_proof["top1_bucket_failures"])
            - len(c_proof["top1_bucket_failures"])
        ),
        "oracle_gap_bucket_failure_count": (
            len(r_proof["oracle_gap_bucket_failures"])
            - len(c_proof["oracle_gap_bucket_failures"])
        ),
    }
    nonworse = all(value is not None and value <= 0.0 for value in deltas.values())
    strict_improvement = any(value is not None and value < 0.0 for value in deltas.values())
    row["direction_vs_control"] = {
        "credible_direction": bool(nonworse and strict_improvement),
        "deltas": deltas,
        "reason": (
            "nonworse_with_strict_primary_improvement"
            if nonworse and strict_improvement
            else "no_nonworse_primary_direction"
        ),
    }
    return row


def _comparison_summary(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "candidate_count": len(candidates),
        "credible_direction_candidates": [
            row["name"]
            for row in candidates
            if row.get("direction_vs_control", {}).get("credible_direction")
        ],
        "best_by_logged_nonworse_ci_high": _best_candidate(
            candidates,
            ("selector_regression", "evaluated_minus_logged_ci_high"),
        ),
        "best_by_collision_delta": _best_candidate(
            candidates,
            ("selector_regression", "weighted_component_delta_mean", "collision"),
        ),
        "best_by_near_miss_delta": _best_candidate(
            candidates,
            ("selector_regression", "weighted_component_delta_mean", "near_miss"),
        ),
        "top1_failure_counts": {
            row["name"]: len(row["proof"]["top1_bucket_failures"])
            for row in candidates
        },
        "oracle_gap_failure_counts": {
            row["name"]: len(row["proof"]["oracle_gap_bucket_failures"])
            for row in candidates
        },
    }


def _route_diagnosis(
    *,
    route_rejected: bool,
    credible_candidates: list[str],
    candidate_diagnostics: list[dict[str, Any]],
) -> dict[str, Any]:
    persistent_failures = sorted(
        {
            failure
            for row in candidate_diagnostics
            for failure in row["failed_acceptance_checks"]
        }
    )
    return {
        "sensitivity_route_rejected": route_rejected,
        "credible_direction_candidates": credible_candidates,
        "persistent_failed_checks": persistent_failures,
        "diagnosis": (
            "reject_objective_label_sensitivity_route"
            if route_rejected
            else "targeted_sensitivity_extension_possible"
        ),
        "interpretation": (
            "No predeclared objective knob variant reduced the primary logged "
            "selector regression, hard component regression, and bucket-proof "
            "failures in a nonworse direction."
            if route_rejected
            else "At least one candidate moved all primary failure measures in "
            "a nonworse direction; review before any new experiment."
        ),
    }


def _final_decision(
    *,
    passed: bool,
    route_rejected: bool,
    credible_candidates: list[str],
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else BLOCKED_STATUS,
        "passed": passed,
        "sensitivity_route_rejected": route_rejected if passed else None,
        "credible_direction_candidates": credible_candidates,
        "authorized_next_work": (
            None
            if not passed
            else (REDESIGN_NEXT_WORK if route_rejected else TARGETED_NEXT_WORK)
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
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    route = report["route_diagnosis"]
    lines = [
        "# Offline Objective/Label Sensitivity Results Diagnosis",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- sensitivity route rejected: `{decision['sensitivity_route_rejected']}`",
        f"- credible direction candidates: `{', '.join(decision['credible_direction_candidates']) or 'none'}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        f"- closed-loop replay authorized: `{decision['closed_loop_replay_authorized']}`",
        f"- formal seeds authorized: `{decision['formal_seeds_authorized']}`",
        "",
        "## Route Diagnosis",
        "",
        f"- diagnosis: `{route['diagnosis']}`",
        f"- interpretation: {route['interpretation']}",
        f"- persistent failed checks: `{', '.join(route['persistent_failed_checks'])}`",
        "",
        "## Variants",
        "",
        "| Variant | Role | Accepted | Logged CI High | Collision | Near Miss | Top-1 Failures | Gap Failures | Credible Direction |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in report["variant_diagnostics"]:
        direction = row.get("direction_vs_control", {})
        lines.append(
            f"| `{row['name']}` | `{row['role']}` | `{row['accepted_for_next_review']}` | "
            f"`{row['selector_regression']['evaluated_minus_logged_ci_high']}` | "
            f"`{_component_value(row['selector_regression'], 'collision')}` | "
            f"`{_component_value(row['selector_regression'], 'near_miss')}` | "
            f"`{len(row['proof']['top1_bucket_failures'])}` | "
            f"`{len(row['proof']['oracle_gap_bucket_failures'])}` | "
            f"`{direction.get('credible_direction')}` |"
        )
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


def _safe_json_artifact(artifacts: dict[str, Any], key: str) -> dict[str, Any]:
    path = _artifact_path(artifacts, key)
    if path is None or not path.is_file():
        return {}
    return _load_json(path)


def _artifact_path(artifacts: dict[str, Any], key: str) -> Path | None:
    entry = artifacts.get(key)
    if not isinstance(entry, dict) or not entry.get("path"):
        return None
    return Path(str(entry["path"]))


def _top_weights(
    training_summary: dict[str, Any],
    weights_path: Path | None,
    *,
    limit: int = 8,
) -> list[dict[str, Any]]:
    if weights_path is None or not weights_path.is_file():
        return []
    weights = np.asarray(np.load(weights_path), dtype=np.float64)
    atom_names = training_summary.get("atom_names")
    if not isinstance(atom_names, list):
        atom_names = _get(training_summary, "atom_scales", "atom_names")
    if not isinstance(atom_names, list):
        atom_names = [f"atom_{idx}" for idx in range(weights.size)]
    rows = []
    for idx, value in enumerate(weights.tolist()):
        if abs(float(value)) <= 1e-12:
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


def _positive_hard_components(values: dict[str, Any]) -> dict[str, float]:
    result = {}
    for name in PRIMARY_HARD_COMPONENTS:
        value = values.get(name)
        if value is not None and float(value) > 0.0:
            result[name] = float(value)
    return result


def _component_value(selector: dict[str, Any], name: str) -> float | None:
    values = selector.get("weighted_component_delta_mean") or {}
    value = values.get(name)
    return None if value is None else float(value)


def _delta(value: Any, baseline: Any) -> float | None:
    if value is None or baseline is None:
        return None
    return float(value) - float(baseline)


def _best_candidate(candidates: list[dict[str, Any]], path: tuple[str, ...]) -> dict[str, Any] | None:
    best: tuple[float, dict[str, Any]] | None = None
    for row in candidates:
        value = _get(row, *path)
        if value is None:
            continue
        numeric = float(value)
        if best is None or numeric < best[0]:
            best = (numeric, row)
    if best is None:
        return None
    return {"name": best[1]["name"], "value": best[0]}


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


def _get(data: Any, *path: str) -> Any:
    current = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


if __name__ == "__main__":
    main()
