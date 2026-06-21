#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any


LOG_NAME = "camp_selection_log.json"
SUMMARY_NAME = "camp_validation_summary.json"
PAYLOAD_KEY = "observable_state_logging"
SUMMARY_KEY = "camp_observable_state_logging"
SCHEMA_VERSION = "dp_camp_observable_state_logging_v1"
PLAN_READY_STATUS = "observable_interaction_coverage_broader_nonformal_plan_ready"
PLAN_NEXT_WORK = "observable_interaction_coverage_broader_nonformal_paired_smoke_only"
PASS_STATUS = "observable_interaction_coverage_broader_nonformal_smoke_passed"
REJECT_STATUS = "observable_interaction_coverage_broader_nonformal_smoke_rejected"
NEXT_WORK_SEPARABILITY = "observable_interaction_descriptor_separability_on_covered_logs_only"
NEXT_WORK_REJECT = "reject_observable_interaction_coverage_or_predeclare_smaller_inventory"
FORMAL_SEEDS = frozenset({11, 12, 13})
LATENCY_KEYS = (
    "latency_ms_observable_state_route_topology",
    "latency_ms_observable_state_traffic_light_relation",
    "latency_ms_observable_state_route_turn",
    "latency_ms_observable_state_neighbor_clearance",
)
EQUIVALENCE_KEYS = (
    "selected_index",
    "camp_selected_index_before_tracker_postselection",
    "camp_selected_index_before_traffic_light_hybrid_postselection",
    "used_fallback",
    "camp_fallback_mode",
    "feasible_mask",
    "infeasibility_reasons",
    "scores",
    "weights",
    "selection_scores",
    "selection_weights",
    "atoms",
    "normalized_atoms",
    "selection_normalized_atoms",
    "atom_schema_version",
    "atom_names",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit the predeclared paired nonformal observable-interaction "
            "coverage smoke. This reads only current-tick logging payloads and "
            "selector-neutrality fields; it does not use closed-loop outcome "
            "labels."
        )
    )
    parser.add_argument("--plan_json", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--require_pass", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    plan = _read_json(args.plan_json)
    report = analyze(plan=plan, root=args.root)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    if args.require_pass and not report["final_decision"]["passed"]:
        raise SystemExit(2)


def analyze(*, plan: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    source_checks = _source_checks(plan)
    spec = plan.get("plan_spec") if isinstance(plan.get("plan_spec"), dict) else {}
    runs = [run for run in spec.get("runs", []) if isinstance(run, dict)]
    smoke_root = Path(root or spec.get("root") or ".")
    expected_records = int(spec.get("steps") or 0)
    expected_candidates = int(spec.get("num_candidates") or 0)
    budgets = {
        "red_distance_budget_m": _float(spec.get("red_distance_budget_m"), 5.0),
        "clearance_budget_m": _float(spec.get("clearance_budget_m"), 2.0),
        "lateral_error_budget_m": _float(spec.get("lateral_error_budget_m"), 0.5),
    }
    min_targets = {
        "red_context": int(spec.get("min_red_context_records") or 1),
        "clearance_context": int(spec.get("min_clearance_context_records") or 1),
        "turn_lateral_context": int(
            spec.get("min_turn_lateral_context_records") or 1
        ),
    }

    errors: list[str] = []
    warnings: list[str] = []
    run_reports: list[dict[str, Any]] = []
    payload_contexts: list[dict[str, Any]] = []
    equivalence_mismatches = 0
    baseline_payload_records = 0
    candidate_payload_records = 0
    total_records = 0
    max_latency_ms = {key: 0.0 for key in LATENCY_KEYS}

    if expected_records <= 0:
        errors.append("plan_spec.steps must be positive")
    if expected_candidates <= 0:
        errors.append("plan_spec.num_candidates must be positive")
    if not runs:
        errors.append("plan_spec.runs is empty")

    for run in runs:
        run_id = str(run.get("run_id") or "")
        if not run_id:
            errors.append("plan run missing run_id")
            continue
        if int(run.get("seed") or -1) in FORMAL_SEEDS:
            errors.append(f"{run_id}: formal_seed={run.get('seed')}")
        baseline_path = smoke_root / "logs" / run_id / "baseline" / LOG_NAME
        candidate_path = smoke_root / "logs" / run_id / "observable_logging" / LOG_NAME
        run_report = {
            "run_id": run_id,
            "baseline_log": str(baseline_path),
            "candidate_log": str(candidate_path),
            "records": 0,
            "candidate_payload_records": 0,
            "equivalence_mismatches": 0,
            "target_context_families": list(run.get("target_context_families") or []),
        }
        run_reports.append(run_report)
        for path in (baseline_path, candidate_path):
            forbidden = sorted(seed for seed in _path_seeds(path) if seed in FORMAL_SEEDS)
            if forbidden:
                errors.append(f"{run_id}: formal_seed_in_path={forbidden}")
        if not baseline_path.exists():
            errors.append(f"{run_id}: missing baseline log {baseline_path}")
            continue
        if not candidate_path.exists():
            errors.append(f"{run_id}: missing candidate log {candidate_path}")
            continue

        baseline_rows = _read_json(baseline_path)
        candidate_rows = _read_json(candidate_path)
        if not isinstance(baseline_rows, list) or not isinstance(candidate_rows, list):
            errors.append(f"{run_id}: selection logs must be JSON lists")
            continue
        if len(baseline_rows) != len(candidate_rows):
            errors.append(
                f"{run_id}: record_count_mismatch={len(baseline_rows)}!={len(candidate_rows)}"
            )
            continue
        if len(candidate_rows) != expected_records:
            errors.append(
                f"{run_id}: record_count={len(candidate_rows)} expected={expected_records}"
            )
        run_report["records"] = len(candidate_rows)
        total_records += len(candidate_rows)

        _validate_summary(
            _load_summary_for_log(baseline_path, errors),
            key=run_id,
            expected_enabled=False,
            errors=errors,
        )
        _validate_summary(
            _load_summary_for_log(candidate_path, errors),
            key=run_id,
            expected_enabled=True,
            errors=errors,
        )

        for index, (baseline, candidate) in enumerate(zip(baseline_rows, candidate_rows)):
            if not isinstance(baseline, dict) or not isinstance(candidate, dict):
                errors.append(f"{run_id} record {index}: rows must be objects")
                continue
            baseline_payload = baseline.get(PAYLOAD_KEY)
            candidate_payload = candidate.get(PAYLOAD_KEY)
            if baseline_payload is not None:
                baseline_payload_records += 1
                errors.append(f"{run_id} record {index}: baseline payload is not disabled")
            if (
                "candidate_closed_loop_outcomes" in candidate
                and candidate.get("candidate_closed_loop_outcomes") is not None
            ):
                errors.append(
                    f"{run_id} record {index}: candidate_closed_loop_outcomes present"
                )

            mismatches = _equivalence_mismatches(
                baseline,
                candidate,
                key=f"{run_id} record {index}",
            )
            if mismatches:
                equivalence_mismatches += len(mismatches)
                run_report["equivalence_mismatches"] += len(mismatches)
                errors.extend(mismatches[:5])

            if candidate_payload is None:
                errors.append(f"{run_id} record {index}: candidate payload missing")
                continue
            candidate_payload_records += 1
            run_report["candidate_payload_records"] += 1
            _validate_payload(
                candidate_payload,
                record=candidate,
                key=run_id,
                record_index=index,
                expected_candidates=expected_candidates,
                errors=errors,
            )
            for latency_key, latency in _latencies(candidate_payload).items():
                if latency < 0.0 or not math.isfinite(latency):
                    errors.append(
                        f"{run_id} record {index}: invalid latency {latency_key}={latency}"
                    )
                max_latency_ms[latency_key] = max(max_latency_ms[latency_key], latency)
            payload_contexts.append(
                _payload_context(
                    candidate_payload,
                    label=f"{run_id} record {index}",
                    run_id=run_id,
                    target_context_families=tuple(
                        str(item) for item in run.get("target_context_families") or ()
                    ),
                    red_distance_budget_m=budgets["red_distance_budget_m"],
                    clearance_budget_m=budgets["clearance_budget_m"],
                    lateral_error_budget_m=budgets["lateral_error_budget_m"],
                )
            )

    coverage = _coverage_metrics(payload_contexts)
    coverage_by_run = {
        run_id: _coverage_metrics(
            [item for item in payload_contexts if item["run_id"] == run_id]
        )
        for run_id in sorted({item["run_id"] for item in payload_contexts})
    }
    materiality = {
        "red_context": (
            coverage["records_with_red_risk_candidate_variation"]
            >= min_targets["red_context"]
        ),
        "clearance_context": (
            coverage["records_with_clearance_deficit_candidate_variation"]
            >= min_targets["clearance_context"]
        ),
        "turn_lateral_context": (
            coverage["records_with_turn_signal_candidate_variation"]
            >= min_targets["turn_lateral_context"]
            and coverage["records_with_lateral_excess_candidate_variation"]
            >= min_targets["turn_lateral_context"]
        ),
    }
    if coverage["normal_control_records"] <= 0:
        errors.append("normal_control_records=0")
    if coverage["normal_control_red_risk_nonzero_records"] > 0:
        errors.append(
            "normal_control_red_risk_nonzero_records="
            f"{coverage['normal_control_red_risk_nonzero_records']}"
        )
    if coverage["normal_control_clearance_deficit_nonzero_records"] > 0:
        errors.append(
            "normal_control_clearance_deficit_nonzero_records="
            f"{coverage['normal_control_clearance_deficit_nonzero_records']}"
        )
    for family, passed in materiality.items():
        if not passed:
            errors.append(f"{family}_materiality_not_reached")
    if candidate_payload_records != total_records:
        errors.append(
            f"candidate_payload_records={candidate_payload_records} total_records={total_records}"
        )

    passed = all(check["passed"] for check in source_checks) and not errors
    return {
        "analysis": {
            "name": "dp_camp_observable_interaction_coverage_smoke_v1",
            "root": str(smoke_root),
            "training": False,
            "diffusion_planner_modification": False,
            "online_selector_change": False,
            "future_outcome_labels_used": False,
            "closed_loop_outcome_labels_allowed": False,
            "formal_seeds_forbidden": sorted(FORMAL_SEEDS),
            "math_boundary": (
                "This audit checks default-off current-tick observable payloads "
                "and selector neutrality only. It creates no atom, no selector, "
                "and no Benders cut. If later atomized, payload-derived "
                "coefficients must remain fixed before scoring so "
                "score_k(w)=a_k^T w stays affine."
            ),
        },
        "source_checks": source_checks,
        "counts": {
            "planned_logs": len(runs),
            "paired_logs": len(
                [
                    row
                    for row in run_reports
                    if Path(row["baseline_log"]).exists()
                    and Path(row["candidate_log"]).exists()
                ]
            ),
            "records": total_records,
            "baseline_payload_records": baseline_payload_records,
            "candidate_payload_records": candidate_payload_records,
            "equivalence_mismatches": equivalence_mismatches,
        },
        "latency_ms": max_latency_ms,
        "coverage": coverage,
        "coverage_by_run": coverage_by_run,
        "materiality": materiality,
        "runs": run_reports,
        "warnings": warnings,
        "errors": errors,
        "final_decision": {
            "status": PASS_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "authorized_next_work": NEXT_WORK_SEPARABILITY if passed else NEXT_WORK_REJECT,
            "offline_separability_authorized": passed,
            "new_replay_authorized": False,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "online_selector_authorized": False,
            "CAMP_retraining_authorized": False,
            "DP_modification_authorized": False,
            "classic_Benders_claim_authorized": False,
        },
    }


def _source_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    final = plan.get("final_decision") if isinstance(plan, dict) else None
    final = final if isinstance(final, dict) else {}
    return [
        {
            "name": "source_plan_ready",
            "passed": final.get("status") == PLAN_READY_STATUS
            and final.get("passed") is True
            and final.get("authorized_next_work") == PLAN_NEXT_WORK,
            "final_decision": final,
        },
        {
            "name": "source_plan_blocks_larger_work",
            "passed": final.get("Full36_authorized") is False
            and final.get("formal_seeds_authorized") is False
            and final.get("online_selector_authorized") is False
            and final.get("CAMP_retraining_authorized") is False
            and final.get("DP_modification_authorized") is False,
        },
    ]


def _validate_summary(
    summary: dict[str, Any] | None,
    *,
    key: str,
    expected_enabled: bool,
    errors: list[str],
) -> None:
    if summary is None:
        return
    payload = summary.get(SUMMARY_KEY)
    if not isinstance(payload, dict):
        errors.append(f"{key}: missing {SUMMARY_KEY} in validation summary")
        return
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{key}: unexpected summary schema={payload.get('schema_version')}")
    if payload.get("enabled") is not expected_enabled:
        errors.append(
            f"{key}: summary enabled={payload.get('enabled')} expected={expected_enabled}"
        )
    if payload.get("default_off") is not True:
        errors.append(f"{key}: summary default_off is not true")
    if payload.get("selection_effect") is not False:
        errors.append(f"{key}: summary selection_effect is not false")
    if payload.get("future_outcome_leakage") is not False:
        errors.append(f"{key}: summary future_outcome_leakage is not false")
    logged_records = int(
        payload.get("logged_records")
        if payload.get("logged_records") is not None
        else payload.get("records") or 0
    )
    if expected_enabled and logged_records <= 0:
        errors.append(f"{key}: summary logged_records={logged_records}")
    if not expected_enabled and logged_records != 0:
        errors.append(f"{key}: disabled summary logged_records={logged_records}")


def _validate_payload(
    payload: dict[str, Any],
    *,
    record: dict[str, Any],
    key: str,
    record_index: int,
    expected_candidates: int,
    errors: list[str],
) -> None:
    prefix = f"{key} record {record_index}"
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{prefix}: unexpected schema={payload.get('schema_version')}")
    for field, expected in (
        ("enabled", True),
        ("default_off", True),
        ("selection_effect", False),
        ("future_outcome_leakage", False),
    ):
        if payload.get(field) is not expected:
            errors.append(f"{prefix}: payload {field}={payload.get(field)}")
    if int(payload.get("candidate_count") or -1) != expected_candidates:
        errors.append(
            f"{prefix}: payload candidate_count={payload.get('candidate_count')} "
            f"expected={expected_candidates}"
        )
    if int(record.get("num_candidates") or -1) != expected_candidates:
        errors.append(
            f"{prefix}: record num_candidates={record.get('num_candidates')} "
            f"expected={expected_candidates}"
        )
    finite_checks = payload.get("finite_checks")
    if not isinstance(finite_checks, dict):
        errors.append(f"{prefix}: missing finite_checks")
    else:
        failed = sorted(key for key, value in finite_checks.items() if value is not True)
        if failed:
            errors.append(f"{prefix}: finite_checks_failed={failed}")


def _equivalence_mismatches(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    key: str,
) -> list[str]:
    mismatches: list[str] = []
    for field in EQUIVALENCE_KEYS:
        if not _same_value(baseline.get(field), candidate.get(field)):
            mismatches.append(f"{key}: equivalence_mismatch={field}")
    return mismatches


def _same_value(left: Any, right: Any, *, atol: float = 1e-8) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=atol)
    if isinstance(left, str) or isinstance(right, str) or left is None or right is None:
        return left == right
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            _same_value(a, b, atol=atol) for a, b in zip(left, right)
        )
    if isinstance(left, dict) and isinstance(right, dict):
        return set(left) == set(right) and all(
            _same_value(left[name], right[name], atol=atol) for name in left
        )
    return left == right


def _payload_context(
    payload: dict[str, Any],
    *,
    label: str,
    run_id: str,
    target_context_families: tuple[str, ...],
    red_distance_budget_m: float,
    clearance_budget_m: float,
    lateral_error_budget_m: float,
) -> dict[str, Any]:
    candidate_count = int(payload.get("candidate_count") or 0)
    red_distance = _nan_to(
        _payload_vector(
            payload,
            "candidate_red_stopline_distance_m",
            candidate_count,
            label,
            none_value=math.inf,
        ),
        math.inf,
    )
    red_alignment = _nan_to(
        _payload_vector(
            payload,
            "candidate_red_heading_alignment",
            candidate_count,
            label,
            none_value=0.0,
        ),
        0.0,
    )
    clearance = _nan_to(
        _payload_vector(
            payload,
            "candidate_min_obstacle_clearance_lower_bound_m",
            candidate_count,
            label,
        ),
        math.inf,
    )
    heading = [abs(value) for value in _nan_to(
        _payload_vector(
            payload,
            "candidate_route_heading_change_rad",
            candidate_count,
            label,
        ),
        0.0,
    )]
    lateral = [abs(value) for value in _nan_to(
        _payload_vector(
            payload,
            "candidate_route_lateral_error_m",
            candidate_count,
            label,
        ),
        0.0,
    )]
    projection = _nan_to(
        _payload_vector(
            payload,
            "candidate_route_projection_s_m",
            candidate_count,
            label,
        ),
        0.0,
    )
    red_risk = [
        max(alignment, 0.0) * max(float(red_distance_budget_m) - distance, 0.0)
        for alignment, distance in zip(red_alignment, red_distance)
    ]
    clearance_deficit = [
        max(float(clearance_budget_m) - value, 0.0) for value in clearance
    ]
    lateral_excess = [
        max(value - float(lateral_error_budget_m), 0.0) for value in lateral
    ]
    return {
        "run_id": run_id,
        "target_context_families": list(target_context_families),
        "red_distance_present": payload.get("candidate_red_stopline_distance_m")
        is not None,
        "red_distance": red_distance,
        "red_alignment": red_alignment,
        "red_risk": red_risk,
        "clearance": clearance,
        "clearance_deficit": clearance_deficit,
        "heading_abs": heading,
        "lateral_abs": lateral,
        "lateral_excess": lateral_excess,
        "projection": projection,
    }


def _coverage_metrics(contexts: list[dict[str, Any]]) -> dict[str, Any]:
    normal = [
        item
        for item in contexts
        if "normal_control" in set(item.get("target_context_families") or [])
    ]
    return {
        "records": len(contexts),
        "normal_control_records": len(normal),
        "records_with_red_distance_payload": sum(
            int(item["red_distance_present"]) for item in contexts
        ),
        "records_with_red_risk_nonzero": _records_with_any_positive(
            contexts, "red_risk"
        ),
        "records_with_red_risk_candidate_variation": _records_with_variation(
            contexts, "red_risk"
        ),
        "records_with_clearance_deficit_nonzero": _records_with_any_positive(
            contexts, "clearance_deficit"
        ),
        "records_with_clearance_deficit_candidate_variation": _records_with_variation(
            contexts, "clearance_deficit"
        ),
        "records_with_turn_signal_nonzero": _records_with_any_positive(
            contexts, "heading_abs"
        ),
        "records_with_turn_signal_candidate_variation": _records_with_variation(
            contexts, "heading_abs"
        ),
        "records_with_lateral_excess_nonzero": _records_with_any_positive(
            contexts, "lateral_excess"
        ),
        "records_with_lateral_excess_candidate_variation": _records_with_variation(
            contexts, "lateral_excess"
        ),
        "records_with_projection_candidate_variation": _records_with_variation(
            contexts, "projection"
        ),
        "min_red_distance_m": _finite_min(contexts, "red_distance"),
        "max_red_alignment": _finite_max(contexts, "red_alignment"),
        "min_clearance_m": _finite_min(contexts, "clearance"),
        "max_lateral_excess_m": _finite_max(contexts, "lateral_excess"),
        "normal_control_red_risk_nonzero_records": _records_with_any_positive(
            normal, "red_risk"
        ),
        "normal_control_clearance_deficit_nonzero_records": (
            _records_with_any_positive(normal, "clearance_deficit")
        ),
    }


def _payload_vector(
    payload: dict[str, Any],
    field: str,
    candidate_count: int,
    label: str,
    *,
    none_value: float | None = None,
) -> list[float]:
    value = payload.get(field)
    if value is None and none_value is not None:
        return [float(none_value)] * candidate_count
    vector = _payload_scalar_vector(value, candidate_count, f"{label} {field}", field)
    if vector is None:
        return [math.nan] * candidate_count
    return vector


def _payload_scalar_vector(
    value: Any,
    candidate_count: int,
    label: str,
    source_field: str,
) -> list[float] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list or null.")
    if len(value) != candidate_count:
        raise ValueError(f"{label} length={len(value)} expected={candidate_count}.")
    if all(not isinstance(item, list) for item in value):
        return [_to_float(item) for item in value]
    rows = []
    for row in value:
        if not isinstance(row, list):
            raise ValueError(f"{label} must be uniformly vector or matrix-valued.")
        rows.append([_to_float(item) for item in row])
    finite_rows = [
        [item for item in row if math.isfinite(item)]
        for row in rows
    ]
    if source_field in {
        "candidate_route_projection_s_m",
        "candidate_route_segment_index",
    }:
        return [float(row[-1]) if row else math.nan for row in finite_rows]
    if source_field in {
        "candidate_route_lateral_error_m",
        "candidate_route_heading_change_rad",
    }:
        return [max((abs(item) for item in row), default=math.nan) for row in finite_rows]
    if source_field == "candidate_red_stopline_distance_m":
        return [min(row) if row else math.nan for row in finite_rows]
    if source_field == "candidate_red_heading_alignment":
        return [sum(row) / len(row) if row else math.nan for row in finite_rows]
    raise ValueError(f"{label} has unsupported matrix-valued source field.")


def _records_with_any_positive(contexts: list[dict[str, Any]], key: str) -> int:
    return sum(
        int(any(math.isfinite(value) and value > 1e-9 for value in item[key]))
        for item in contexts
    )


def _records_with_variation(contexts: list[dict[str, Any]], key: str) -> int:
    count = 0
    for item in contexts:
        values = [
            value for value in item[key] if math.isfinite(value)
        ]
        if values and max(values) - min(values) > 1e-9:
            count += 1
    return count


def _finite_min(contexts: list[dict[str, Any]], key: str) -> float | None:
    values = [
        value
        for item in contexts
        for value in item[key]
        if math.isfinite(value)
    ]
    return min(values) if values else None


def _finite_max(contexts: list[dict[str, Any]], key: str) -> float | None:
    values = [
        value
        for item in contexts
        for value in item[key]
        if math.isfinite(value)
    ]
    return max(values) if values else None


def _latencies(payload: dict[str, Any]) -> dict[str, float]:
    raw = payload.get("latency_ms")
    if not isinstance(raw, dict):
        return {key: math.nan for key in LATENCY_KEYS}
    return {key: _float(raw.get(key), math.nan) for key in LATENCY_KEYS}


def _nan_to(values: list[float], replacement: float) -> list[float]:
    return [
        value if math.isfinite(value) else float(replacement)
        for value in values
    ]


def _to_float(value: Any) -> float:
    if value is None:
        return math.nan
    return float(value)


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _path_seeds(path: Path) -> set[int]:
    return {
        int(match.group(1))
        for match in re.finditer(r"seed[_-]?(\d+)", str(path), flags=re.IGNORECASE)
    }


def _load_summary_for_log(log_path: Path, errors: list[str]) -> dict[str, Any] | None:
    path = log_path.parent / SUMMARY_NAME
    if not path.exists():
        errors.append(f"missing validation summary for {log_path}")
        return None
    summary = _read_json(path)
    if not isinstance(summary, dict):
        errors.append(f"{path} must contain a JSON object")
        return None
    return summary


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Observable Interaction Coverage Smoke Audit",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Counts",
        "",
        "```json",
        json.dumps(report["counts"], indent=2, sort_keys=True),
        "```",
        "",
        "## Coverage",
        "",
        "```json",
        json.dumps(report["coverage"], indent=2, sort_keys=True),
        "```",
        "",
        "## Materiality",
        "",
        "```json",
        json.dumps(report["materiality"], indent=2, sort_keys=True),
        "```",
        "",
        "## Errors",
        "",
    ]
    if report["errors"]:
        lines.extend(f"- {item}" for item in report["errors"])
    else:
        lines.append("- none")
    lines.extend(["", "## Mathematical Boundary", "", report["analysis"]["math_boundary"]])
    return "\n".join(lines)


if __name__ == "__main__":
    main()
