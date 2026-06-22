#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import numpy as np

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    BroaderMaterialitySpec,
    FORMAL_SEEDS,
    MAX_PAYLOAD_LATENCY_MS,
    MIN_POSITIVE_SPREAD_RATE,
    MIN_VALID_RECORD_RATE,
)


READY_STATUS = "candidate_set_consensus_broader_nonformal_materiality_diagnosis_ready"
INSUFFICIENT_STATUS = (
    "candidate_set_consensus_broader_nonformal_materiality_diagnosis_insufficient"
)
REJECT_STATUS = "candidate_set_consensus_broader_nonformal_materiality_diagnosis_rejected"
AUTHORIZED_NEXT_WORK = "candidate_set_consensus_atom_design_review_plan_only"
INSUFFICIENT_NEXT_WORK = (
    "candidate_set_consensus_broader_materiality_reject_or_redesign_review_only"
)

PAYLOAD_AUDIT_STATUS = "candidate_set_consensus_payload_smoke_audit_passed"
PAYLOAD_KEY = "candidate_set_consensus_payload_logging"
COEFFICIENT_KEY = "candidate_set_consensus_center_rms_m"
RANK_KEY = "candidate_set_consensus_center_rms_rank"

EXPECTED_LOGS = 6
EXPECTED_RECORDS = 60
EXPECTED_CANDIDATES = 8
EXPECTED_CANDIDATE_ROWS = 480
EPS = 1e-12

BLOCKED_ACTIONS = (
    "safety_benefit_evidence",
    "atom_promotion_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "formal_seeds_authorized",
    "full36_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "camp_retraining_authorized",
    "training_execution_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnose broader nonformal materiality for the default-off "
            "candidate-set consensus payload. This consumes completed replay "
            "artifacts only; it does not run DP, train CAMP, promote atoms, "
            "or change online selection."
        )
    )
    parser.add_argument("--replay_root", type=Path, required=True)
    parser.add_argument("--selector_equivalence_json", type=Path)
    parser.add_argument("--payload_audit_json", type=Path)
    parser.add_argument("--dataset_audit_json", type=Path)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--require_materiality", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selector_path = args.selector_equivalence_json or (
        args.replay_root / "audit" / "selector_equivalence.json"
    )
    payload_path = args.payload_audit_json or (
        args.replay_root / "audit" / "candidate_set_consensus_payload_audit.json"
    )
    dataset_path = args.dataset_audit_json or (
        args.replay_root / "audit" / "dataset_audit.json"
    )
    report = build_report(
        replay_root=args.replay_root,
        selector_equivalence=_load_json(selector_path),
        payload_audit=_load_json(payload_path),
        dataset_audit=_load_json(dataset_path),
        label=args.label,
        paths={
            "replay_root": str(args.replay_root),
            "selector_equivalence_json": str(selector_path),
            "payload_audit_json": str(payload_path),
            "dataset_audit_json": str(dataset_path),
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
    if args.require_materiality and not report["final_decision"]["materiality_gate_passed"]:
        raise SystemExit(1)


def build_report(
    *,
    replay_root: Path,
    selector_equivalence: dict[str, Any],
    payload_audit: dict[str, Any],
    dataset_audit: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    plan_spec = BroaderMaterialitySpec()
    expected_buckets = _expected_buckets(plan_spec)
    logs = _discover_logs(replay_root)
    records = _load_records(logs, expected_buckets)
    record_reports = [_record_report(record, index) for index, record in enumerate(records)]
    materiality = _materiality_summary(record_reports, expected_buckets)
    selector = _selector_summary(selector_equivalence)
    payload = _payload_summary(payload_audit)
    dataset = _dataset_summary(dataset_audit)
    precondition_checks = [
        *_selector_checks(selector),
        *_payload_checks(payload),
        *_dataset_checks(dataset),
        *_input_checks(logs, materiality),
    ]
    materiality_checks = _materiality_checks(materiality)
    checks = [*precondition_checks, *materiality_checks]
    decision = _final_decision(precondition_checks, materiality_checks, materiality)
    return {
        "analysis": {
            "name": "dp_camp_candidate_set_consensus_broader_materiality_v1",
            "label": label,
            "role": (
                "completed broader nonformal replay materiality diagnosis for "
                "candidate-set consensus payload"
            ),
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used": False,
            "formal_seed_records": int(len(materiality["formal_seed_run_ids"])),
            "paths": paths or {"replay_root": str(replay_root)},
            "math_boundary": (
                "This diagnosis reads only fixed current-tick candidate-set "
                "consensus payloads, feasible masks, selected indices, and "
                "existing CAMP selection scores from completed nonformal logs. "
                "It does not use closed-loop outcomes or safety scores to "
                "define an online feature. Passing materiality can only "
                "authorize a separate atom-design review plan. It does not "
                "authorize atom promotion, CAMP retraining, online selector "
                "changes, Full36, formal seeds, DP modification, or a DP-side "
                "classical Benders claim. Any later atom must preserve "
                "score_k(w)=a_k^T w and the simplex/CVaR/L2 convex master."
            ),
        },
        "selector_summary": selector,
        "payload_summary": payload,
        "dataset_summary": dataset,
        "input_summary": {
            "replay_root": str(replay_root),
            "selection_logs_found": [str(path) for path in logs],
        },
        "record_summary": materiality,
        "example_records": record_reports[:5],
        "checks": checks,
        "final_decision": decision,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["record_summary"]
    lines = [
        "# Candidate-Set Consensus Broader Nonformal Materiality Diagnosis",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Materiality gate passed: `{decision['materiality_gate_passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Signal present: `{decision['signal_present']}`",
        f"- Atom design review plan authorized: `{decision['atom_design_review_plan_authorized']}`",
        f"- Atom promotion authorized: `{decision['atom_promotion_authorized']}`",
        f"- Safety benefit evidence: `{decision['safety_benefit_evidence']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Replay Gates",
        "",
        f"- Selector equivalent: `{report['selector_summary']['equivalent']}`",
        f"- Payload audit passed: `{report['payload_summary']['passed']}`",
        f"- Dataset audit passed: `{report['dataset_summary']['passed']}`",
        f"- Payload latency max ms: `{report['payload_summary']['latency_max_ms']}`",
        "",
        "## Materiality Summary",
        "",
        f"- logs: `{summary['logs']}`",
        f"- records: `{summary['records']}`",
        f"- valid records: `{summary['valid_records']}`",
        f"- valid record rate: `{summary['valid_record_rate']}`",
        f"- candidate rows: `{summary['candidate_rows']}`",
        f"- positive spread records: `{summary['positive_spread_records']}`",
        f"- positive spread rate: `{summary['positive_spread_rate']}`",
        f"- selected not consensus-best records: `{summary['selected_not_consensus_best_records']}`",
        f"- finite lambda records: `{summary['finite_lambda_records']}`",
        f"- selected rank mean: `{summary['selected_rank_mean']}`",
        f"- selected rank max: `{summary['selected_rank_max']}`",
        f"- cost spread mean: `{summary['cost_spread_mean']}`",
        f"- cost spread max: `{summary['cost_spread_max']}`",
        f"- min lambda to change any record: `{summary['min_lambda_to_change_any_record']}`",
        "",
        "## Bucket Diagnostics",
        "",
        "| Bucket | Records | Valid | Positive spread | Selected not best | Finite lambda |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for bucket, bucket_summary in summary["bucket_summaries"].items():
        lines.append(
            f"| `{bucket}` | `{bucket_summary['records']}` | "
            f"`{bucket_summary['valid_records']}` | "
            f"`{bucket_summary['positive_spread_records']}` | "
            f"`{bucket_summary['selected_not_consensus_best_records']}` | "
            f"`{bucket_summary['finite_lambda_records']}` |"
        )
    lines.extend(
        [
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report["checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _discover_logs(replay_root: Path) -> list[Path]:
    root = replay_root / "logging_enabled"
    if not root.exists():
        return []
    return sorted(path for path in root.glob("*/camp_selection_log.json") if path.is_file())


def _load_records(
    logs: list[Path],
    expected_buckets: dict[str, tuple[str, ...]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in logs:
        run_id = path.parent.name
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            rows.append(
                {
                    "_path": str(path),
                    "_run_id": run_id,
                    "_buckets": expected_buckets.get(run_id, ()),
                    "_record_index": 0,
                    "_load_error": str(exc),
                }
            )
            continue
        records = payload if isinstance(payload, list) else []
        for index, record in enumerate(records):
            row = dict(record) if isinstance(record, dict) else {}
            row["_path"] = str(path)
            row["_run_id"] = run_id
            row["_buckets"] = expected_buckets.get(run_id, ())
            row["_record_index"] = index
            rows.append(row)
    return rows


def _record_report(record: dict[str, Any], ordinal: int) -> dict[str, Any]:
    run_id = str(record.get("_run_id") or "")
    payload = _dict(record.get(PAYLOAD_KEY))
    selected_index = int(record.get("selected_index", -1))
    feasible = np.asarray(record.get("feasible_mask") or [], dtype=bool)
    scores = np.asarray(record.get("selection_scores") or record.get("scores") or [], dtype=float)
    costs = np.asarray(payload.get(COEFFICIENT_KEY) or [], dtype=float)
    ranks = np.asarray(payload.get(RANK_KEY) or [], dtype=int)
    available = bool(payload.get("available"))
    if record.get("_load_error"):
        return _invalid_record(record, ordinal, available, "selection_log_load_error")
    valid = (
        available
        and feasible.ndim == 1
        and costs.shape == feasible.shape
        and ranks.shape == feasible.shape
        and scores.shape == feasible.shape
        and costs.size == EXPECTED_CANDIDATES
        and 0 <= selected_index < costs.size
        and bool(feasible[selected_index])
        and bool(payload.get("selection_effect") is False)
        and bool(payload.get("future_outcome_leakage") is False)
        and bool(payload.get("closed_loop_outcome_fields_read") is False)
        and bool(payload.get("classical_benders_claim") is False)
        and np.all(np.isfinite(costs))
        and np.all(costs >= -EPS)
        and np.all(np.isfinite(scores[feasible]))
    )
    if not valid:
        return _invalid_record(record, ordinal, available, "candidate_set_consensus_payload_invalid")
    masked_costs = np.where(feasible, costs, np.inf)
    masked_scores = np.where(feasible, scores, np.inf)
    best_consensus_index = int(np.argmin(masked_costs))
    best_score_index = int(np.argmin(masked_scores))
    selected_cost = float(costs[selected_index])
    best_cost = float(costs[best_consensus_index])
    lower_cost_candidates = []
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
        lower_cost_candidates.append(score_gap / cost_gap)
    lambdas = [
        float(value)
        for value in lower_cost_candidates
        if np.isfinite(float(value)) and float(value) >= 0.0
    ]
    return {
        "ordinal": ordinal,
        "path": str(record.get("_path") or ""),
        "run_id": run_id,
        "buckets": list(record.get("_buckets") or []),
        "record_index": int(record.get("_record_index") or 0),
        "available": available,
        "valid": True,
        "reason": "ok",
        "candidate_count": int(costs.size),
        "selected_index": selected_index,
        "best_score_index": best_score_index,
        "best_consensus_index": best_consensus_index,
        "selected_consensus_rank": int(ranks[selected_index]),
        "best_consensus_rank": int(ranks[best_consensus_index]),
        "selected_consensus_cost": selected_cost,
        "best_consensus_cost": best_cost,
        "selected_minus_best_consensus_cost": float(selected_cost - best_cost),
        "consensus_cost_spread": float(np.max(costs[feasible]) - np.min(costs[feasible])),
        "selected_not_consensus_best": selected_index != best_consensus_index,
        "finite_lambda_to_change": float(min(lambdas)) if lambdas else None,
    }


def _invalid_record(
    record: dict[str, Any],
    ordinal: int,
    available: bool,
    reason: str,
) -> dict[str, Any]:
    return {
        "ordinal": ordinal,
        "path": str(record.get("_path") or ""),
        "run_id": str(record.get("_run_id") or ""),
        "buckets": list(record.get("_buckets") or []),
        "record_index": int(record.get("_record_index") or 0),
        "available": available,
        "valid": False,
        "reason": reason,
    }


def _materiality_summary(
    records: list[dict[str, Any]],
    expected_buckets: dict[str, tuple[str, ...]],
) -> dict[str, Any]:
    valid = [row for row in records if row.get("valid")]
    spreads = [float(row["consensus_cost_spread"]) for row in valid]
    ranks = [float(row["selected_consensus_rank"]) for row in valid]
    lambdas = [
        float(row["finite_lambda_to_change"])
        for row in valid
        if row.get("finite_lambda_to_change") is not None
    ]
    positive = [row for row in valid if float(row["consensus_cost_spread"]) > EPS]
    selected_not_best = [row for row in valid if bool(row["selected_not_consensus_best"])]
    run_ids = sorted({str(row.get("run_id")) for row in records if row.get("run_id")})
    formal_run_ids = [
        run_id for run_id in run_ids if (_seed_from_run_id(run_id) in FORMAL_SEEDS)
    ]
    bucket_summaries = _bucket_summaries(records)
    bucket_spread_failures = [
        bucket
        for bucket in sorted({bucket for buckets in expected_buckets.values() for bucket in buckets})
        if bucket_summaries.get(bucket, {}).get("positive_spread_records", 0) <= 0
    ]
    valid_record_rate = _ratio(len(valid), len(records))
    positive_spread_rate = _ratio(len(positive), len(valid))
    candidate_rows = int(sum(int(row.get("candidate_count") or 0) for row in valid))
    signal_present = bool(
        len(positive) > 0 and len(selected_not_best) > 0 and len(lambdas) > 0
    )
    materiality_gate_passed = bool(
        len(records) >= EXPECTED_RECORDS
        and candidate_rows >= EXPECTED_CANDIDATE_ROWS
        and valid_record_rate >= MIN_VALID_RECORD_RATE
        and positive_spread_rate >= MIN_POSITIVE_SPREAD_RATE
        and signal_present
        and not bucket_spread_failures
        and not formal_run_ids
    )
    return {
        "logs": len(run_ids),
        "run_ids": run_ids,
        "formal_seed_run_ids": formal_run_ids,
        "records": len(records),
        "available_records": sum(1 for row in records if row.get("available")),
        "valid_records": len(valid),
        "valid_record_rate": valid_record_rate,
        "candidate_rows": candidate_rows,
        "positive_spread_records": len(positive),
        "positive_spread_rate": positive_spread_rate,
        "selected_not_consensus_best_records": len(selected_not_best),
        "finite_lambda_records": len(lambdas),
        "selected_rank_mean": _mean_or_none(ranks),
        "selected_rank_max": max(ranks) if ranks else None,
        "cost_spread_mean": _mean_or_none(spreads),
        "cost_spread_max": max(spreads) if spreads else None,
        "min_lambda_to_change_any_record": min(lambdas) if lambdas else None,
        "min_lambda_to_change_mean": _mean_or_none(lambdas),
        "bucket_summaries": bucket_summaries,
        "bucket_positive_spread_failures": bucket_spread_failures,
        "signal_present": signal_present,
        "sample_too_small_for_promotion": len(records) < EXPECTED_RECORDS,
        "materiality_gate_passed": materiality_gate_passed,
    }


def _bucket_summaries(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        for bucket in record.get("buckets") or []:
            buckets.setdefault(str(bucket), []).append(record)
    summaries = {}
    for bucket, rows in sorted(buckets.items()):
        valid = [row for row in rows if row.get("valid")]
        positive = [
            row for row in valid if float(row.get("consensus_cost_spread") or 0.0) > EPS
        ]
        selected_not_best = [
            row for row in valid if bool(row.get("selected_not_consensus_best"))
        ]
        lambdas = [row for row in valid if row.get("finite_lambda_to_change") is not None]
        summaries[bucket] = {
            "records": len(rows),
            "valid_records": len(valid),
            "positive_spread_records": len(positive),
            "selected_not_consensus_best_records": len(selected_not_best),
            "finite_lambda_records": len(lambdas),
        }
    return summaries


def _selector_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "equivalent": bool(report.get("equivalent")),
        "paired_logs": report.get("paired_logs"),
        "records": report.get("records"),
        "exact_mismatch_total": _sum_values(report.get("exact_field_mismatches")),
        "numeric_mismatch_total": _sum_values(report.get("numeric_field_mismatches")),
        "numeric_shape_mismatch_total": _sum_values(report.get("numeric_shape_mismatches")),
    }


def _payload_summary(report: dict[str, Any]) -> dict[str, Any]:
    final = _dict(report.get("final_decision"))
    counts = _dict(report.get("counts"))
    latency = _dict(report.get("latency_ms"))
    component = _dict(latency.get("latency_ms_candidate_set_consensus_payload"))
    return {
        "status": final.get("status"),
        "passed": bool(final.get("passed")),
        "errors": list(report.get("errors") or []),
        "baseline_logs": counts.get("baseline_logs"),
        "candidate_logs": counts.get("candidate_logs"),
        "records": counts.get("records"),
        "candidate_payload_records": counts.get("candidate_payload_records"),
        "available_payload_records": counts.get("available_payload_records"),
        "invalid_payload_records": counts.get("invalid_payload_records"),
        "latency_max_ms": component.get("max"),
        "latency_mean_ms": component.get("mean"),
    }


def _dataset_summary(report: dict[str, Any]) -> dict[str, Any]:
    counts = _dict(report.get("counts"))
    return {
        "passed": bool(report.get("passed")),
        "logs": counts.get("logs"),
        "records": counts.get("records"),
        "candidates": counts.get("candidates"),
        "errors": list(report.get("errors") or []),
    }


def _selector_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("selector_equivalent", summary["equivalent"], True),
        _check_equal("selector_paired_logs", summary["paired_logs"], EXPECTED_LOGS),
        _check_equal("selector_records", summary["records"], EXPECTED_RECORDS),
        _check_equal("selector_exact_mismatches_zero", summary["exact_mismatch_total"], 0),
        _check_equal("selector_numeric_mismatches_zero", summary["numeric_mismatch_total"], 0),
        _check_equal(
            "selector_numeric_shape_mismatches_zero",
            summary["numeric_shape_mismatch_total"],
            0,
        ),
    ]


def _payload_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("payload_status", summary["status"], PAYLOAD_AUDIT_STATUS),
        _check_equal("payload_passed", summary["passed"], True),
        _check_equal("payload_errors_empty", summary["errors"], []),
        _check_equal("payload_baseline_logs", summary["baseline_logs"], EXPECTED_LOGS),
        _check_equal("payload_candidate_logs", summary["candidate_logs"], EXPECTED_LOGS),
        _check_equal("payload_records", summary["records"], EXPECTED_RECORDS),
        _check_equal(
            "payload_candidate_payload_records",
            summary["candidate_payload_records"],
            EXPECTED_RECORDS,
        ),
        _check_equal(
            "payload_available_payload_records",
            summary["available_payload_records"],
            EXPECTED_RECORDS,
        ),
        _check_equal("payload_invalid_payload_records", summary["invalid_payload_records"], 0),
        _check_at_most(
            "payload_latency_max_ms",
            summary["latency_max_ms"],
            MAX_PAYLOAD_LATENCY_MS,
        ),
    ]


def _dataset_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("dataset_passed", summary["passed"], True),
        _check_equal("dataset_logs", summary["logs"], EXPECTED_LOGS),
        _check_equal("dataset_records", summary["records"], EXPECTED_RECORDS),
        _check_equal("dataset_candidates", summary["candidates"], EXPECTED_CANDIDATE_ROWS),
    ]


def _input_checks(logs: list[Path], materiality: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("input_selection_logs", len(logs), EXPECTED_LOGS),
        _check_equal("input_records", materiality["records"], EXPECTED_RECORDS),
        _check_equal("input_no_formal_seed_runs", materiality["formal_seed_run_ids"], []),
    ]


def _materiality_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_at_least("materiality_valid_record_rate", summary["valid_record_rate"], MIN_VALID_RECORD_RATE),
        _check_at_least(
            "materiality_positive_spread_rate",
            summary["positive_spread_rate"],
            MIN_POSITIVE_SPREAD_RATE,
        ),
        _check_at_least("materiality_candidate_rows", summary["candidate_rows"], EXPECTED_CANDIDATE_ROWS),
        _check_at_least("materiality_selected_not_best_records", summary["selected_not_consensus_best_records"], 1),
        _check_at_least("materiality_finite_lambda_records", summary["finite_lambda_records"], 1),
        _check_equal(
            "materiality_required_bucket_positive_spread",
            summary["bucket_positive_spread_failures"],
            [],
        ),
    ]


def _final_decision(
    precondition_checks: list[dict[str, Any]],
    materiality_checks: list[dict[str, Any]],
    materiality: dict[str, Any],
) -> dict[str, Any]:
    checks = [*precondition_checks, *materiality_checks]
    evidence_passed = all(check["passed"] for check in precondition_checks)
    materiality_checks_passed = all(check["passed"] for check in materiality_checks)
    materiality_gate_passed = bool(
        evidence_passed
        and materiality_checks_passed
        and materiality["materiality_gate_passed"]
    )
    if materiality_gate_passed:
        status = READY_STATUS
        authorized_next_work = AUTHORIZED_NEXT_WORK
    elif evidence_passed:
        status = INSUFFICIENT_STATUS
        authorized_next_work = INSUFFICIENT_NEXT_WORK
    else:
        status = REJECT_STATUS
        authorized_next_work = None
    return {
        "status": status,
        "passed": materiality_gate_passed,
        "screen_completed": evidence_passed,
        "materiality_gate_passed": materiality_gate_passed,
        "signal_present": bool(materiality["signal_present"]),
        "sample_too_small_for_promotion": bool(materiality["sample_too_small_for_promotion"]),
        "authorized_next_work": authorized_next_work,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "atom_design_review_plan_authorized": materiality_gate_passed,
        **{key: False for key in BLOCKED_ACTIONS},
    }


def _expected_buckets(spec: BroaderMaterialitySpec) -> dict[str, tuple[str, ...]]:
    return {run.run_id: tuple(run.scenario_buckets) for run in spec.runs}


def _seed_from_run_id(run_id: str) -> int | None:
    match = re.search(r"seed(\d+)", run_id)
    if match is None:
        return None
    return int(match.group(1))


def _sum_values(value: Any) -> int:
    if not isinstance(value, dict):
        return 0
    return int(sum(int(item or 0) for item in value.values()))


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


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


def _check_at_least(name: str, observed: Any, minimum: float) -> dict[str, Any]:
    try:
        value = float(observed)
    except (TypeError, ValueError):
        value = float("-inf")
    return {
        "name": name,
        "observed": observed,
        "expected": f">= {minimum}",
        "passed": value >= float(minimum),
    }


def _check_at_most(name: str, observed: Any, maximum: float) -> dict[str, Any]:
    try:
        value = float(observed)
    except (TypeError, ValueError):
        value = float("inf")
    return {
        "name": name,
        "observed": observed,
        "expected": f"<= {maximum}",
        "passed": value <= float(maximum),
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
