#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np


SMOKE_RESULT_READY_STATUS = "candidate_set_consensus_payload_smoke_result_ready"
SMOKE_RESULT_NEXT_WORK = (
    "candidate_set_consensus_payload_tiny_smoke_materiality_diagnosis_only"
)
READY_STATUS = "candidate_set_consensus_tiny_materiality_diagnosis_ready"
REJECT_STATUS = "candidate_set_consensus_tiny_materiality_diagnosis_rejected"
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_broader_nonformal_materiality_plan_only"
)
PAYLOAD_KEY = "candidate_set_consensus_payload_logging"
COEFFICIENT_KEY = "candidate_set_consensus_center_rms_m"
RANK_KEY = "candidate_set_consensus_center_rms_rank"
MIN_RECORDS_FOR_PROMOTION = 12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnose tiny-smoke materiality for the candidate-set consensus "
            "payload. This consumes real smoke logs but does not use closed-loop "
            "outcomes, run replay, train CAMP, or change selection."
        )
    )
    parser.add_argument("--selection_log", type=Path, required=True)
    parser.add_argument("--smoke_result_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--require_pass", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        selection_log=args.selection_log,
        smoke_result=_load_json(args.smoke_result_json),
        label=args.label,
        paths={
            "selection_log": str(args.selection_log),
            "smoke_result_json": str(args.smoke_result_json),
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
    if args.require_pass and not report["final_decision"]["passed"]:
        raise SystemExit(1)


def analyze(
    *,
    selection_log: Path,
    smoke_result: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    smoke = _smoke_summary(smoke_result)
    rows = _load_rows(selection_log)
    record_reports = [_record_report(row, index) for index, row in enumerate(rows)]
    summary = _summarize_records(record_reports)
    checks = [*_smoke_checks(smoke), *_record_checks(summary)]
    passed = all(check["passed"] for check in checks)
    failed_checks = [check["name"] for check in checks if not check["passed"]]
    signal_present = bool(
        summary["positive_spread_records"] > 0
        and summary["selected_not_consensus_best_records"] > 0
        and summary["finite_lambda_records"] > 0
    )
    materiality_gate_passed = bool(
        signal_present and summary["records"] >= MIN_RECORDS_FOR_PROMOTION
    )
    return {
        "analysis": {
            "name": "dp_camp_candidate_set_consensus_tiny_materiality_v1",
            "label": label,
            "paths": paths or {},
            "future_outcome_labels_used": False,
            "selection_effect": False,
            "training": False,
            "new_replay": False,
            "math_boundary": (
                "This diagnosis reads only the logged fixed current-tick "
                "candidate-set consensus coefficient, current feasible mask, "
                "selected index, and existing CAMP selection scores. It checks "
                "whether a nonnegative affine coefficient could change the "
                "finite-candidate argmin in principle, but it does not use "
                "closed-loop outcomes, claim safety benefit, train CAMP, or "
                "promote an atom. If later atomized, the coefficient is fixed "
                "before scoring and preserves score_k(w)=a_k^T w and the "
                "simplex/CVaR/L2 convex master in w."
            ),
        },
        "smoke_result_summary": smoke,
        "record_summary": summary,
        "record_reports": record_reports,
        "checks": checks,
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
            "failed_checks": failed_checks,
            "signal_present": signal_present,
            "materiality_gate_passed": materiality_gate_passed,
            "sample_too_small_for_promotion": summary["records"]
            < MIN_RECORDS_FOR_PROMOTION,
            "safety_benefit_evidence": False,
            "atom_promotion_authorized": False,
            "new_replay_authorized": False,
            "closed_loop_smoke_authorized": False,
            "closed_loop_replay_authorized": False,
            "formal_seeds_authorized": False,
            "full36_authorized": False,
            "online_selector_authorized": False,
            "camp_retraining_authorized": False,
            "training_execution_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["record_summary"]
    lines = [
        "# Candidate-Set Consensus Tiny Materiality Diagnosis",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Signal present: `{decision['signal_present']}`",
        f"- Materiality gate passed: `{decision['materiality_gate_passed']}`",
        f"- Sample too small for promotion: `{decision['sample_too_small_for_promotion']}`",
        f"- Atom promotion authorized: `{decision['atom_promotion_authorized']}`",
        f"- Safety benefit evidence: `{decision['safety_benefit_evidence']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Summary",
        "",
        f"- records: `{summary['records']}`",
        f"- available records: `{summary['available_records']}`",
        f"- positive spread records: `{summary['positive_spread_records']}`",
        f"- selected not consensus-best records: `{summary['selected_not_consensus_best_records']}`",
        f"- finite lambda records: `{summary['finite_lambda_records']}`",
        f"- selected rank mean: `{summary['selected_rank_mean']}`",
        f"- selected minus consensus-best cost mean: `{summary['selected_minus_best_cost_mean']}`",
        f"- minimum lambda to change any record: `{summary['min_lambda_to_change_any_record']}`",
        "",
        "## Checks",
        "",
        "| Check | Passed | Observed | Expected |",
        "| --- | ---: | --- | --- |",
    ]
    for check in report["checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _smoke_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(report.get("final_decision"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "safety_benefit_evidence": bool(decision.get("safety_benefit_evidence")),
        "atom_promotion_authorized": bool(decision.get("atom_promotion_authorized")),
        "new_replay_authorized": bool(decision.get("new_replay_authorized")),
    }


def _record_report(row: dict[str, Any], index: int) -> dict[str, Any]:
    payload = _dict(row.get(PAYLOAD_KEY))
    selected_index = int(row.get("selected_index", -1))
    feasible = np.asarray(row.get("feasible_mask") or [], dtype=bool)
    scores = np.asarray(row.get("selection_scores") or row.get("scores") or [], dtype=float)
    costs = np.asarray(payload.get(COEFFICIENT_KEY) or [], dtype=float)
    ranks = np.asarray(payload.get(RANK_KEY) or [], dtype=int)
    available = bool(payload.get("available"))
    valid = (
        available
        and feasible.ndim == 1
        and costs.shape == feasible.shape
        and ranks.shape == feasible.shape
        and scores.shape == feasible.shape
        and 0 <= selected_index < costs.size
        and bool(feasible[selected_index])
        and np.all(np.isfinite(costs))
        and np.all(np.isfinite(scores[feasible]))
    )
    if not valid:
        return {
            "record_index": index,
            "available": available,
            "valid": False,
            "selected_index": selected_index,
        }
    masked_costs = np.where(feasible, costs, np.inf)
    masked_scores = np.where(feasible, scores, np.inf)
    best_consensus_index = int(np.argmin(masked_costs))
    best_score_index = int(np.argmin(masked_scores))
    selected_cost = float(costs[selected_index])
    best_cost = float(costs[best_consensus_index])
    lower_cost_candidates: list[dict[str, Any]] = []
    for candidate_index in range(costs.size):
        if (
            candidate_index == selected_index
            or not bool(feasible[candidate_index])
            or costs[candidate_index] >= selected_cost
        ):
            continue
        score_gap = float(scores[candidate_index] - scores[selected_index])
        cost_gap = float(selected_cost - costs[candidate_index])
        if cost_gap <= 0.0:
            continue
        lower_cost_candidates.append(
            {
                "candidate_index": int(candidate_index),
                "score_gap_vs_selected": score_gap,
                "cost_gap_vs_selected": cost_gap,
                "lambda_to_tie": score_gap / cost_gap,
            }
        )
    finite_thresholds = [
        item["lambda_to_tie"]
        for item in lower_cost_candidates
        if np.isfinite(float(item["lambda_to_tie"])) and item["lambda_to_tie"] >= 0.0
    ]
    return {
        "record_index": index,
        "available": available,
        "valid": True,
        "selected_index": selected_index,
        "best_score_index": best_score_index,
        "best_consensus_index": best_consensus_index,
        "selected_consensus_rank": int(ranks[selected_index]),
        "best_consensus_rank": int(ranks[best_consensus_index]),
        "selected_consensus_cost": selected_cost,
        "best_consensus_cost": best_cost,
        "selected_minus_best_consensus_cost": float(selected_cost - best_cost),
        "consensus_cost_spread": float(np.max(costs[feasible]) - np.min(costs[feasible])),
        "lower_consensus_cost_candidate_count": len(lower_cost_candidates),
        "min_nonnegative_lambda_to_change": (
            float(min(finite_thresholds)) if finite_thresholds else None
        ),
    }


def _summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [record for record in records if record.get("valid")]
    ranks = [float(record["selected_consensus_rank"]) for record in valid]
    cost_gaps = [
        float(record["selected_minus_best_consensus_cost"]) for record in valid
    ]
    spreads = [float(record["consensus_cost_spread"]) for record in valid]
    lambdas = [
        float(record["min_nonnegative_lambda_to_change"])
        for record in valid
        if record.get("min_nonnegative_lambda_to_change") is not None
    ]
    return {
        "records": len(records),
        "available_records": sum(1 for record in records if record.get("available")),
        "valid_records": len(valid),
        "positive_spread_records": sum(1 for value in spreads if value > 1e-12),
        "selected_not_consensus_best_records": sum(
            1
            for record in valid
            if record["selected_index"] != record["best_consensus_index"]
        ),
        "finite_lambda_records": len(lambdas),
        "selected_rank_mean": _mean_or_none(ranks),
        "selected_rank_max": max(ranks) if ranks else None,
        "selected_minus_best_cost_mean": _mean_or_none(cost_gaps),
        "selected_minus_best_cost_max": max(cost_gaps) if cost_gaps else None,
        "cost_spread_mean": _mean_or_none(spreads),
        "min_lambda_to_change_any_record": min(lambdas) if lambdas else None,
        "min_lambda_to_change_mean": _mean_or_none(lambdas),
    }


def _smoke_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("smoke_result_status", summary["status"], SMOKE_RESULT_READY_STATUS),
        _check_equal("smoke_result_passed", summary["passed"], True),
        _check_equal(
            "smoke_result_authorizes_materiality",
            summary["authorized_next_work"],
            SMOKE_RESULT_NEXT_WORK,
        ),
        _check_equal(
            "smoke_result_no_safety_claim",
            summary["safety_benefit_evidence"],
            False,
        ),
        _check_equal(
            "smoke_result_no_atom_promotion",
            summary["atom_promotion_authorized"],
            False,
        ),
        _check_equal("smoke_result_no_new_replay", summary["new_replay_authorized"], False),
    ]


def _record_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("record_count_tiny_smoke", summary["records"], 3),
        _check_equal("all_records_available", summary["available_records"], 3),
        _check_equal("all_records_valid", summary["valid_records"], 3),
        _check_gte("positive_spread_records", summary["positive_spread_records"], 1),
        _check_gte(
            "selected_not_consensus_best_records",
            summary["selected_not_consensus_best_records"],
            1,
        ),
        _check_gte("finite_lambda_records", summary["finite_lambda_records"], 1),
    ]


def _load_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a JSON list.")
    return [row if isinstance(row, dict) else {} for row in payload]


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _mean_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return float(np.mean(np.asarray(values, dtype=float)))


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


def _check_gte(name: str, observed: Any, expected: float) -> dict[str, Any]:
    try:
        value = float(observed)
    except (TypeError, ValueError):
        value = float("-inf")
    return {
        "name": name,
        "observed": observed,
        "expected": f">= {expected}",
        "passed": value >= expected,
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


if __name__ == "__main__":
    main()
