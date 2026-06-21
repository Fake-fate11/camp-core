#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


SOURCE_READY_STATUS = "temporal_consistency_broader_nonformal_smoke_result_ready"
SOURCE_READY_NEXT_WORK = (
    "temporal_consistency_materiality_diagnosis_existing_broader_smoke_only"
)
READY_STATUS = "temporal_consistency_materiality_diagnosis_ready"
REJECT_STATUS = "temporal_consistency_materiality_diagnosis_rejected"
AUTHORIZED_NEXT_WORK = "temporal_consistency_atom_schema_preflight_only"
RECORD_KEY = "temporal_consistency_payload_logging"
COEFFICIENT_KEY = "previous_plan_temporal_consistency_rms_m"
FORMAL_SEEDS = frozenset({11, 12, 13})

MIN_AVAILABLE_RECORDS = 40
MIN_NONZERO_RANGE_RECORDS = 40
MIN_LOWER_FEASIBLE_RECORDS = 20
MIN_MEAN_FEASIBLE_GAP_M = 0.02

BLOCKED_ACTIONS = (
    "training_execution_authorized",
    "camp_retraining_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
    "atom_promotion_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only materiality diagnosis for temporal-consistency payload "
            "coefficients in an existing broader nonformal smoke."
        )
    )
    parser.add_argument("--smoke_result_json", type=Path, required=True)
    parser.add_argument("--logging_root", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        smoke_result=_load_json(args.smoke_result_json),
        logging_root=args.logging_root,
        label=args.label,
        paths={
            "smoke_result_json": str(args.smoke_result_json),
            "logging_root": str(args.logging_root),
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
    smoke_result: dict[str, Any],
    logging_root: Path,
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source = _source_summary(smoke_result)
    rows = _load_materiality_rows(logging_root)
    materiality = _materiality_summary(rows)
    checks = [
        *_source_checks(source),
        *_row_contract_checks(materiality),
        *_materiality_checks(materiality),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_temporal_consistency_materiality_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "diffusion_planner_execution": False,
            "future_outcome_labels_used": False,
            "paths": paths or {},
            "math_boundary": (
                "This diagnosis reads existing logging-enabled selection logs "
                "only. It uses current-tick candidate coefficients, selected_index, "
                "and feasible_mask to test whether the temporal-consistency "
                "coefficient varies across fixed DP candidates and whether lower "
                "base-feasible alternatives exist. It reads no future outcomes. "
                "The coefficient is finite and nonnegative when available, so a "
                "future atom would enter as fixed a_k in score_k(w)=a_k^T w and "
                "would preserve the simplex/CVaR/L2 convex master. This is not a "
                "DP-side classical Benders proof and does not prove safety benefit."
            ),
        },
        "source_summary": source,
        "materiality_summary": materiality,
        "result_checks": checks,
        "example_rows": rows[:5],
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks, materiality),
    }


def _source_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "coverage_ready_for_materiality_diagnosis": bool(
            decision.get("coverage_ready_for_materiality_diagnosis")
        ),
        "safety_benefit_evidence": bool(decision.get("safety_benefit_evidence")),
        "atom_promotion_authorized": bool(decision.get("atom_promotion_authorized")),
        "blocked_action_conflicts": conflicts,
    }


def _load_materiality_rows(logging_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(logging_root.rglob("camp_selection_log.json")):
        formal = _formal_seed_in_path(path)
        records = _load_json(path)
        run_id = path.parent.name
        for tick_index, record in enumerate(records):
            payload = record.get(RECORD_KEY) or {}
            if not payload.get("available"):
                continue
            values = payload.get(COEFFICIENT_KEY) or []
            selected_index = _as_int(record.get("selected_index"))
            feasible_mask = record.get("feasible_mask")
            row = _materiality_row(
                run_id=run_id,
                tick_index=tick_index,
                path=path,
                formal_seed=formal,
                record=record,
                values=values,
                selected_index=selected_index,
                feasible_mask=feasible_mask,
            )
            rows.append(row)
    return rows


def _materiality_row(
    *,
    run_id: str,
    tick_index: int,
    path: Path,
    formal_seed: int | None,
    record: dict[str, Any],
    values: Any,
    selected_index: int | None,
    feasible_mask: Any,
) -> dict[str, Any]:
    errors: list[str] = []
    vector = _float_vector(values)
    if not vector:
        errors.append("coefficient_vector_missing_or_invalid")
    if selected_index is None or selected_index < 0 or selected_index >= len(vector):
        errors.append("selected_index_invalid")
    if formal_seed is not None:
        errors.append(f"formal_seed_detected={formal_seed}")
    payload = record.get(RECORD_KEY) or {}
    for key in (
        "selection_effect",
        "future_outcome_leakage",
        "closed_loop_outcome_fields_read",
        "online_selector_change",
        "deployed_atom_vector_change",
        "classical_benders_claim",
    ):
        if bool(payload.get(key)):
            errors.append(f"{key}_must_be_false")
    if record.get("candidate_closed_loop_outcomes") is not None:
        errors.append("candidate_closed_loop_outcomes_present")
    if any((not math.isfinite(value)) or value < 0.0 for value in vector):
        errors.append("coefficient_nonfinite_or_negative")

    feasible = _feasible_indices(feasible_mask, len(vector))
    selected_value = vector[selected_index] if selected_index is not None and selected_index < len(vector) else math.nan
    global_min = min(vector) if vector else math.nan
    global_max = max(vector) if vector else math.nan
    feasible_values = [vector[index] for index in feasible]
    feasible_min = min(feasible_values) if feasible_values else math.nan
    global_gap = selected_value - global_min if math.isfinite(selected_value) else math.nan
    feasible_gap = selected_value - feasible_min if math.isfinite(selected_value) and math.isfinite(feasible_min) else math.nan
    value_range = global_max - global_min if math.isfinite(global_max) and math.isfinite(global_min) else math.nan
    return {
        "run_id": run_id,
        "tick_index": tick_index,
        "path": str(path),
        "selected_index": selected_index,
        "selected_value": selected_value,
        "global_min": global_min,
        "feasible_min": feasible_min,
        "global_gap": global_gap,
        "feasible_gap": feasible_gap,
        "value_range": value_range,
        "feasible_count": len(feasible),
        "lower_global_candidate_exists": bool(math.isfinite(global_gap) and global_gap > 1e-9),
        "lower_feasible_candidate_exists": bool(
            math.isfinite(feasible_gap) and feasible_gap > 1e-9
        ),
        "errors": errors,
    }


def _materiality_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid_rows = [row for row in rows if not row["errors"]]
    feasible_gaps = [
        row["feasible_gap"]
        for row in valid_rows
        if math.isfinite(row["feasible_gap"])
    ]
    global_gaps = [
        row["global_gap"] for row in valid_rows if math.isfinite(row["global_gap"])
    ]
    ranges = [row["value_range"] for row in valid_rows if math.isfinite(row["value_range"])]
    by_run: dict[str, dict[str, Any]] = {}
    for row in valid_rows:
        stats = by_run.setdefault(
            row["run_id"],
            {"records": 0, "lower_feasible_records": 0, "nonzero_range_records": 0},
        )
        stats["records"] += 1
        stats["lower_feasible_records"] += int(row["lower_feasible_candidate_exists"])
        stats["nonzero_range_records"] += int(row["value_range"] > 1e-9)
    return {
        "available_records": len(rows),
        "valid_records": len(valid_rows),
        "invalid_records": len(rows) - len(valid_rows),
        "invalid_errors": _error_counts(rows),
        "nonzero_range_records": sum(1 for value in ranges if value > 1e-9),
        "lower_global_candidate_records": sum(
            1 for row in valid_rows if row["lower_global_candidate_exists"]
        ),
        "lower_feasible_candidate_records": sum(
            1 for row in valid_rows if row["lower_feasible_candidate_exists"]
        ),
        "mean_global_gap_m": _mean(global_gaps),
        "mean_feasible_gap_m": _mean(feasible_gaps),
        "max_global_gap_m": max(global_gaps) if global_gaps else math.nan,
        "max_feasible_gap_m": max(feasible_gaps) if feasible_gaps else math.nan,
        "mean_range_m": _mean(ranges),
        "by_run": by_run,
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status", source["status"], SOURCE_READY_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal(
            "source_authorizes_materiality",
            source["authorized_next_work"],
            SOURCE_READY_NEXT_WORK,
        ),
        _check_equal(
            "source_coverage_ready",
            source["coverage_ready_for_materiality_diagnosis"],
            True,
        ),
        _check_equal("source_safety_benefit_not_claimed", source["safety_benefit_evidence"], False),
        _check_equal(
            "source_atom_promotion_not_authorized",
            source["atom_promotion_authorized"],
            False,
        ),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
    ]


def _row_contract_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal(
            "available_record_count_material",
            summary["available_records"] >= MIN_AVAILABLE_RECORDS,
            True,
        ),
        _check_equal("invalid_records_zero", summary["invalid_records"], 0),
    ]


def _materiality_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal(
            "nonzero_range_material",
            summary["nonzero_range_records"] >= MIN_NONZERO_RANGE_RECORDS,
            True,
        ),
        _check_equal(
            "lower_feasible_alternatives_material",
            summary["lower_feasible_candidate_records"] >= MIN_LOWER_FEASIBLE_RECORDS,
            True,
        ),
        _check_equal(
            "mean_feasible_gap_material",
            summary["mean_feasible_gap_m"] >= MIN_MEAN_FEASIBLE_GAP_M,
            True,
        ),
    ]


def _final_decision(
    passed: bool,
    checks: list[dict[str, Any]],
    materiality: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "source_materiality_evidence": passed,
        "safety_benefit_evidence": False,
        "atom_schema_preflight_authorized": passed,
        "atom_promotion_authorized": False,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "next_step": (
            "Design a schema-only atom preflight for the temporal-consistency "
            "coefficient. Do not train CAMP, promote online selection, run "
            "Full36, use formal seeds, or claim safety benefit."
            if passed
            else "Reject temporal consistency as a material atom source for this smoke."
        ),
        "available_records": materiality["available_records"],
        "lower_feasible_candidate_records": materiality[
            "lower_feasible_candidate_records"
        ],
        "mean_feasible_gap_m": materiality["mean_feasible_gap_m"],
        **{key: False for key in BLOCKED_ACTIONS},
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Temporal Consistency Materiality Diagnosis",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Safety benefit evidence: `{decision['safety_benefit_evidence']}`",
        f"- Atom schema preflight authorized: `{decision['atom_schema_preflight_authorized']}`",
        f"- Atom promotion authorized: `{decision['atom_promotion_authorized']}`",
        "",
        "## Summaries",
        "",
        f"- Source: `{report['source_summary']}`",
        f"- Materiality: `{report['materiality_summary']}`",
        "",
        "## Mathematical Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "## Checks",
        "",
        "| Check | Passed | Observed | Expected |",
        "| --- | ---: | --- | --- |",
    ]
    for check in report["result_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _formal_seed_in_path(path: Path) -> int | None:
    parts = {part.lower() for part in path.parts}
    for seed in FORMAL_SEEDS:
        if f"seed_{seed}" in parts or f"seed{seed}" in parts:
            return seed
    return None


def _float_vector(values: Any) -> list[float]:
    if not isinstance(values, list):
        return []
    result: list[float] = []
    for value in values:
        try:
            result.append(float(value))
        except (TypeError, ValueError):
            return []
    return result


def _feasible_indices(mask: Any, size: int) -> list[int]:
    if isinstance(mask, list) and len(mask) == size:
        return [index for index, value in enumerate(mask) if bool(value)]
    return list(range(size))


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _error_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        for error in row["errors"]:
            counts[error] = counts.get(error, 0) + 1
    return counts


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else math.nan


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
