#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


SOURCE_READY_STATUS = "temporal_consistency_shadow_atom_dry_run_ready"
SOURCE_READY_NEXT_WORK = "temporal_consistency_shadow_weight_sensitivity_existing_smoke_only"
READY_STATUS = "temporal_consistency_shadow_weight_sensitivity_ready"
REJECT_STATUS = "temporal_consistency_shadow_weight_sensitivity_rejected"
AUTHORIZED_NEXT_WORK = "temporal_consistency_shadow_safety_proxy_existing_smoke_only"

LOG_NAME = "camp_selection_log.json"
PAYLOAD_KEY = "temporal_consistency_payload_logging"
COEFFICIENT_KEY = "previous_plan_temporal_consistency_rms_m"
DEFAULT_WEIGHT_GRID = (0.0, 0.01, 0.05, 0.1, 0.2, 0.5, 1.0)
SCORE_TOLERANCE = 1e-9

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
            "Existing-smoke shadow weight sensitivity for the temporal-consistency "
            "atom. This reads logs only and does not deploy or train CAMP."
        )
    )
    parser.add_argument("--shadow_dry_run_json", type=Path, required=True)
    parser.add_argument("--candidate_root", type=Path, required=True)
    parser.add_argument("--expected_logs", type=int, required=True)
    parser.add_argument("--expected_records", type=int, required=True)
    parser.add_argument("--expected_candidates", type=int, required=True)
    parser.add_argument("--expected_available_records", type=int, required=True)
    parser.add_argument(
        "--shadow_weight",
        type=float,
        action="append",
        default=None,
        help="Shadow weight grid entry. May be repeated; defaults to a fixed grid.",
    )
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--require_pass", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        shadow_dry_run=_load_json(args.shadow_dry_run_json),
        candidate_root=args.candidate_root,
        expected_logs=args.expected_logs,
        expected_records=args.expected_records,
        expected_candidates=args.expected_candidates,
        expected_available_records=args.expected_available_records,
        weight_grid=tuple(args.shadow_weight or DEFAULT_WEIGHT_GRID),
        label=args.label,
        paths={
            "shadow_dry_run_json": str(args.shadow_dry_run_json),
            "candidate_root": str(args.candidate_root),
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
    shadow_dry_run: dict[str, Any],
    candidate_root: Path,
    expected_logs: int,
    expected_records: int,
    expected_candidates: int,
    expected_available_records: int,
    weight_grid: tuple[float, ...] = DEFAULT_WEIGHT_GRID,
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    weights = _validated_weight_grid(weight_grid)
    source = _source_summary(shadow_dry_run)
    logs = _load_selection_logs(candidate_root)
    records = [
        _sensitivity_record(
            record=record,
            run_id=run_id,
            record_index=record_index,
            global_index=global_index,
            expected_candidates=expected_candidates,
            weight_grid=weights,
        )
        for global_index, (run_id, record_index, record) in enumerate(_iter_records(logs))
    ]
    summary = _summary(records, logs, weights)
    checks = [
        *_source_checks(source),
        *_record_count_checks(
            summary,
            expected_logs=expected_logs,
            expected_records=expected_records,
            expected_available_records=expected_available_records,
        ),
        *_sensitivity_checks(summary),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_temporal_consistency_shadow_weight_sensitivity_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used": False,
            "paths": paths or {},
            "math_boundary": (
                "This sensitivity scan reuses existing logs and applies fixed "
                "shadow weights to the already validated temporal-consistency "
                "coefficient. For each finite candidate it evaluates "
                "score'_k = selection_score_k + lambda * a_temporal,k. The "
                "coefficient is fixed before scoring, so the expression remains "
                "affine in weights. The scan is diagnostic only: no online "
                "selector, training, DP execution, safety claim, or classical "
                "Benders decomposition is introduced."
            ),
        },
        "source_summary": source,
        "weight_grid": list(weights),
        "sensitivity_records": records,
        "sensitivity_summary": summary,
        "sensitivity_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks, summary),
    }


def _source_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    summary = report.get("dry_run_summary") or {}
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "shadow_atom_dry_run_ready": bool(decision.get("shadow_atom_dry_run_ready")),
        "safety_benefit_evidence": bool(decision.get("safety_benefit_evidence")),
        "atom_promotion_authorized": bool(decision.get("atom_promotion_authorized")),
        "blocked_action_conflicts": conflicts,
        "records": int(summary.get("records", -1)),
        "available_records": int(summary.get("available_records", -1)),
        "ranking_signal_records": int(summary.get("ranking_signal_records", -1)),
        "max_shadow_zero_weight_score_abs_diff": float(
            decision.get("max_shadow_zero_weight_score_abs_diff", math.inf)
        ),
    }


def _sensitivity_record(
    *,
    record: dict[str, Any],
    run_id: str,
    record_index: int,
    global_index: int,
    expected_candidates: int,
    weight_grid: tuple[float, ...],
) -> dict[str, Any]:
    payload = record.get(PAYLOAD_KEY)
    if not isinstance(payload, dict) or not payload.get("available"):
        return {
            "run_id": run_id,
            "record_index": record_index,
            "global_index": global_index,
            "available": False,
            "passed": True,
            "errors": [],
            "weight_results": [],
        }
    errors: list[str] = []
    selected_index = _optional_int(record.get("selected_index"))
    feasible_mask = _bool_vector(record.get("feasible_mask"), expected_candidates)
    selection_scores = _score_vector(record.get("selection_scores"))
    coeff = _float_vector(payload.get(COEFFICIENT_KEY))
    if selected_index is None or selected_index < 0 or selected_index >= expected_candidates:
        errors.append("selected_index_invalid")
    if len(selection_scores) != expected_candidates:
        errors.append("selection_scores_shape_mismatch")
    if len(coeff) != expected_candidates:
        errors.append("temporal_coefficient_shape_mismatch")
    if any((not math.isfinite(value)) or value < 0.0 for value in coeff):
        errors.append("temporal_coefficient_nonfinite_or_negative")
    candidate_domain = _candidate_domain(selection_scores, feasible_mask)
    if selected_index is not None and selected_index not in candidate_domain:
        errors.append("selected_index_not_in_candidate_domain")
    weight_results = []
    for weight in weight_grid:
        shadow_scores = _shadow_scores(selection_scores, coeff, weight, candidate_domain)
        shadow_selected = _argmin(shadow_scores, candidate_domain)
        changed = (
            selected_index is not None
            and shadow_selected is not None
            and shadow_selected != selected_index
        )
        selected_coeff = coeff[selected_index] if selected_index is not None and selected_index < len(coeff) else math.nan
        shadow_coeff = coeff[shadow_selected] if shadow_selected is not None else math.nan
        weight_results.append(
            {
                "weight": weight,
                "shadow_selected_index": shadow_selected,
                "changed_selected_index": changed,
                "selected_temporal_coeff": selected_coeff,
                "shadow_selected_temporal_coeff": shadow_coeff,
                "temporal_coeff_delta": (
                    shadow_coeff - selected_coeff
                    if math.isfinite(shadow_coeff) and math.isfinite(selected_coeff)
                    else math.nan
                ),
            }
        )
    critical_weight = _critical_positive_weight(
        selected_index=selected_index,
        selection_scores=selection_scores,
        coeff=coeff,
        candidate_domain=candidate_domain,
    )
    return {
        "run_id": run_id,
        "record_index": record_index,
        "global_index": global_index,
        "available": True,
        "selected_index": selected_index,
        "candidate_domain": candidate_domain,
        "critical_positive_weight": critical_weight,
        "weight_results": weight_results,
        "passed": not errors,
        "errors": errors,
    }


def _summary(
    records: list[dict[str, Any]],
    logs: list[tuple[str, list[dict[str, Any]]]],
    weights: tuple[float, ...],
) -> dict[str, Any]:
    available = [record for record in records if record.get("available") is True]
    valid_available = [record for record in available if record.get("passed") is True]
    by_weight = []
    for weight in weights:
        changed = []
        coeff_deltas = []
        for record in valid_available:
            result = next(
                item for item in record["weight_results"] if item["weight"] == weight
            )
            if result["changed_selected_index"]:
                changed.append(record)
                delta = result["temporal_coeff_delta"]
                if math.isfinite(delta):
                    coeff_deltas.append(delta)
        by_weight.append(
            {
                "weight": weight,
                "changed_records": len(changed),
                "changed_fraction": (
                    len(changed) / len(valid_available) if valid_available else 0.0
                ),
                "mean_temporal_coeff_delta_on_changed": _mean(coeff_deltas),
                "changed_global_indices": [record["global_index"] for record in changed],
            }
        )
    critical = [
        record["critical_positive_weight"]
        for record in valid_available
        if math.isfinite(record["critical_positive_weight"])
    ]
    zero_weight_rows = [item for item in by_weight if item["weight"] == 0.0]
    return {
        "log_count": len(logs),
        "records": len(records),
        "available_records": len(available),
        "valid_available_records": len(valid_available),
        "invalid_available_records": len(available) - len(valid_available),
        "record_error_counts": _error_counts(records),
        "weights": list(weights),
        "by_weight": by_weight,
        "zero_weight_changed_records": (
            zero_weight_rows[0]["changed_records"] if zero_weight_rows else None
        ),
        "positive_weight_any_change": any(
            item["weight"] > 0.0 and item["changed_records"] > 0 for item in by_weight
        ),
        "min_critical_positive_weight": min(critical) if critical else math.inf,
        "median_critical_positive_weight": _median(critical),
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status", source["status"], SOURCE_READY_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal(
            "source_authorizes_weight_sensitivity",
            source["authorized_next_work"],
            SOURCE_READY_NEXT_WORK,
        ),
        _check_equal(
            "source_shadow_dry_run_ready",
            source["shadow_atom_dry_run_ready"],
            True,
        ),
        _check_equal("source_safety_benefit_not_claimed", source["safety_benefit_evidence"], False),
        _check_equal(
            "source_atom_promotion_not_authorized",
            source["atom_promotion_authorized"],
            False,
        ),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
        _check_equal(
            "source_zero_weight_diff_tiny",
            source["max_shadow_zero_weight_score_abs_diff"] <= SCORE_TOLERANCE,
            True,
        ),
    ]


def _record_count_checks(
    summary: dict[str, Any],
    *,
    expected_logs: int,
    expected_records: int,
    expected_available_records: int,
) -> list[dict[str, Any]]:
    return [
        _check_equal("log_count", summary["log_count"], expected_logs),
        _check_equal("record_count", summary["records"], expected_records),
        _check_equal(
            "available_record_count",
            summary["available_records"],
            expected_available_records,
        ),
        _check_equal("invalid_available_records_zero", summary["invalid_available_records"], 0),
        _check_equal("record_errors_empty", summary["record_error_counts"], {}),
    ]


def _sensitivity_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("grid_contains_zero", 0.0 in summary["weights"], True),
        _check_equal("grid_contains_positive", any(w > 0.0 for w in summary["weights"]), True),
        _check_equal("zero_weight_preserves_selection", summary["zero_weight_changed_records"], 0),
        _check_equal(
            "positive_weight_has_shadow_effect",
            summary["positive_weight_any_change"],
            True,
        ),
    ]


def _final_decision(
    passed: bool,
    checks: list[dict[str, Any]],
    summary: dict[str, Any],
) -> dict[str, Any]:
    max_changed = max(
        (item["changed_records"] for item in summary["by_weight"]),
        default=0,
    )
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "safety_benefit_evidence": False,
        "atom_promotion_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_replay_authorized": False,
        "max_changed_records": max_changed,
        "min_critical_positive_weight": summary["min_critical_positive_weight"],
        "median_critical_positive_weight": summary["median_critical_positive_weight"],
        "next_step": (
            "Run an existing-smoke safety-proxy association for the shadow-selected "
            "candidates before considering any selector design. Keep it shadow-only."
            if passed
            else "Reject weight sensitivity and inspect source, records, or grid."
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["sensitivity_summary"]
    lines = [
        "# Temporal Consistency Shadow Weight Sensitivity",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Max changed records: `{decision['max_changed_records']}`",
        f"- Min critical positive weight: `{decision['min_critical_positive_weight']}`",
        f"- Safety benefit evidence: `{decision['safety_benefit_evidence']}`",
        "",
        "## Weight Grid",
        "",
        "| Weight | Changed Records | Changed Fraction | Mean Temporal Delta On Changed |",
        "| ---: | ---: | ---: | ---: |",
    ]
    for item in summary["by_weight"]:
        lines.append(
            f"| `{item['weight']}` | `{item['changed_records']}` | "
            f"`{item['changed_fraction']}` | "
            f"`{item['mean_temporal_coeff_delta_on_changed']}` |"
        )
    lines.extend(["", "## Mathematical Boundary", "", report["analysis"]["math_boundary"], ""])
    lines.extend(["## Checks", "", "| Check | Passed | Observed | Expected |", "| --- | ---: | --- | --- |"])
    for check in report["sensitivity_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _candidate_domain(selection_scores: list[float], feasible_mask: list[bool]) -> list[int]:
    finite = [index for index, value in enumerate(selection_scores) if math.isfinite(value)]
    if finite:
        return finite
    return [index for index, value in enumerate(feasible_mask) if value]


def _shadow_scores(
    base_scores: list[float],
    coeff: list[float],
    weight: float,
    domain: list[int],
) -> list[float]:
    result = [math.inf for _ in base_scores]
    for index in domain:
        result[index] = base_scores[index] + weight * coeff[index]
    return result


def _argmin(scores: list[float], domain: list[int]) -> int | None:
    if not domain:
        return None
    return min(domain, key=lambda index: (scores[index], index))


def _critical_positive_weight(
    *,
    selected_index: int | None,
    selection_scores: list[float],
    coeff: list[float],
    candidate_domain: list[int],
) -> float:
    if selected_index is None or selected_index >= len(coeff):
        return math.inf
    selected_score = selection_scores[selected_index]
    selected_coeff = coeff[selected_index]
    thresholds = []
    for index in candidate_domain:
        if index == selected_index:
            continue
        denom = selected_coeff - coeff[index]
        if denom <= 0.0:
            continue
        numerator = selection_scores[index] - selected_score
        threshold = numerator / denom
        if threshold > 0.0 and math.isfinite(threshold):
            thresholds.append(threshold)
    return min(thresholds) if thresholds else math.inf


def _validated_weight_grid(values: tuple[float, ...]) -> tuple[float, ...]:
    parsed = sorted({float(value) for value in values})
    if not parsed:
        raise ValueError("weight grid must not be empty.")
    if any((not math.isfinite(value)) or value < 0.0 for value in parsed):
        raise ValueError("shadow weights must be finite and nonnegative.")
    return tuple(parsed)


def _load_selection_logs(root: Path) -> list[tuple[str, list[dict[str, Any]]]]:
    paths = sorted(root.rglob(LOG_NAME))
    result = []
    for path in paths:
        payload = _load_json(path)
        if not isinstance(payload, list):
            raise ValueError(f"{path} must contain a JSON list.")
        result.append((path.parent.name, [row for row in payload if isinstance(row, dict)]))
    return result


def _iter_records(
    logs: list[tuple[str, list[dict[str, Any]]]],
) -> list[tuple[str, int, dict[str, Any]]]:
    rows: list[tuple[str, int, dict[str, Any]]] = []
    for run_id, records in logs:
        rows.extend((run_id, index, record) for index, record in enumerate(records))
    return rows


def _score_vector(value: Any) -> list[float]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        try:
            result.append(float(item))
        except (TypeError, ValueError):
            return []
    return result


def _float_vector(value: Any) -> list[float]:
    return _score_vector(value)


def _bool_vector(value: Any, expected_candidates: int) -> list[bool]:
    if isinstance(value, list):
        return [bool(item) for item in value]
    return [True for _ in range(expected_candidates)]


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else math.nan


def _median(values: list[float]) -> float:
    if not values:
        return math.inf
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return 0.5 * (ordered[mid - 1] + ordered[mid])


def _error_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        for error in record.get("errors") or []:
            counts[error] = counts.get(error, 0) + 1
    return counts


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
