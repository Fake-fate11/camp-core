#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
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
    MIN_BENEFICIAL_CANDIDATES,
    MIN_HARMFUL_CANDIDATES,
    MIN_VALUE_GAIN,
    MIN_VALUE_LOSS,
    PROGRESS_LOSS_BUDGET_M,
    FeatureSpec,
    _class_counts,
    _feature_report,
    _load_json,
    _outcome,
    _pair_reports,
    _path_seeds,
    _ranked_screens,
    _record_candidate_count,
    _record_seed,
    _validate_payload,
)


READY_STATUS = "route_progress_support_envelope_ready_for_certificate_design"
REJECT_STATUS = "route_progress_support_envelope_rejected"
SOURCE_BLOCKED_STATUS = "route_progress_support_envelope_source_not_ready"
FORMAL_SEED_STATUS = "route_progress_support_envelope_formal_seed_conflict"

BOTTLENECK_READY_STATUS = "observable_descriptor_bottleneck_diagnosed"
BOTTLENECK_NEXT_WORK = "predeclare_next_descriptor_family_or_reject_observable_route"
READY_NEXT_WORK = "offline_current_tick_certificate_design_only"

SUPPORT_ENVELOPE_WEIGHTS = {
    "max_progress_loss": 1.0,
    "progress_shape_rms": 0.25,
    "lateral_excess": 1.0,
    "segment_lag_steps": 0.5,
    "heading_excess": 1.0,
}

FEATURE_SPECS: tuple[FeatureSpec, ...] = (
    FeatureSpec(
        "prefix_route_final_progress_loss_vs_top1_m",
        "candidate_route_projection_s_m",
        "allow_low",
        "final prefix route-progress deficit against DP Top-1",
    ),
    FeatureSpec(
        "prefix_route_max_progress_loss_vs_top1_m",
        "candidate_route_projection_s_m",
        "allow_low",
        "largest aligned prefix route-progress deficit against DP Top-1",
    ),
    FeatureSpec(
        "prefix_route_mean_progress_loss_vs_top1_m",
        "candidate_route_projection_s_m",
        "allow_low",
        "mean aligned prefix route-progress deficit against DP Top-1",
    ),
    FeatureSpec(
        "prefix_route_min_aligned_progress_delta_m",
        "candidate_route_projection_s_m",
        "allow_high",
        "worst aligned prefix route-progress margin relative to DP Top-1",
    ),
    FeatureSpec(
        "prefix_route_progress_shape_rms_m",
        "candidate_route_projection_s_m",
        "allow_low",
        "RMS route-progress prefix deviation from DP Top-1",
    ),
    FeatureSpec(
        "prefix_route_progress_regression_m",
        "candidate_route_projection_s_m",
        "allow_low",
        "largest within-candidate backward route-progress step",
    ),
    FeatureSpec(
        "prefix_abs_lateral_error_max_m",
        "candidate_route_lateral_error_m",
        "allow_low",
        "maximum absolute lateral support error on the candidate prefix",
    ),
    FeatureSpec(
        "prefix_lateral_error_excess_vs_top1_m",
        "candidate_route_lateral_error_m",
        "allow_low",
        "extra maximum lateral support error compared with DP Top-1",
    ),
    FeatureSpec(
        "prefix_lateral_shape_rms_vs_top1_m",
        "candidate_route_lateral_error_m",
        "allow_low",
        "RMS lateral prefix deviation from DP Top-1",
    ),
    FeatureSpec(
        "prefix_segment_lag_steps_vs_top1",
        "candidate_route_segment_index",
        "allow_low",
        "number of aligned prefix steps whose route segment lags DP Top-1",
    ),
    FeatureSpec(
        "prefix_segment_abs_delta_max",
        "candidate_route_segment_index",
        "allow_low",
        "maximum absolute aligned route-segment deviation from DP Top-1",
    ),
    FeatureSpec(
        "prefix_heading_excess_vs_top1_rad",
        "candidate_route_heading_change_rad",
        "allow_low",
        "extra maximum heading-change support compared with DP Top-1",
    ),
    FeatureSpec(
        "route_progress_support_envelope_cost",
        "fixed_current_tick_descriptor_family",
        "allow_low",
        "fixed nonnegative weighted progress/support envelope score",
    ),
)

BLOCKED_ACTIONS = (
    "new_replay_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "online_selector_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline no-leak route-progress/support envelope screen over the "
            "existing matched observable-outcome artifact. This does not run DP "
            "or tune an online selector."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--bottleneck_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--min_value_gain", type=float, default=MIN_VALUE_GAIN)
    parser.add_argument("--min_value_loss", type=float, default=MIN_VALUE_LOSS)
    parser.add_argument("--progress_loss_budget_m", type=float, default=PROGRESS_LOSS_BUDGET_M)
    parser.add_argument("--harmful_block_rate_target", type=float, default=HARMFUL_BLOCK_RATE_TARGET)
    parser.add_argument("--beneficial_retain_rate_target", type=float, default=BENEFICIAL_RETAIN_RATE_TARGET)
    parser.add_argument("--allowed_harmful_rate_target", type=float, default=ALLOWED_HARMFUL_RATE_TARGET)
    parser.add_argument("--min_beneficial_candidates", type=int, default=MIN_BENEFICIAL_CANDIDATES)
    parser.add_argument("--min_harmful_candidates", type=int, default=MIN_HARMFUL_CANDIDATES)
    parser.add_argument("--fail_on_formal_seeds", action="store_true")
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
        bottleneck_report=_load_json(args.bottleneck_json),
        label=args.label,
        min_value_gain=args.min_value_gain,
        min_value_loss=args.min_value_loss,
        progress_loss_budget_m=args.progress_loss_budget_m,
        harmful_block_rate_target=args.harmful_block_rate_target,
        beneficial_retain_rate_target=args.beneficial_retain_rate_target,
        allowed_harmful_rate_target=args.allowed_harmful_rate_target,
        min_beneficial_candidates=args.min_beneficial_candidates,
        min_harmful_candidates=args.min_harmful_candidates,
        fail_on_formal_seeds=args.fail_on_formal_seeds,
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
    bottleneck_report: dict[str, Any],
    label: str | None = None,
    min_value_gain: float = MIN_VALUE_GAIN,
    min_value_loss: float = MIN_VALUE_LOSS,
    progress_loss_budget_m: float = PROGRESS_LOSS_BUDGET_M,
    harmful_block_rate_target: float = HARMFUL_BLOCK_RATE_TARGET,
    beneficial_retain_rate_target: float = BENEFICIAL_RETAIN_RATE_TARGET,
    allowed_harmful_rate_target: float = ALLOWED_HARMFUL_RATE_TARGET,
    min_beneficial_candidates: int = MIN_BENEFICIAL_CANDIDATES,
    min_harmful_candidates: int = MIN_HARMFUL_CANDIDATES,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    items = []
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
        bottleneck_report=bottleneck_report,
        label=label,
        min_value_gain=min_value_gain,
        min_value_loss=min_value_loss,
        progress_loss_budget_m=progress_loss_budget_m,
        harmful_block_rate_target=harmful_block_rate_target,
        beneficial_retain_rate_target=beneficial_retain_rate_target,
        allowed_harmful_rate_target=allowed_harmful_rate_target,
        min_beneficial_candidates=min_beneficial_candidates,
        min_harmful_candidates=min_harmful_candidates,
        fail_on_formal_seeds=fail_on_formal_seeds,
    )


def analyze_records(
    items: list[dict[str, Any]],
    *,
    bottleneck_report: dict[str, Any],
    label: str | None = None,
    min_value_gain: float = MIN_VALUE_GAIN,
    min_value_loss: float = MIN_VALUE_LOSS,
    progress_loss_budget_m: float = PROGRESS_LOSS_BUDGET_M,
    harmful_block_rate_target: float = HARMFUL_BLOCK_RATE_TARGET,
    beneficial_retain_rate_target: float = BENEFICIAL_RETAIN_RATE_TARGET,
    allowed_harmful_rate_target: float = ALLOWED_HARMFUL_RATE_TARGET,
    min_beneficial_candidates: int = MIN_BENEFICIAL_CANDIDATES,
    min_harmful_candidates: int = MIN_HARMFUL_CANDIDATES,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    source = _source_gate(bottleneck_report)
    rows: list[dict[str, Any]] = []
    formal_seed_records = 0
    for index, item in enumerate(items):
        record_rows, formal_seed = _candidate_rows(
            item["raw"],
            item["context"],
            f"record {index}",
            min_value_gain=min_value_gain,
            min_value_loss=min_value_loss,
            progress_loss_budget_m=progress_loss_budget_m,
        )
        rows.extend(record_rows)
        formal_seed_records += int(formal_seed)
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden for this offline gate.")

    alternative_rows = [row for row in rows if int(row["candidate_index"]) != 0]
    class_counts = _class_counts(alternative_rows)
    feature_reports = [
        _feature_report(
            spec,
            alternative_rows,
            harmful_block_rate_target=harmful_block_rate_target,
            beneficial_retain_rate_target=beneficial_retain_rate_target,
            allowed_harmful_rate_target=allowed_harmful_rate_target,
            min_beneficial_candidates=min_beneficial_candidates,
            min_harmful_candidates=min_harmful_candidates,
        )
        for spec in FEATURE_SPECS
    ]
    pair_reports = _pair_reports(
        feature_reports,
        alternative_rows,
        harmful_block_rate_target=harmful_block_rate_target,
        beneficial_retain_rate_target=beneficial_retain_rate_target,
        allowed_harmful_rate_target=allowed_harmful_rate_target,
        min_beneficial_candidates=min_beneficial_candidates,
        min_harmful_candidates=min_harmful_candidates,
    )
    ranked = _ranked_screens(feature_reports, pair_reports)
    failure_gap = _failure_gap(
        ranked,
        class_counts,
        source,
        formal_seed_records=formal_seed_records,
        min_beneficial_candidates=min_beneficial_candidates,
        min_harmful_candidates=min_harmful_candidates,
        harmful_block_rate_target=harmful_block_rate_target,
        beneficial_retain_rate_target=beneficial_retain_rate_target,
        allowed_harmful_rate_target=allowed_harmful_rate_target,
    )
    decision = _decision(
        source,
        ranked,
        class_counts,
        formal_seed_records=formal_seed_records,
        min_beneficial_candidates=min_beneficial_candidates,
        min_harmful_candidates=min_harmful_candidates,
    )
    return {
        "analysis": {
            "name": "dp_camp_route_progress_support_envelope_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "uses_existing_artifact_only": True,
            "future_outcome_labels_used_for_descriptors": False,
            "future_outcome_labels_used_for_classification": True,
            "thresholds_are_offline_oracle_diagnostics": True,
            "support_envelope_weights": SUPPORT_ENVELOPE_WEIGHTS,
            "acceptance_targets": {
                "harmful_block_rate": float(harmful_block_rate_target),
                "beneficial_retain_rate": float(beneficial_retain_rate_target),
                "allowed_harmful_rate": float(allowed_harmful_rate_target),
                "min_beneficial_candidates": int(min_beneficial_candidates),
                "min_harmful_candidates": int(min_harmful_candidates),
            },
            "math_boundary": (
                "All route-progress/support descriptors are fixed current-tick "
                "finite-candidate quantities computed from observable candidate "
                "prefixes before closed-loop outcomes. Outcome labels are used "
                "only offline to classify alternatives and score threshold "
                "diagnostics. If a descriptor is later atomized, it is a fixed "
                "candidate coefficient a_k, so CAMP scoring remains affine "
                "score_k(w)=a_k^T w and the simplex/CVaR/L2 master remains "
                "convex. This script constructs no classical DP-side Benders "
                "master, subproblem, dual, or cut."
            ),
        },
        "source_bottleneck_gate": source,
        "records": {
            "total_records": len(items),
            "candidate_rows": len(rows),
            "alternative_rows": len(alternative_rows),
            "formal_seed_records": formal_seed_records,
            "class_counts": class_counts,
        },
        "feature_specs": [_feature_payload(spec) for spec in FEATURE_SPECS],
        "feature_coverage": _feature_coverage(alternative_rows),
        "feature_reports": feature_reports,
        "pair_reports": pair_reports,
        "ranked_screens": ranked[:20],
        "failure_gap": failure_gap,
        "source_bottleneck_counts": bottleneck_report.get("counts"),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _candidate_rows(
    raw: dict[str, Any],
    context: dict[str, Any],
    label: str,
    *,
    min_value_gain: float,
    min_value_loss: float,
    progress_loss_budget_m: float,
) -> tuple[list[dict[str, Any]], bool]:
    payload = raw.get("observable_state_logging")
    outcomes = raw.get("candidate_closed_loop_outcomes")
    candidate_count = _record_candidate_count(raw, payload, outcomes, label)
    _validate_payload(payload, candidate_count, label)
    if not isinstance(payload, dict):
        raise ValueError(f"{label} missing observable payload.")
    if not isinstance(outcomes, list) or len(outcomes) != candidate_count:
        raise ValueError(f"{label} must contain complete candidate outcomes.")

    formal_seed = bool(set(context.get("path_seeds") or ()) & FORMAL_SEEDS)
    record_seed = _record_seed(raw)
    if record_seed in FORMAL_SEEDS:
        formal_seed = True

    top1 = _outcome(outcomes[0], f"{label} outcome 0")
    features = _descriptor_values(payload, candidate_count, label)
    rows = []
    for candidate_index, raw_outcome in enumerate(outcomes):
        outcome = _outcome(raw_outcome, f"{label} outcome {candidate_index}")
        value_delta = outcome["value"] - top1["value"]
        progress_delta = outcome["progress_m"] - top1["progress_m"]
        hard_worse = outcome["hard_violation_count"] > top1["hard_violation_count"]
        beneficial = (
            candidate_index != 0
            and outcome["feasible"]
            and value_delta >= float(min_value_gain)
            and progress_delta >= -float(progress_loss_budget_m)
            and not hard_worse
        )
        harmful = (
            candidate_index != 0
            and (
                not outcome["feasible"]
                or hard_worse
                or value_delta <= -float(min_value_loss)
                or progress_delta < -float(progress_loss_budget_m)
            )
        )
        if candidate_index == 0:
            cls = "top1_reference"
        elif beneficial:
            cls = CLASS_BENEFICIAL
        elif harmful:
            cls = CLASS_HARMFUL
        else:
            cls = CLASS_NEUTRAL
        rows.append(
            {
                "context": context,
                "candidate_index": candidate_index,
                "class": cls,
                "outcome_value_delta_vs_top1": value_delta,
                "progress_delta_vs_top1_m": progress_delta,
                "hard_violation_delta_vs_top1": (
                    outcome["hard_violation_count"] - top1["hard_violation_count"]
                ),
                "features": {
                    name: float(values[candidate_index])
                    for name, values in features.items()
                    if np.isfinite(values[candidate_index])
                },
            }
        )
    return rows, formal_seed


def _descriptor_values(
    payload: dict[str, Any],
    candidate_count: int,
    label: str,
) -> dict[str, np.ndarray]:
    projection = _payload_matrix(
        payload.get("candidate_route_projection_s_m"),
        candidate_count,
        f"{label} candidate_route_projection_s_m",
    )
    lateral = _payload_matrix(
        payload.get("candidate_route_lateral_error_m"),
        candidate_count,
        f"{label} candidate_route_lateral_error_m",
    )
    segment = _payload_matrix(
        payload.get("candidate_route_segment_index"),
        candidate_count,
        f"{label} candidate_route_segment_index",
    )
    heading = _payload_matrix(
        payload.get("candidate_route_heading_change_rad"),
        candidate_count,
        f"{label} candidate_route_heading_change_rad",
    )

    final_loss = np.full(candidate_count, np.nan, dtype=np.float64)
    max_loss = np.full(candidate_count, np.nan, dtype=np.float64)
    mean_loss = np.full(candidate_count, np.nan, dtype=np.float64)
    min_delta = np.full(candidate_count, np.nan, dtype=np.float64)
    progress_rms = np.full(candidate_count, np.nan, dtype=np.float64)
    regression = np.full(candidate_count, np.nan, dtype=np.float64)
    abs_lateral = np.full(candidate_count, np.nan, dtype=np.float64)
    lateral_excess = np.full(candidate_count, np.nan, dtype=np.float64)
    lateral_rms = np.full(candidate_count, np.nan, dtype=np.float64)
    segment_lag = np.full(candidate_count, np.nan, dtype=np.float64)
    segment_delta = np.full(candidate_count, np.nan, dtype=np.float64)
    heading_excess = np.full(candidate_count, np.nan, dtype=np.float64)

    for idx in range(candidate_count):
        progress_stats = _aligned_projection_stats(projection[0], projection[idx])
        final_loss[idx] = progress_stats["final_loss"]
        max_loss[idx] = progress_stats["max_loss"]
        mean_loss[idx] = progress_stats["mean_loss"]
        min_delta[idx] = progress_stats["min_delta"]
        progress_rms[idx] = progress_stats["rms"]
        regression[idx] = _monotonicity_regression(projection[idx])

        lateral_stats = _aligned_abs_stats(lateral[0], lateral[idx])
        abs_lateral[idx] = lateral_stats["candidate_abs_max"]
        lateral_excess[idx] = lateral_stats["excess_max"]
        lateral_rms[idx] = lateral_stats["rms_delta"]

        segment_stats = _aligned_segment_stats(segment[0], segment[idx])
        segment_lag[idx] = segment_stats["lag_steps"]
        segment_delta[idx] = segment_stats["abs_delta_max"]

        heading_stats = _aligned_abs_stats(heading[0], heading[idx])
        heading_excess[idx] = heading_stats["excess_max"]

    envelope = (
        SUPPORT_ENVELOPE_WEIGHTS["max_progress_loss"] * max_loss
        + SUPPORT_ENVELOPE_WEIGHTS["progress_shape_rms"] * progress_rms
        + SUPPORT_ENVELOPE_WEIGHTS["lateral_excess"] * lateral_excess
        + SUPPORT_ENVELOPE_WEIGHTS["segment_lag_steps"] * segment_lag
        + SUPPORT_ENVELOPE_WEIGHTS["heading_excess"] * heading_excess
    )

    return {
        "prefix_route_final_progress_loss_vs_top1_m": final_loss,
        "prefix_route_max_progress_loss_vs_top1_m": max_loss,
        "prefix_route_mean_progress_loss_vs_top1_m": mean_loss,
        "prefix_route_min_aligned_progress_delta_m": min_delta,
        "prefix_route_progress_shape_rms_m": progress_rms,
        "prefix_route_progress_regression_m": regression,
        "prefix_abs_lateral_error_max_m": abs_lateral,
        "prefix_lateral_error_excess_vs_top1_m": lateral_excess,
        "prefix_lateral_shape_rms_vs_top1_m": lateral_rms,
        "prefix_segment_lag_steps_vs_top1": segment_lag,
        "prefix_segment_abs_delta_max": segment_delta,
        "prefix_heading_excess_vs_top1_rad": heading_excess,
        "route_progress_support_envelope_cost": envelope,
    }


def _payload_matrix(value: Any, candidate_count: int, label: str) -> np.ndarray:
    if value is None:
        return np.full((candidate_count, 1), np.nan, dtype=np.float64)
    array = np.asarray(value, dtype=np.float64)
    if array.ndim == 1 and array.shape == (candidate_count,):
        return array.reshape(candidate_count, 1)
    if array.ndim == 2 and array.shape[0] == candidate_count:
        return array
    raise ValueError(f"{label} must have shape ({candidate_count},) or ({candidate_count}, H).")


def _aligned_projection_stats(top1: np.ndarray, candidate: np.ndarray) -> dict[str, float]:
    top, cand = _aligned_finite(top1, candidate)
    if top.size == 0:
        return _nan_stats(("final_loss", "max_loss", "mean_loss", "min_delta", "rms"))
    delta = cand - top
    loss = np.maximum(top - cand, 0.0)
    return {
        "final_loss": float(max(top[-1] - cand[-1], 0.0)),
        "max_loss": float(np.max(loss)),
        "mean_loss": float(np.mean(loss)),
        "min_delta": float(np.min(delta)),
        "rms": float(math.sqrt(float(np.mean(delta * delta)))),
    }


def _aligned_abs_stats(top1: np.ndarray, candidate: np.ndarray) -> dict[str, float]:
    top, cand = _aligned_finite(top1, candidate)
    if top.size == 0:
        return _nan_stats(("candidate_abs_max", "excess_max", "rms_delta"))
    abs_top = np.abs(top)
    abs_cand = np.abs(cand)
    delta = cand - top
    return {
        "candidate_abs_max": float(np.max(abs_cand)),
        "excess_max": float(max(np.max(abs_cand) - np.max(abs_top), 0.0)),
        "rms_delta": float(math.sqrt(float(np.mean(delta * delta)))),
    }


def _aligned_segment_stats(top1: np.ndarray, candidate: np.ndarray) -> dict[str, float]:
    top, cand = _aligned_finite(top1, candidate)
    if top.size == 0:
        return _nan_stats(("lag_steps", "abs_delta_max"))
    delta = cand - top
    return {
        "lag_steps": float(np.sum(delta < -1e-9)),
        "abs_delta_max": float(np.max(np.abs(delta))),
    }


def _aligned_finite(left: np.ndarray, right: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    horizon = min(len(left), len(right))
    if horizon <= 0:
        return np.asarray([], dtype=np.float64), np.asarray([], dtype=np.float64)
    left_prefix = np.asarray(left[:horizon], dtype=np.float64)
    right_prefix = np.asarray(right[:horizon], dtype=np.float64)
    mask = np.isfinite(left_prefix) & np.isfinite(right_prefix)
    return left_prefix[mask], right_prefix[mask]


def _monotonicity_regression(values: np.ndarray) -> float:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if finite.size < 2:
        return math.nan
    backwards = finite[:-1] - finite[1:]
    return float(max(np.max(backwards), 0.0))


def _nan_stats(names: tuple[str, ...]) -> dict[str, float]:
    return {name: math.nan for name in names}


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") if isinstance(report, dict) else None
    if not isinstance(decision, dict):
        return {"passed": False, "status": "missing_final_decision"}
    status = decision.get("status")
    next_work = decision.get("authorized_next_work")
    passed = bool(decision.get("passed")) and status == BOTTLENECK_READY_STATUS and next_work == BOTTLENECK_NEXT_WORK
    return {
        "passed": passed,
        "status": status,
        "authorized_next_work": next_work,
        "dominant_allowed_harmful_reason": (report.get("counts") or {}).get(
            "dominant_allowed_harmful_reason"
        ),
        "dominant_blocked_beneficial_reason": (report.get("counts") or {}).get(
            "dominant_blocked_beneficial_reason"
        ),
    }


def _decision(
    source: dict[str, Any],
    ranked_screens: list[dict[str, Any]],
    class_counts: dict[str, int],
    *,
    formal_seed_records: int,
    min_beneficial_candidates: int,
    min_harmful_candidates: int,
) -> dict[str, Any]:
    promising = [row for row in ranked_screens if row.get("promising_screen")]
    if not source["passed"]:
        status = SOURCE_BLOCKED_STATUS
        primary_gap = "bottleneck_gate_not_ready"
        next_work = None
    elif formal_seed_records:
        status = FORMAL_SEED_STATUS
        primary_gap = "formal_seed_conflict"
        next_work = None
    elif class_counts.get(CLASS_BENEFICIAL, 0) < int(min_beneficial_candidates):
        status = REJECT_STATUS
        primary_gap = "beneficial_candidate_support_insufficient"
        next_work = None
    elif class_counts.get(CLASS_HARMFUL, 0) < int(min_harmful_candidates):
        status = REJECT_STATUS
        primary_gap = "harmful_candidate_support_insufficient"
        next_work = None
    elif promising:
        status = READY_STATUS
        primary_gap = "no_gap_promising_route_progress_support_screen_found"
        next_work = READY_NEXT_WORK
    else:
        status = REJECT_STATUS
        primary_gap = "route_progress_support_envelope_does_not_separate_candidates"
        next_work = None
    return {
        "status": status,
        "passed": status == READY_STATUS,
        "primary_gap": primary_gap,
        "authorized_next_work": next_work,
        "promising_screen_count": len(promising),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def _failure_gap(
    ranked_screens: list[dict[str, Any]],
    class_counts: dict[str, int],
    source: dict[str, Any],
    *,
    formal_seed_records: int,
    min_beneficial_candidates: int,
    min_harmful_candidates: int,
    harmful_block_rate_target: float,
    beneficial_retain_rate_target: float,
    allowed_harmful_rate_target: float,
) -> dict[str, Any]:
    best = ranked_screens[0] if ranked_screens else None
    if not source["passed"]:
        primary = "bottleneck_gate_not_ready"
    elif formal_seed_records:
        primary = "formal_seed_conflict"
    elif class_counts.get(CLASS_BENEFICIAL, 0) < int(min_beneficial_candidates):
        primary = "beneficial_candidate_support_insufficient"
    elif class_counts.get(CLASS_HARMFUL, 0) < int(min_harmful_candidates):
        primary = "harmful_candidate_support_insufficient"
    elif best is None:
        primary = "no_finite_route_progress_support_screen"
    elif best["harmful_block_rate"] < float(harmful_block_rate_target):
        primary = "harmful_block_rate_insufficient"
    elif best["beneficial_retain_rate"] < float(beneficial_retain_rate_target):
        primary = "beneficial_retain_rate_insufficient"
    elif best["allowed_harmful_rate"] > float(allowed_harmful_rate_target):
        primary = "allowed_harmful_rate_too_high"
    else:
        primary = "no_gap_promising_route_progress_support_screen_found"
    return {"primary_gap": primary, "best_screen": best}


def _feature_coverage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        spec.name: _coverage(rows, spec.name)
        for spec in FEATURE_SPECS
    }


def _coverage(rows: list[dict[str, Any]], feature_name: str) -> dict[str, int]:
    finite = [
        row for row in rows
        if feature_name in row["features"] and np.isfinite(float(row["features"][feature_name]))
    ]
    varied = len({round(float(row["features"][feature_name]), 12) for row in finite}) > 1
    return {
        "finite_rows": len(finite),
        "total_rows": len(rows),
        "has_variation": int(varied),
    }


def _feature_payload(spec: FeatureSpec) -> dict[str, str]:
    return {
        "name": spec.name,
        "source_field": spec.source_field,
        "direction_hint": spec.direction_hint,
        "rationale": spec.rationale,
    }


def _top_screen_lines(report: dict[str, Any]) -> list[str]:
    screens = report.get("ranked_screens") or []
    if not screens:
        return ["No finite screen was available."]
    lines = []
    for idx, screen in enumerate(screens[:5], start=1):
        lines.append(
            f"{idx}. `{screen['screen_name']}` "
            f"harmful_block={screen['harmful_block_rate']:.6f}, "
            f"beneficial_retain={screen['beneficial_retain_rate']:.6f}, "
            f"allowed_harmful={screen['allowed_harmful_rate']:.6f}, "
            f"promising={screen['promising_screen']}"
        )
    return lines


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# DP CAMP Route Progress Support Envelope",
        "",
        "This is a read-only offline descriptor-family screen over the existing "
        "matched observable/outcome artifact. It does not run DP, select online "
        "trajectories, train CAMP, or authorize replay.",
        "",
        "## Decision",
        "",
        f"status=`{decision['status']}`",
        f"passed=`{decision['passed']}`",
        f"primary_gap=`{decision['primary_gap']}`",
        f"authorized_next_work=`{decision['authorized_next_work']}`",
        "",
        "## Records",
        "",
        "```json",
        json.dumps(report["records"], indent=2, sort_keys=True),
        "```",
        "",
        "## Top Screens",
        "",
        *_top_screen_lines(report),
        "",
        "## Failure Gap",
        "",
        "```json",
        json.dumps(report["failure_gap"], indent=2, sort_keys=True),
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
