#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner_coverage import (  # noqa: E402
    iter_selection_log_paths,
)
from scripts.integrations.analyze_diffusion_planner_matched_observable_descriptor_separability import (  # noqa: E402
    ALLOWED_HARMFUL_RATE_TARGET,
    BENEFICIAL_RETAIN_RATE_TARGET,
    CLASS_BENEFICIAL,
    CLASS_HARMFUL,
    CLASS_NEUTRAL,
    FORMAL_SEEDS,
    HARMFUL_BLOCK_RATE_TARGET,
    MIN_VALUE_GAIN,
    MIN_VALUE_LOSS,
    PROGRESS_LOSS_BUDGET_M,
    _class_counts,
    _load_json,
    _path_seeds,
    _payload_scalar_vector,
)
from scripts.integrations.analyze_diffusion_planner_observable_interaction_descriptor_separability import (  # noqa: E402
    DESCRIPTOR_SPECS,
    NEXT_WORK_BOTTLENECK as SOURCE_NEXT_WORK,
    REJECT_STATUS as SOURCE_REJECT_STATUS,
    _interaction_candidate_rows,
    _payload_vector,
)


READY_STATUS = "observable_interaction_descriptor_bottleneck_diagnosed"
SOURCE_BLOCKED_STATUS = "observable_interaction_descriptor_bottleneck_source_not_rejected"

NEXT_WORK_COVERAGE_PLAN = (
    "predeclare_broader_nonformal_observable_interaction_coverage_plan_only"
)
NEXT_WORK_REJECT = "reject_observable_interaction_descriptor_family_or_redefine_label"

BLOCKED_ACTIONS = (
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "online_selector_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only bottleneck diagnosis for the rejected observable "
            "interaction descriptor separability screen. It explains whether "
            "the failure comes from descriptor collapse, missing red/turn/"
            "obstacle variation, or true beneficial/harmful overlap."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--separability_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--red_distance_budget_m", type=float, default=5.0)
    parser.add_argument("--clearance_budget_m", type=float, default=2.0)
    parser.add_argument("--lateral_error_budget_m", type=float, default=0.5)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = [*args.root, *args.selection_log]
    if not paths:
        raise SystemExit("Provide at least one --root or --selection_log.")
    report = analyze(
        paths,
        separability_report=_load_json(args.separability_json),
        label=args.label,
        red_distance_budget_m=args.red_distance_budget_m,
        clearance_budget_m=args.clearance_budget_m,
        lateral_error_budget_m=args.lateral_error_budget_m,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def analyze(
    paths: list[Path],
    *,
    separability_report: dict[str, Any],
    label: str | None = None,
    red_distance_budget_m: float = 5.0,
    clearance_budget_m: float = 2.0,
    lateral_error_budget_m: float = 0.5,
) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    items: list[dict[str, Any]] = []
    for log_path in log_paths:
        rows = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for record_index, raw in enumerate(rows):
            if not isinstance(raw, dict):
                raise ValueError(f"{log_path} record {record_index} must be an object.")
            items.append(
                {
                    "raw": raw,
                    "context": {
                        "log_path": str(log_path),
                        "record_index": record_index,
                        "path_seeds": sorted(_path_seeds(log_path)),
                    },
                }
            )
    return analyze_records(
        items,
        separability_report=separability_report,
        label=label,
        red_distance_budget_m=red_distance_budget_m,
        clearance_budget_m=clearance_budget_m,
        lateral_error_budget_m=lateral_error_budget_m,
    )


def analyze_records(
    items: list[dict[str, Any]],
    *,
    separability_report: dict[str, Any],
    label: str | None = None,
    red_distance_budget_m: float = 5.0,
    clearance_budget_m: float = 2.0,
    lateral_error_budget_m: float = 0.5,
) -> dict[str, Any]:
    if not items:
        raise ValueError("At least one selection record is required.")

    source = _source_gate(separability_report)
    rows: list[dict[str, Any]] = []
    payload_contexts: list[dict[str, Any]] = []
    formal_seed_records = 0
    for index, item in enumerate(items):
        record_rows, record_formal = _interaction_candidate_rows(
            item["raw"],
            item["context"],
            f"record {index}",
            descriptor_specs=DESCRIPTOR_SPECS,
            red_distance_budget_m=red_distance_budget_m,
            clearance_budget_m=clearance_budget_m,
            lateral_error_budget_m=lateral_error_budget_m,
            min_value_gain=MIN_VALUE_GAIN,
            min_value_loss=MIN_VALUE_LOSS,
            progress_loss_budget_m=PROGRESS_LOSS_BUDGET_M,
        )
        rows.extend(record_rows)
        formal_seed_records += int(record_formal)
        payload_contexts.append(
            _payload_context(
                item["raw"],
                f"record {index}",
                red_distance_budget_m=red_distance_budget_m,
                clearance_budget_m=clearance_budget_m,
                lateral_error_budget_m=lateral_error_budget_m,
            )
        )
    alternative_rows = [row for row in rows if int(row["candidate_index"]) != 0]
    class_counts = _class_counts(alternative_rows)
    descriptor_diagnostics = _descriptor_diagnostics(alternative_rows)
    payload_materiality = _payload_materiality(payload_contexts)
    best_screen = (separability_report.get("failure_gap") or {}).get("best_screen")
    residual = _screen_residual(alternative_rows, best_screen)
    diagnosis = _diagnosis(
        source=source,
        descriptor_diagnostics=descriptor_diagnostics,
        payload_materiality=payload_materiality,
        residual=residual,
    )
    final = {
        "status": READY_STATUS if source["passed"] else SOURCE_BLOCKED_STATUS,
        "passed": bool(source["passed"]),
        "primary_gap": (
            diagnosis["primary_gap"] if source["passed"] else "source_gate_not_rejected"
        ),
        "authorized_next_work": (
            diagnosis["authorized_next_work"]
            if source["passed"]
            else "fix_interaction_separability_source_before_bottleneck"
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }
    return {
        "analysis": {
            "name": "dp_camp_observable_interaction_descriptor_bottleneck_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "closed_loop_replay": False,
            "online_selector_change": False,
            "uses_existing_artifact_only": True,
            "future_outcome_labels_used_for_runtime_features": False,
            "future_outcome_labels_used_for_bottleneck_diagnosis": True,
            "budgets": {
                "red_distance_budget_m": float(red_distance_budget_m),
                "clearance_budget_m": float(clearance_budget_m),
                "lateral_error_budget_m": float(lateral_error_budget_m),
            },
            "math_boundary": (
                "This diagnostic does not create selector thresholds or new "
                "atoms. It uses outcome labels only after the fixed rejected "
                "interaction screen to explain residual errors and payload "
                "coverage. Runtime-eligible quantities remain fixed current-"
                "tick finite-candidate descriptors; any later atomization must "
                "preserve affine score_k(w)=a_k^T w and the simplex/CVaR/L2 "
                "convex master. No DP-side classical Benders master/"
                "subproblem, dual, or cut is constructed."
            ),
        },
        "source_separability_gate": source,
        "records": {
            "total_records": len(items),
            "candidate_rows": len(rows),
            "alternative_rows": len(alternative_rows),
            "formal_seed_records": formal_seed_records,
            "class_counts": class_counts,
        },
        "payload_materiality": payload_materiality,
        "descriptor_diagnostics": descriptor_diagnostics,
        "screen_residual": residual,
        "diagnosis": diagnosis,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": final,
    }


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") if isinstance(report, dict) else None
    if not isinstance(decision, dict):
        return {
            "passed": False,
            "status": "missing_final_decision",
            "authorized_next_work": None,
        }
    passed = bool(
        not decision.get("passed")
        and decision.get("status") == SOURCE_REJECT_STATUS
        and decision.get("authorized_next_work") == SOURCE_NEXT_WORK
    )
    return {
        "passed": passed,
        "status": decision.get("status"),
        "primary_gap": decision.get("primary_gap"),
        "authorized_next_work": decision.get("authorized_next_work"),
        "promising_screen_count": decision.get("promising_screen_count"),
    }


def _payload_context(
    raw: dict[str, Any],
    label: str,
    *,
    red_distance_budget_m: float,
    clearance_budget_m: float,
    lateral_error_budget_m: float,
) -> dict[str, Any]:
    payload = raw.get("observable_state_logging")
    if not isinstance(payload, dict):
        raise ValueError(f"{label} missing observable_state_logging payload.")
    candidate_count = int(payload.get("candidate_count") or raw.get("num_candidates"))
    red_distance = _payload_vector(
        payload,
        "candidate_red_stopline_distance_m",
        candidate_count,
        label,
        none_value=np.inf,
    )
    red_alignment = _payload_vector(
        payload,
        "candidate_red_heading_alignment",
        candidate_count,
        label,
        none_value=0.0,
    )
    clearance = _payload_vector(
        payload,
        "candidate_min_obstacle_clearance_lower_bound_m",
        candidate_count,
        label,
    )
    heading = _payload_vector(
        payload,
        "candidate_route_heading_change_rad",
        candidate_count,
        label,
    )
    lateral = _payload_vector(
        payload,
        "candidate_route_lateral_error_m",
        candidate_count,
        label,
    )
    projection = _payload_vector(
        payload,
        "candidate_route_projection_s_m",
        candidate_count,
        label,
    )
    red_distance = _replace_nonfinite(red_distance, np.inf)
    red_alignment = _replace_nonfinite(red_alignment, 0.0)
    clearance = _replace_nonfinite(clearance, np.inf)
    heading = np.abs(_replace_nonfinite(heading, 0.0))
    lateral = np.abs(_replace_nonfinite(lateral, 0.0))
    projection = _replace_nonfinite(projection, 0.0)
    red_risk = np.maximum(red_alignment, 0.0) * np.maximum(
        float(red_distance_budget_m) - red_distance,
        0.0,
    )
    clearance_deficit = np.maximum(float(clearance_budget_m) - clearance, 0.0)
    lateral_excess = np.maximum(lateral - float(lateral_error_budget_m), 0.0)
    return {
        "candidate_count": candidate_count,
        "red_distance_present": raw.get("observable_state_logging", {}).get(
            "candidate_red_stopline_distance_m"
        )
        is not None,
        "red_risk": red_risk,
        "clearance": clearance,
        "clearance_deficit": clearance_deficit,
        "heading_abs": heading,
        "lateral_abs": lateral,
        "lateral_excess": lateral_excess,
        "projection": projection,
    }


def _payload_materiality(payload_contexts: list[dict[str, Any]]) -> dict[str, Any]:
    records = len(payload_contexts)
    metrics = {
        "records": records,
        "records_with_red_distance_payload": sum(
            int(item["red_distance_present"]) for item in payload_contexts
        ),
        "records_with_red_risk_nonzero": _records_with_any_positive(
            payload_contexts,
            "red_risk",
        ),
        "records_with_red_risk_candidate_variation": _records_with_variation(
            payload_contexts,
            "red_risk",
        ),
        "records_with_clearance_deficit_nonzero": _records_with_any_positive(
            payload_contexts,
            "clearance_deficit",
        ),
        "records_with_clearance_deficit_candidate_variation": _records_with_variation(
            payload_contexts,
            "clearance_deficit",
        ),
        "records_with_turn_signal_nonzero": _records_with_any_positive(
            payload_contexts,
            "heading_abs",
        ),
        "records_with_turn_signal_candidate_variation": _records_with_variation(
            payload_contexts,
            "heading_abs",
        ),
        "records_with_lateral_excess_nonzero": _records_with_any_positive(
            payload_contexts,
            "lateral_excess",
        ),
        "records_with_lateral_excess_candidate_variation": _records_with_variation(
            payload_contexts,
            "lateral_excess",
        ),
        "records_with_projection_candidate_variation": _records_with_variation(
            payload_contexts,
            "projection",
        ),
    }
    metrics["red_context_material"] = bool(
        metrics["records_with_red_risk_candidate_variation"]
    )
    metrics["clearance_context_material"] = bool(
        metrics["records_with_clearance_deficit_candidate_variation"]
    )
    metrics["turn_lateral_context_material"] = bool(
        metrics["records_with_turn_signal_candidate_variation"]
        and metrics["records_with_lateral_excess_candidate_variation"]
    )
    return metrics


def _descriptor_diagnostics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    diagnostics = {}
    for spec in DESCRIPTOR_SPECS:
        values = np.asarray(
            [
                row["features"].get(spec.name, np.nan)
                for row in rows
            ],
            dtype=np.float64,
        )
        finite = values[np.isfinite(values)]
        diagnostics[spec.name] = {
            "finite_rows": int(finite.size),
            "total_rows": len(rows),
            "unique_values": int(len({round(float(value), 12) for value in finite})),
            "has_variation": bool(
                len({round(float(value), 12) for value in finite}) > 1
            ),
            "nonzero_rows": int(np.sum(finite > 1e-12)),
            "beneficial_mean": _class_mean(rows, spec.name, CLASS_BENEFICIAL),
            "harmful_mean": _class_mean(rows, spec.name, CLASS_HARMFUL),
            "neutral_mean": _class_mean(rows, spec.name, CLASS_NEUTRAL),
        }
    collapsed = [
        name for name, report in diagnostics.items() if not report["has_variation"]
    ]
    varying = [
        name for name, report in diagnostics.items() if report["has_variation"]
    ]
    return {
        "per_descriptor": diagnostics,
        "collapsed_descriptors": collapsed,
        "varying_descriptors": varying,
        "collapsed_descriptor_count": len(collapsed),
        "varying_descriptor_count": len(varying),
    }


def _screen_residual(
    rows: list[dict[str, Any]],
    best_screen: Any,
) -> dict[str, Any]:
    if not isinstance(best_screen, dict):
        return {
            "has_best_screen": False,
            "allowed_harmful_count": 0,
            "blocked_beneficial_count": 0,
            "best_screen": None,
        }
    allowed = [_screen_allows(row, best_screen) for row in rows]
    allowed_harmful = [
        row for row, flag in zip(rows, allowed)
        if flag and row["class"] == CLASS_HARMFUL
    ]
    blocked_beneficial = [
        row for row, flag in zip(rows, allowed)
        if not flag and row["class"] == CLASS_BENEFICIAL
    ]
    return {
        "has_best_screen": True,
        "best_screen": best_screen,
        "allowed_harmful_count": len(allowed_harmful),
        "blocked_beneficial_count": len(blocked_beneficial),
        "allowed_harmful_reasons": _reason_counts(
            _harmful_reason(row) for row in allowed_harmful
        ),
        "blocked_beneficial_value_delta_mean": _mean(
            [row["outcome_value_delta_vs_top1"] for row in blocked_beneficial]
        ),
        "blocked_beneficial_progress_delta_mean_m": _mean(
            [row["progress_delta_vs_top1_m"] for row in blocked_beneficial]
        ),
        "allowed_harmful_value_delta_mean": _mean(
            [row["outcome_value_delta_vs_top1"] for row in allowed_harmful]
        ),
        "allowed_harmful_progress_delta_mean_m": _mean(
            [row["progress_delta_vs_top1_m"] for row in allowed_harmful]
        ),
    }


def _diagnosis(
    *,
    source: dict[str, Any],
    descriptor_diagnostics: dict[str, Any],
    payload_materiality: dict[str, Any],
    residual: dict[str, Any],
) -> dict[str, Any]:
    collapsed_count = int(descriptor_diagnostics["collapsed_descriptor_count"])
    varying_count = int(descriptor_diagnostics["varying_descriptor_count"])
    context_missing = [
        name for name, material in (
            ("red_context", payload_materiality["red_context_material"]),
            ("clearance_context", payload_materiality["clearance_context_material"]),
            (
                "turn_lateral_context",
                payload_materiality["turn_lateral_context_material"],
            ),
        )
        if not material
    ]
    best = residual.get("best_screen") or {}
    harmful_block = float(best.get("harmful_block_rate", 0.0))
    beneficial_retain = float(best.get("beneficial_retain_rate", 0.0))
    allowed_harmful = float(best.get("allowed_harmful_rate", 1.0))
    if not source["passed"]:
        primary_gap = "source_interaction_separability_not_rejected"
        next_work = "fix_interaction_separability_source_before_bottleneck"
    elif collapsed_count >= 3 and context_missing:
        primary_gap = (
            "interaction_descriptors_collapse_due_to_missing_context_variation"
        )
        next_work = NEXT_WORK_COVERAGE_PLAN
    elif varying_count and (
        harmful_block < HARMFUL_BLOCK_RATE_TARGET
        or beneficial_retain < BENEFICIAL_RETAIN_RATE_TARGET
        or allowed_harmful > ALLOWED_HARMFUL_RATE_TARGET
    ):
        primary_gap = "varying_interaction_descriptor_overlaps_beneficial_and_harmful"
        next_work = NEXT_WORK_REJECT
    else:
        primary_gap = "observable_interaction_bottleneck_unclassified"
        next_work = NEXT_WORK_REJECT
    return {
        "primary_gap": primary_gap,
        "authorized_next_work": next_work,
        "missing_context_families": context_missing,
        "collapsed_descriptor_count": collapsed_count,
        "varying_descriptor_count": varying_count,
        "best_screen_harmful_block_rate": harmful_block,
        "best_screen_beneficial_retain_rate": beneficial_retain,
        "best_screen_allowed_harmful_rate": allowed_harmful,
    }


def _screen_allows(row: dict[str, Any], screen: dict[str, Any]) -> bool:
    features = list(screen.get("feature_names") or [])
    directions = list(screen.get("directions") or [])
    thresholds = list(screen.get("thresholds") or [])
    if not (len(features) == len(directions) == len(thresholds)):
        return False
    for feature, direction, threshold in zip(features, directions, thresholds):
        value = row["features"].get(str(feature))
        if value is None or not np.isfinite(float(value)):
            return False
        if direction == "allow_low" and float(value) > float(threshold) + 1e-12:
            return False
        if direction == "allow_high" and float(value) < float(threshold) - 1e-12:
            return False
    return True


def _payload_field(
    payload: dict[str, Any],
    field: str,
    candidate_count: int,
    label: str,
    *,
    none_value: float | None = None,
) -> np.ndarray:
    value = payload.get(field)
    if value is None and none_value is not None:
        return np.full(candidate_count, float(none_value), dtype=np.float64)
    vector = _payload_scalar_vector(value, candidate_count, f"{label} {field}", field)
    if vector is None:
        return np.full(candidate_count, np.nan, dtype=np.float64)
    return vector


def _replace_nonfinite(values: np.ndarray, replacement: float) -> np.ndarray:
    result = np.asarray(values, dtype=np.float64).copy()
    result[~np.isfinite(result)] = float(replacement)
    return result


def _records_with_any_positive(
    payload_contexts: list[dict[str, Any]],
    field: str,
) -> int:
    return sum(int(np.any(np.asarray(item[field], dtype=np.float64) > 1e-12)) for item in payload_contexts)


def _records_with_variation(payload_contexts: list[dict[str, Any]], field: str) -> int:
    count = 0
    for item in payload_contexts:
        finite = np.asarray(item[field], dtype=np.float64)
        finite = finite[np.isfinite(finite)]
        if len({round(float(value), 12) for value in finite}) > 1:
            count += 1
    return count


def _class_mean(rows: list[dict[str, Any]], feature: str, cls: str) -> float | None:
    return _mean(
        [
            row["features"].get(feature)
            for row in rows
            if row["class"] == cls
        ]
    )


def _harmful_reason(row: dict[str, Any]) -> str:
    if row.get("collision_worse_than_top1"):
        return "collision_worse"
    if row.get("near_miss_worse_than_top1"):
        return "near_miss_worse"
    if row.get("red_light_worse_than_top1"):
        return "red_light_worse"
    if row.get("lane_worse_than_top1"):
        return "lane_worse"
    if float(row.get("progress_delta_vs_top1_m", 0.0)) < -PROGRESS_LOSS_BUDGET_M:
        return "progress_loss"
    if float(row.get("outcome_value_delta_vs_top1", 0.0)) <= -MIN_VALUE_LOSS:
        return "value_loss"
    return "other_harmful"


def _reason_counts(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[str(value)] = counts.get(str(value), 0) + 1
    return dict(sorted(counts.items()))


def _mean(values: list[Any]) -> float | None:
    finite = np.asarray(
        [float(value) for value in values if value is not None],
        dtype=np.float64,
    )
    finite = finite[np.isfinite(finite)]
    return None if finite.size == 0 else float(np.mean(finite))


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Observable Interaction Descriptor Bottleneck",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- primary gap: `{decision['primary_gap']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Records",
        "",
        "```json",
        json.dumps(report["records"], indent=2, sort_keys=True),
        "```",
        "",
        "## Payload Materiality",
        "",
        "```json",
        json.dumps(report["payload_materiality"], indent=2, sort_keys=True),
        "```",
        "",
        "## Descriptor Diagnostics",
        "",
        "```json",
        json.dumps(report["descriptor_diagnostics"], indent=2, sort_keys=True),
        "```",
        "",
        "## Screen Residual",
        "",
        "```json",
        json.dumps(report["screen_residual"], indent=2, sort_keys=True),
        "```",
        "",
        "## Mathematical Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
