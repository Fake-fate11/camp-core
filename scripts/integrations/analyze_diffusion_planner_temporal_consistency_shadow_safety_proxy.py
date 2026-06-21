#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SOURCE_READY_STATUS = "temporal_consistency_shadow_weight_sensitivity_ready"
SOURCE_READY_NEXT_WORK = "temporal_consistency_shadow_safety_proxy_existing_smoke_only"
READY_STATUS = "temporal_consistency_shadow_safety_proxy_ready"
REJECT_STATUS = "temporal_consistency_shadow_safety_proxy_rejected"
SAFETY_EVIDENCE_NEXT_WORK = "temporal_consistency_selector_budget_preflight_only"
NO_EVIDENCE_NEXT_WORK = (
    "reject_temporal_consistency_as_safety_source_or_predeclare_alternative_no_leak_atom_only"
)

LOG_NAME = "camp_selection_log.json"
PAYLOAD_KEY = "temporal_consistency_payload_logging"
INDEX_TOLERANCE = 1e-12
DELTA_TOLERANCE = 1e-9
DEFAULT_MIN_EVIDENCE_CHANGED_RECORDS = 2
DEFAULT_REQUIRED_SAFETY_NONDEGRADING_FRACTION = 1.0

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
    "new_replay_authorized",
    "closed_loop_replay_authorized",
)


@dataclass(frozen=True)
class ProxySpec:
    name: str
    path: tuple[str, ...]
    family: str
    direction: str


PROXY_SPECS = (
    ProxySpec(
        name="h30_union_planned_red_light_cost",
        path=("candidate_horizon_union_planned_red_light_cost",),
        family="safety",
        direction="lower_better",
    ),
    ProxySpec(
        name="h80_full_planned_red_light_cost",
        path=("candidate_full_horizon_planned_red_light_cost",),
        family="safety",
        direction="lower_better",
    ),
    ProxySpec(
        name="red_stopping_margin_cost",
        path=("candidate_red_stopping_margin_cost",),
        family="safety",
        direction="lower_better",
    ),
    ProxySpec(
        name="soft_clearance_violation_cost",
        path=("candidate_obstacle_clearance", "soft_clearance_violation_cost"),
        family="safety",
        direction="lower_better",
    ),
    ProxySpec(
        name="near_miss_violation_cost",
        path=("candidate_obstacle_clearance", "near_miss_violation_cost"),
        family="safety",
        direction="lower_better",
    ),
    ProxySpec(
        name="horizon_lateral_acceleration_cost",
        path=("candidate_horizon_lateral_acceleration_cost",),
        family="comfort",
        direction="lower_better",
    ),
    ProxySpec(
        name="horizon_yaw_rate_cost",
        path=("candidate_horizon_yaw_rate_cost",),
        family="comfort",
        direction="lower_better",
    ),
    ProxySpec(
        name="perfect_tracker_jerk_magnitude_mps3",
        path=("candidate_perfect_tracker_jerk_magnitude_mps3",),
        family="comfort",
        direction="lower_better",
    ),
    ProxySpec(
        name="perfect_tracker_lateral_acceleration_magnitude_mps2",
        path=("candidate_perfect_tracker_lateral_acceleration_magnitude_mps2",),
        family="comfort",
        direction="lower_better",
    ),
    ProxySpec(
        name="route_progress_m",
        path=("candidate_route_progress",),
        family="progress",
        direction="higher_better",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Existing-smoke safety/comfort/progress proxy comparison between "
            "deployed selected candidates and temporal-consistency shadow-selected "
            "candidates. This reads existing logs only."
        )
    )
    parser.add_argument("--weight_sensitivity_json", type=Path, required=True)
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
        help=(
            "Positive shadow weight to analyze. May be repeated. Defaults to all "
            "positive source weights that changed at least one record."
        ),
    )
    parser.add_argument(
        "--min_evidence_changed_records",
        type=int,
        default=DEFAULT_MIN_EVIDENCE_CHANGED_RECORDS,
    )
    parser.add_argument(
        "--required_safety_nondegrading_fraction",
        type=float,
        default=DEFAULT_REQUIRED_SAFETY_NONDEGRADING_FRACTION,
    )
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--require_pass", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        weight_sensitivity=_load_json(args.weight_sensitivity_json),
        candidate_root=args.candidate_root,
        expected_logs=args.expected_logs,
        expected_records=args.expected_records,
        expected_candidates=args.expected_candidates,
        expected_available_records=args.expected_available_records,
        weight_grid=tuple(args.shadow_weight) if args.shadow_weight else None,
        min_evidence_changed_records=args.min_evidence_changed_records,
        required_safety_nondegrading_fraction=(
            args.required_safety_nondegrading_fraction
        ),
        label=args.label,
        paths={
            "weight_sensitivity_json": str(args.weight_sensitivity_json),
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
    weight_sensitivity: dict[str, Any],
    candidate_root: Path,
    expected_logs: int,
    expected_records: int,
    expected_candidates: int,
    expected_available_records: int,
    weight_grid: tuple[float, ...] | None = None,
    min_evidence_changed_records: int = DEFAULT_MIN_EVIDENCE_CHANGED_RECORDS,
    required_safety_nondegrading_fraction: float = (
        DEFAULT_REQUIRED_SAFETY_NONDEGRADING_FRACTION
    ),
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    if expected_logs <= 0:
        raise ValueError("expected_logs must be positive.")
    if expected_records <= 0:
        raise ValueError("expected_records must be positive.")
    if expected_candidates <= 0:
        raise ValueError("expected_candidates must be positive.")
    if expected_available_records < 0:
        raise ValueError("expected_available_records must be nonnegative.")
    if min_evidence_changed_records <= 0:
        raise ValueError("min_evidence_changed_records must be positive.")
    if not 0.0 <= required_safety_nondegrading_fraction <= 1.0:
        raise ValueError("required_safety_nondegrading_fraction must be in [0, 1].")

    source = _source_summary(weight_sensitivity)
    weights = _resolved_weight_grid(weight_grid, weight_sensitivity)
    logs = _load_selection_logs(candidate_root)
    source_records = _source_records_by_global_index(weight_sensitivity)
    records = [
        _proxy_record(
            record=record,
            source_record=source_records.get(global_index),
            run_id=run_id,
            record_index=record_index,
            global_index=global_index,
            expected_candidates=expected_candidates,
            weight_grid=weights,
        )
        for global_index, (run_id, record_index, record) in enumerate(_iter_records(logs))
    ]
    summary = _summary(records, logs, weights)
    evidence = _safety_proxy_evidence(
        summary,
        min_changed_records=min_evidence_changed_records,
        required_nondegrading_fraction=required_safety_nondegrading_fraction,
    )
    checks = [
        *_source_checks(source),
        *_record_count_checks(
            summary,
            expected_logs=expected_logs,
            expected_records=expected_records,
            expected_available_records=expected_available_records,
        ),
        *_proxy_checks(summary),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_temporal_consistency_shadow_safety_proxy_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used": False,
            "selection_effect": False,
            "paths": paths or {},
            "proxy_specs": [
                {
                    "name": spec.name,
                    "path": list(spec.path),
                    "family": spec.family,
                    "direction": spec.direction,
                }
                for spec in PROXY_SPECS
            ],
            "math_boundary": (
                "This gate reads existing nonformal smoke logs and an accepted "
                "shadow weight-sensitivity report. For each current-tick finite "
                "candidate set, it compares the deployed selected candidate with "
                "the shadow-selected candidate under fixed positive shadow weights "
                "using already logged current-candidate proxy fields only. The "
                "temporal-consistency coefficient and all proxy values are fixed "
                "before scoring; no future closed-loop outcome labels are read. "
                "The CAMP score remains affine in weights, score_k(w)=a_k^T w, "
                "and the simplex/CVaR/L2 master boundary remains convex. This is "
                "not a DP-side classical Benders decomposition and does not deploy "
                "or train a selector."
            ),
        },
        "source_summary": source,
        "weight_grid": list(weights),
        "thresholds": {
            "min_evidence_changed_records": min_evidence_changed_records,
            "required_safety_nondegrading_fraction": (
                required_safety_nondegrading_fraction
            ),
            "delta_tolerance": DELTA_TOLERANCE,
        },
        "proxy_records": records,
        "proxy_summary": summary,
        "safety_proxy_evidence": evidence,
        "proxy_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(
            passed=passed,
            checks=checks,
            summary=summary,
            evidence=evidence,
        ),
    }


def _source_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    summary = report.get("sensitivity_summary") or {}
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "safety_benefit_evidence": bool(decision.get("safety_benefit_evidence")),
        "atom_promotion_authorized": bool(decision.get("atom_promotion_authorized")),
        "blocked_action_conflicts": conflicts,
        "available_records": int(summary.get("available_records", -1)),
        "valid_available_records": int(summary.get("valid_available_records", -1)),
        "zero_weight_changed_records": summary.get("zero_weight_changed_records"),
        "positive_weight_any_change": bool(summary.get("positive_weight_any_change")),
        "max_changed_records": int(decision.get("max_changed_records", -1)),
    }


def _proxy_record(
    *,
    record: dict[str, Any],
    source_record: dict[str, Any] | None,
    run_id: str,
    record_index: int,
    global_index: int,
    expected_candidates: int,
    weight_grid: tuple[float, ...],
) -> dict[str, Any]:
    errors: list[str] = []
    payload = record.get(PAYLOAD_KEY)
    source_available = bool(source_record and source_record.get("available"))
    log_available = bool(isinstance(payload, dict) and payload.get("available"))
    if source_record is None:
        errors.append("source_record_missing")
    if source_available != log_available:
        errors.append("source_log_availability_mismatch")
    if not source_available and not log_available:
        return {
            "run_id": run_id,
            "record_index": record_index,
            "global_index": global_index,
            "available": False,
            "passed": not errors,
            "errors": errors,
            "weight_results": [],
        }
    if not isinstance(payload, dict):
        errors.append("payload_missing")
    elif _payload_has_forbidden_effect(payload):
        errors.append("payload_forbidden_effect_flag")
    if record.get("candidate_closed_loop_outcomes") is not None:
        errors.append("candidate_closed_loop_outcomes_present")

    selected_index = _optional_int(record.get("selected_index"))
    source_selected_index = _optional_int(source_record.get("selected_index"))
    if selected_index != source_selected_index:
        errors.append("source_log_selected_index_mismatch")
    if selected_index is None or selected_index < 0 or selected_index >= expected_candidates:
        errors.append("selected_index_invalid")

    proxy_vectors = _proxy_vectors(record, expected_candidates)
    errors.extend(proxy_vectors["errors"])
    weight_results = []
    for weight in weight_grid:
        source_weight_result = _source_weight_result(source_record, weight)
        if source_weight_result is None:
            errors.append(f"source_weight_result_missing:{weight}")
            continue
        shadow_selected_index = _optional_int(
            source_weight_result.get("shadow_selected_index")
        )
        if (
            shadow_selected_index is None
            or shadow_selected_index < 0
            or shadow_selected_index >= expected_candidates
        ):
            errors.append(f"shadow_selected_index_invalid:{weight}")
            continue
        changed = bool(source_weight_result.get("changed_selected_index"))
        comparisons = []
        for spec in PROXY_SPECS:
            values = proxy_vectors["values"].get(spec.name)
            if values is None:
                continue
            selected_value = values[selected_index] if selected_index is not None else math.nan
            shadow_value = values[shadow_selected_index]
            improvement = _improvement(
                selected_value=selected_value,
                shadow_value=shadow_value,
                direction=spec.direction,
            )
            comparisons.append(
                {
                    "name": spec.name,
                    "family": spec.family,
                    "direction": spec.direction,
                    "selected_value": selected_value,
                    "shadow_selected_value": shadow_value,
                    "improvement": improvement,
                    "classification": _classify_delta(improvement),
                }
            )
        weight_results.append(
            {
                "weight": weight,
                "shadow_selected_index": shadow_selected_index,
                "changed_selected_index": changed,
                "proxy_comparisons": comparisons if changed else [],
            }
        )
    return {
        "run_id": run_id,
        "record_index": record_index,
        "global_index": global_index,
        "available": True,
        "selected_index": selected_index,
        "passed": not errors,
        "errors": errors,
        "weight_results": weight_results,
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
        changed_records = []
        proxy_deltas: dict[str, list[float]] = {spec.name: [] for spec in PROXY_SPECS}
        family_rows: dict[str, list[dict[str, bool]]] = {
            family: [] for family in sorted({spec.family for spec in PROXY_SPECS})
        }
        changed_global_indices = []
        for record in valid_available:
            result = _record_weight_result(record, weight)
            if not result or not result["changed_selected_index"]:
                continue
            changed_records.append(record)
            changed_global_indices.append(record["global_index"])
            by_family: dict[str, list[float]] = {
                family: [] for family in family_rows
            }
            for comparison in result["proxy_comparisons"]:
                delta = comparison["improvement"]
                if not math.isfinite(delta):
                    continue
                proxy_deltas[comparison["name"]].append(delta)
                by_family[comparison["family"]].append(delta)
            for family, deltas in by_family.items():
                if deltas:
                    family_rows[family].append(_family_record_flags(deltas))
        changed_count = len(changed_records)
        by_weight.append(
            {
                "weight": weight,
                "changed_records": changed_count,
                "changed_fraction": (
                    changed_count / len(valid_available) if valid_available else 0.0
                ),
                "changed_global_indices": changed_global_indices,
                "proxy_summary": _proxy_delta_summary(proxy_deltas),
                "family_summary": _family_summary(family_rows, changed_count),
            }
        )
    return {
        "log_count": len(logs),
        "records": len(records),
        "available_records": len(available),
        "valid_available_records": len(valid_available),
        "invalid_available_records": len(available) - len(valid_available),
        "record_error_counts": _error_counts(records),
        "weights": list(weights),
        "by_weight": by_weight,
        "positive_weight_any_change": any(
            item["weight"] > 0.0 and item["changed_records"] > 0 for item in by_weight
        ),
        "max_changed_records": max(
            (item["changed_records"] for item in by_weight), default=0
        ),
    }


def _safety_proxy_evidence(
    summary: dict[str, Any],
    *,
    min_changed_records: int,
    required_nondegrading_fraction: float,
) -> dict[str, Any]:
    accepted_weights = []
    for item in summary["by_weight"]:
        safety = item["family_summary"].get("safety") or {}
        changed = int(item["changed_records"])
        if changed <= 0:
            nondegrading_fraction = 0.0
        else:
            nondegrading_fraction = safety.get("nondegrading_records", 0) / changed
        has_evidence = (
            changed >= min_changed_records
            and nondegrading_fraction >= required_nondegrading_fraction
            and safety.get("improved_records", 0) > 0
            and safety.get("worsened_records", 0) == 0
        )
        accepted_weights.append(
            {
                "weight": item["weight"],
                "changed_records": changed,
                "safety_nondegrading_fraction": nondegrading_fraction,
                "safety_improved_records": safety.get("improved_records", 0),
                "safety_worsened_records": safety.get("worsened_records", 0),
                "passes_safety_proxy_evidence": has_evidence,
            }
        )
    return {
        "has_safety_proxy_evidence": any(
            item["passes_safety_proxy_evidence"] for item in accepted_weights
        ),
        "weights": accepted_weights,
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status", source["status"], SOURCE_READY_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal(
            "source_authorizes_safety_proxy",
            source["authorized_next_work"],
            SOURCE_READY_NEXT_WORK,
        ),
        _check_equal("source_safety_benefit_not_claimed", source["safety_benefit_evidence"], False),
        _check_equal("source_atom_promotion_not_authorized", source["atom_promotion_authorized"], False),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
        _check_equal("source_positive_weight_has_shadow_effect", source["positive_weight_any_change"], True),
        _check_equal("source_max_changed_records_positive", source["max_changed_records"] > 0, True),
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


def _proxy_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("grid_contains_positive", any(w > 0.0 for w in summary["weights"]), True),
        _check_equal(
            "positive_weight_has_shadow_effect",
            summary["positive_weight_any_change"],
            True,
        ),
        _check_equal("max_changed_records_positive", summary["max_changed_records"] > 0, True),
    ]


def _final_decision(
    *,
    passed: bool,
    checks: list[dict[str, Any]],
    summary: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    has_safety_evidence = bool(evidence["has_safety_proxy_evidence"])
    authorized_next = None
    if passed:
        authorized_next = (
            SAFETY_EVIDENCE_NEXT_WORK if has_safety_evidence else NO_EVIDENCE_NEXT_WORK
        )
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": authorized_next,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "safety_proxy_evidence": has_safety_evidence,
        "safety_benefit_evidence": has_safety_evidence,
        "atom_promotion_authorized": False,
        "camp_retraining_authorized": False,
        "online_selector_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_replay_authorized": False,
        "max_changed_records": summary["max_changed_records"],
        "next_step": (
            "If accepted after audit, design a default-off selector budget preflight. "
            "Do not deploy or retrain."
            if passed and has_safety_evidence
            else (
                "Reject temporal consistency as a safety-benefit source for this "
                "smoke and predeclare a different current-tick no-leak atom/source."
                if passed
                else "Reject this diagnostic and inspect the source report or log contract."
            )
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["proxy_summary"]
    lines = [
        "# Temporal Consistency Shadow Safety Proxy",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Safety proxy evidence: `{decision['safety_proxy_evidence']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Max changed records: `{decision['max_changed_records']}`",
        "",
        "## Weight Summary",
        "",
        "| Weight | Changed Records | Safety Improved | Safety Worsened | Safety Nondegrading | Progress Mean Improvement |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in summary["by_weight"]:
        safety = item["family_summary"].get("safety") or {}
        progress = item["family_summary"].get("progress") or {}
        lines.append(
            f"| `{item['weight']}` | `{item['changed_records']}` | "
            f"`{safety.get('improved_records', 0)}` | "
            f"`{safety.get('worsened_records', 0)}` | "
            f"`{safety.get('nondegrading_records', 0)}` | "
            f"`{progress.get('mean_record_sum_improvement')}` |"
        )
    lines.extend(["", "## Proxy Details", ""])
    for item in summary["by_weight"]:
        lines.extend(
            [
                f"### Weight `{item['weight']}`",
                "",
                "| Proxy | Family | Improved | Worsened | Mean Improvement | Min Improvement | Max Improvement |",
                "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for proxy in item["proxy_summary"]:
            lines.append(
                f"| `{proxy['name']}` | `{proxy['family']}` | "
                f"`{proxy['improved_count']}` | `{proxy['worsened_count']}` | "
                f"`{proxy['mean_improvement']}` | `{proxy['min_improvement']}` | "
                f"`{proxy['max_improvement']}` |"
            )
        lines.append("")
    lines.extend(["## Mathematical Boundary", "", report["analysis"]["math_boundary"], ""])
    lines.extend(["## Checks", "", "| Check | Passed | Observed | Expected |", "| --- | ---: | --- | --- |"])
    for check in report["proxy_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _resolved_weight_grid(
    requested: tuple[float, ...] | None,
    report: dict[str, Any],
) -> tuple[float, ...]:
    if requested is not None:
        values = requested
    else:
        values = tuple(
            float(item["weight"])
            for item in (report.get("sensitivity_summary") or {}).get("by_weight", [])
            if float(item.get("weight", 0.0)) > 0.0
            and int(item.get("changed_records", 0)) > 0
        )
    parsed = sorted({float(value) for value in values})
    if not parsed:
        raise ValueError("weight grid must contain at least one positive value.")
    if any((not math.isfinite(value)) or value <= 0.0 for value in parsed):
        raise ValueError("safety-proxy shadow weights must be finite and positive.")
    return tuple(parsed)


def _source_records_by_global_index(report: dict[str, Any]) -> dict[int, dict[str, Any]]:
    result = {}
    for record in report.get("sensitivity_records") or []:
        if isinstance(record, dict):
            index = _optional_int(record.get("global_index"))
            if index is not None:
                result[index] = record
    return result


def _source_weight_result(
    source_record: dict[str, Any] | None,
    weight: float,
) -> dict[str, Any] | None:
    if not source_record:
        return None
    for item in source_record.get("weight_results") or []:
        try:
            item_weight = float(item.get("weight"))
        except (TypeError, ValueError):
            continue
        if abs(item_weight - weight) <= INDEX_TOLERANCE:
            return item
    return None


def _record_weight_result(
    record: dict[str, Any],
    weight: float,
) -> dict[str, Any] | None:
    for item in record.get("weight_results") or []:
        if abs(float(item.get("weight")) - weight) <= INDEX_TOLERANCE:
            return item
    return None


def _proxy_vectors(
    record: dict[str, Any],
    expected_candidates: int,
) -> dict[str, Any]:
    values: dict[str, list[float]] = {}
    errors: list[str] = []
    for spec in PROXY_SPECS:
        raw = _get_path(record, spec.path)
        vector = _float_vector(raw)
        if len(vector) != expected_candidates:
            errors.append(f"proxy_shape_mismatch:{spec.name}")
            continue
        if any(not math.isfinite(value) for value in vector):
            errors.append(f"proxy_nonfinite:{spec.name}")
            continue
        values[spec.name] = vector
    return {"values": values, "errors": errors}


def _get_path(record: dict[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = record
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _payload_has_forbidden_effect(payload: dict[str, Any]) -> bool:
    for key in (
        "selection_effect",
        "future_outcome_leakage",
        "closed_loop_outcome_fields_read",
        "online_selector_change",
        "deployed_atom_vector_change",
        "classical_benders_claim",
    ):
        if bool(payload.get(key)):
            return True
    return False


def _improvement(
    *,
    selected_value: float,
    shadow_value: float,
    direction: str,
) -> float:
    if direction == "lower_better":
        return selected_value - shadow_value
    if direction == "higher_better":
        return shadow_value - selected_value
    raise ValueError(f"unsupported proxy direction: {direction}")


def _classify_delta(value: float) -> str:
    if value > DELTA_TOLERANCE:
        return "improved"
    if value < -DELTA_TOLERANCE:
        return "worsened"
    return "unchanged"


def _family_record_flags(deltas: list[float]) -> dict[str, bool]:
    return {
        "improved": any(delta > DELTA_TOLERANCE for delta in deltas),
        "worsened": any(delta < -DELTA_TOLERANCE for delta in deltas),
        "nondegrading": all(delta >= -DELTA_TOLERANCE for delta in deltas),
        "record_sum_improvement": sum(deltas),
    }


def _proxy_delta_summary(
    proxy_deltas: dict[str, list[float]],
) -> list[dict[str, Any]]:
    by_name = {spec.name: spec for spec in PROXY_SPECS}
    result = []
    for name, deltas in proxy_deltas.items():
        spec = by_name[name]
        result.append(
            {
                "name": name,
                "family": spec.family,
                "direction": spec.direction,
                "count": len(deltas),
                "improved_count": sum(delta > DELTA_TOLERANCE for delta in deltas),
                "worsened_count": sum(delta < -DELTA_TOLERANCE for delta in deltas),
                "unchanged_count": sum(abs(delta) <= DELTA_TOLERANCE for delta in deltas),
                "mean_improvement": _mean(deltas),
                "min_improvement": min(deltas) if deltas else math.nan,
                "max_improvement": max(deltas) if deltas else math.nan,
            }
        )
    return result


def _family_summary(
    rows: dict[str, list[dict[str, bool]]],
    changed_records: int,
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for family, family_rows in rows.items():
        record_sums = [
            float(row["record_sum_improvement"]) for row in family_rows
        ]
        result[family] = {
            "changed_records_with_family": len(family_rows),
            "changed_records_missing_family": changed_records - len(family_rows),
            "improved_records": sum(bool(row["improved"]) for row in family_rows),
            "worsened_records": sum(bool(row["worsened"]) for row in family_rows),
            "nondegrading_records": sum(
                bool(row["nondegrading"]) for row in family_rows
            ),
            "mean_record_sum_improvement": _mean(record_sums),
        }
    return result


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


def _float_vector(value: Any) -> list[float]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        try:
            parsed = float(item)
        except (TypeError, ValueError):
            return []
        result.append(parsed)
    return result


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else math.nan


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
