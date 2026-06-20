#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
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


READY_STATUS = "matched_observable_descriptor_separability_ready_for_certificate_design"
REJECT_STATUS = "matched_observable_descriptor_separability_rejected"
SOURCE_BLOCKED_STATUS = "matched_observable_descriptor_separability_source_not_ready"
FORMAL_SEED_STATUS = "matched_observable_descriptor_separability_formal_seed_conflict"

CONTRACT_READY_STATUS = "matched_observable_outcome_contract_passed"
CONTRACT_NEXT_WORK = "offline_observable_descriptor_separability_screen_only"
OBSERVABLE_SCHEMA_VERSION = "dp_camp_observable_state_logging_v1"
FORMAL_SEEDS = frozenset({11, 12, 13})

MIN_VALUE_GAIN = 0.25
MIN_VALUE_LOSS = 0.25
PROGRESS_LOSS_BUDGET_M = 0.05
HARMFUL_BLOCK_RATE_TARGET = 0.75
BENEFICIAL_RETAIN_RATE_TARGET = 0.75
ALLOWED_HARMFUL_RATE_TARGET = 0.10
MIN_BENEFICIAL_CANDIDATES = 5
MIN_HARMFUL_CANDIDATES = 5
THRESHOLD_PERCENTILES = (0.0, 5.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 95.0, 100.0)

BLOCKED_ACTIONS = (
    "full36_authorized",
    "formal_seeds_authorized",
    "online_selector_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
)

CLASS_BENEFICIAL = "beneficial_alternative"
CLASS_HARMFUL = "harmful_alternative"
CLASS_NEUTRAL = "neutral_alternative"


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    source_field: str
    direction_hint: str
    rationale: str


FEATURE_SPECS: tuple[FeatureSpec, ...] = (
    FeatureSpec(
        "route_projection_delta_m",
        "candidate_route_projection_s_m",
        "both",
        "route-relative progress of a candidate compared with DP Top-1",
    ),
    FeatureSpec(
        "route_projection_loss_vs_top1_m",
        "candidate_route_projection_s_m",
        "allow_low",
        "current-tick route-progress deficit against DP Top-1",
    ),
    FeatureSpec(
        "abs_route_lateral_error_m",
        "candidate_route_lateral_error_m",
        "allow_low",
        "absolute route-relative lateral support error",
    ),
    FeatureSpec(
        "route_lateral_error_worse_vs_top1_m",
        "candidate_route_lateral_error_m",
        "allow_low",
        "extra absolute lateral support error compared with DP Top-1",
    ),
    FeatureSpec(
        "route_segment_abs_delta",
        "candidate_route_segment_index",
        "allow_low",
        "route-topology segment displacement from DP Top-1",
    ),
    FeatureSpec(
        "same_route_segment_as_top1",
        "candidate_route_segment_index",
        "allow_high",
        "same current route segment as DP Top-1",
    ),
    FeatureSpec(
        "abs_route_heading_change_rad",
        "candidate_route_heading_change_rad",
        "allow_low",
        "candidate prefix turn severity",
    ),
    FeatureSpec(
        "route_heading_change_worse_vs_top1_rad",
        "candidate_route_heading_change_rad",
        "allow_low",
        "extra turn severity compared with DP Top-1",
    ),
    FeatureSpec(
        "min_obstacle_clearance_lower_bound_m",
        "candidate_min_obstacle_clearance_lower_bound_m",
        "allow_high",
        "current-tick obstacle clearance lower bound",
    ),
    FeatureSpec(
        "obstacle_clearance_deficit_vs_top1_m",
        "candidate_min_obstacle_clearance_lower_bound_m",
        "allow_low",
        "current-tick clearance deficit compared with DP Top-1",
    ),
    FeatureSpec(
        "obstacle_slot_count",
        "candidate_obstacle_slot_count",
        "both",
        "number of current obstacle slots interacting with the candidate",
    ),
    FeatureSpec(
        "red_stopline_distance_m",
        "candidate_red_stopline_distance_m",
        "both",
        "candidate relation to current red-light stopline",
    ),
    FeatureSpec(
        "red_heading_alignment",
        "candidate_red_heading_alignment",
        "both",
        "candidate heading relation to current red-light stopline",
    ),
    FeatureSpec(
        "route_curvature_context_abs",
        "route_curvature_context_abs",
        "both",
        "route curvature context along the candidate prefix",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline no-leak separability screen over matched DP-CAMP "
            "observable-state descriptors and candidate outcome labels."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--matched_contract_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--min_value_gain", type=float, default=MIN_VALUE_GAIN)
    parser.add_argument("--min_value_loss", type=float, default=MIN_VALUE_LOSS)
    parser.add_argument("--progress_loss_budget_m", type=float, default=PROGRESS_LOSS_BUDGET_M)
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
        matched_contract_report=_load_json(args.matched_contract_json),
        label=args.label,
        min_value_gain=args.min_value_gain,
        min_value_loss=args.min_value_loss,
        progress_loss_budget_m=args.progress_loss_budget_m,
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
    matched_contract_report: dict[str, Any],
    label: str | None = None,
    min_value_gain: float = MIN_VALUE_GAIN,
    min_value_loss: float = MIN_VALUE_LOSS,
    progress_loss_budget_m: float = PROGRESS_LOSS_BUDGET_M,
    min_beneficial_candidates: int = MIN_BENEFICIAL_CANDIDATES,
    min_harmful_candidates: int = MIN_HARMFUL_CANDIDATES,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    items: list[dict[str, Any]] = []
    for log_path in log_paths:
        rows = _read_json(log_path)
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
        matched_contract_report=matched_contract_report,
        label=label,
        min_value_gain=min_value_gain,
        min_value_loss=min_value_loss,
        progress_loss_budget_m=progress_loss_budget_m,
        min_beneficial_candidates=min_beneficial_candidates,
        min_harmful_candidates=min_harmful_candidates,
        fail_on_formal_seeds=fail_on_formal_seeds,
    )


def analyze_records(
    items: list[dict[str, Any]],
    *,
    matched_contract_report: dict[str, Any],
    label: str | None = None,
    feature_specs: tuple[FeatureSpec, ...] = FEATURE_SPECS,
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
    if not items:
        raise ValueError("At least one selection record is required.")
    source = _source_gate(matched_contract_report)
    rows: list[dict[str, Any]] = []
    formal_seed_records = 0
    for index, item in enumerate(items):
        record_rows, record_formal = _candidate_rows(
            item["raw"],
            item["context"],
            f"record {index}",
            feature_specs,
            min_value_gain=min_value_gain,
            min_value_loss=min_value_loss,
            progress_loss_budget_m=progress_loss_budget_m,
        )
        formal_seed_records += int(record_formal)
        rows.extend(record_rows)
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")
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
        for spec in feature_specs
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
    decision = _decision(
        source,
        feature_reports,
        pair_reports,
        formal_seed_records=formal_seed_records,
        class_counts=class_counts,
        min_beneficial_candidates=min_beneficial_candidates,
        min_harmful_candidates=min_harmful_candidates,
    )
    return {
        "analysis": {
            "name": "dp_camp_matched_observable_descriptor_separability_v1",
            "label": label,
            "training": False,
            "diffusion_planner_execution": False,
            "online_selector_change": False,
            "future_outcome_labels_used_for_descriptors": False,
            "future_outcome_labels_used_for_thresholds": True,
            "future_outcome_labels_used_for_evaluation": True,
            "thresholds_are_offline_oracle_diagnostics": True,
            "top1_reference_candidate_index": 0,
            "feature_specs": [_feature_payload(spec) for spec in feature_specs],
            "label_definition": {
                "beneficial": (
                    "candidate k>0 is feasible, improves outcome value over "
                    "candidate0 by min_value_gain, preserves progress within "
                    "progress_loss_budget_m, and is hard-safety-nonworse"
                ),
                "harmful": (
                    "candidate k>0 is infeasible, hard-safety-worse, loses "
                    "more than min_value_loss in outcome value, or exceeds the "
                    "progress loss budget"
                ),
                "neutral": "all other k>0 candidates",
                "outcome_value_direction": "higher_is_better",
            },
            "accept_criteria": {
                "min_beneficial_candidates": int(min_beneficial_candidates),
                "min_harmful_candidates": int(min_harmful_candidates),
                "harmful_block_rate": f">= {harmful_block_rate_target}",
                "beneficial_retain_rate": f">= {beneficial_retain_rate_target}",
                "allowed_harmful_rate": f"<= {allowed_harmful_rate_target}",
            },
            "math_boundary": (
                "Observable descriptors are fixed current-tick finite-candidate "
                "quantities computed before candidate closed-loop outcomes. "
                "Outcome labels define only offline beneficial/harmful classes "
                "and threshold-screen diagnostics. If any descriptor is later "
                "atomized, it is a fixed coefficient a_k, so CAMP score_k(w)=a_k^T w "
                "remains affine and the simplex/CVaR/L2 robust master remains "
                "convex. No DP-side classical Benders master/subproblem, dual, "
                "or cut is constructed."
            ),
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
        },
        "source_matched_contract_gate": source,
        "records": {
            "total_records": len(items),
            "candidate_rows": len(rows),
            "alternative_rows": len(alternative_rows),
            "formal_seed_records": formal_seed_records,
            "class_counts": class_counts,
        },
        "feature_coverage": _feature_coverage(alternative_rows, feature_specs),
        "feature_reports": feature_reports,
        "pair_reports": pair_reports,
        "ranked_screens": _ranked_screens(feature_reports, pair_reports),
        "failure_gap": _failure_gap(feature_reports, pair_reports, class_counts),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _candidate_rows(
    raw: dict[str, Any],
    context: dict[str, Any],
    label: str,
    feature_specs: tuple[FeatureSpec, ...],
    *,
    min_value_gain: float,
    min_value_loss: float,
    progress_loss_budget_m: float,
) -> tuple[list[dict[str, Any]], bool]:
    payload = raw.get("observable_state_logging")
    outcomes = raw.get("candidate_closed_loop_outcomes")
    candidate_count = _record_candidate_count(raw, payload, outcomes, label)
    _validate_payload(payload, candidate_count, label)
    if not isinstance(outcomes, list) or len(outcomes) != candidate_count:
        raise ValueError(f"{label} must contain complete candidate outcomes.")
    formal_seed = bool(set(context.get("path_seeds") or ()) & FORMAL_SEEDS)
    record_seed = _record_seed(raw)
    if record_seed in FORMAL_SEEDS:
        formal_seed = True

    top1 = _outcome(outcomes[0], f"{label} outcome 0")
    rows = []
    feature_values = _feature_values(payload, feature_specs, candidate_count, label)
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
                    for name, values in feature_values.items()
                    if np.isfinite(values[candidate_index])
                },
            }
        )
    return rows, formal_seed


def _feature_values(
    payload: dict[str, Any],
    feature_specs: tuple[FeatureSpec, ...],
    candidate_count: int,
    label: str,
) -> dict[str, np.ndarray]:
    raw_fields: dict[str, np.ndarray | None] = {}
    for spec in feature_specs:
        if spec.source_field in raw_fields:
            continue
        raw_fields[spec.source_field] = _payload_scalar_vector(
            payload.get(spec.source_field),
            candidate_count,
            f"{label} {spec.source_field}",
            spec.source_field,
        )
    result: dict[str, np.ndarray] = {}
    for spec in feature_specs:
        values = raw_fields[spec.source_field]
        if values is None:
            result[spec.name] = np.full(candidate_count, np.nan, dtype=np.float64)
            continue
        top1 = float(values[0])
        if spec.name == "route_projection_delta_m":
            derived = values - top1
        elif spec.name == "route_projection_loss_vs_top1_m":
            derived = np.maximum(top1 - values, 0.0)
        elif spec.name == "abs_route_lateral_error_m":
            derived = np.abs(values)
        elif spec.name == "route_lateral_error_worse_vs_top1_m":
            derived = np.maximum(np.abs(values) - abs(top1), 0.0)
        elif spec.name == "route_segment_abs_delta":
            derived = np.abs(values - top1)
        elif spec.name == "same_route_segment_as_top1":
            derived = (np.abs(values - top1) <= 1e-9).astype(np.float64)
        elif spec.name == "abs_route_heading_change_rad":
            derived = np.abs(values)
        elif spec.name == "route_heading_change_worse_vs_top1_rad":
            derived = np.maximum(np.abs(values) - abs(top1), 0.0)
        elif spec.name == "obstacle_clearance_deficit_vs_top1_m":
            derived = np.maximum(top1 - values, 0.0)
        else:
            derived = values.astype(np.float64)
        result[spec.name] = np.asarray(derived, dtype=np.float64)
    return result


def _feature_report(
    spec: FeatureSpec,
    rows: list[dict[str, Any]],
    *,
    harmful_block_rate_target: float,
    beneficial_retain_rate_target: float,
    allowed_harmful_rate_target: float,
    min_beneficial_candidates: int,
    min_harmful_candidates: int,
) -> dict[str, Any]:
    directions = ("allow_low", "allow_high") if spec.direction_hint == "both" else (spec.direction_hint,)
    screens = []
    for direction in directions:
        screens.extend(
            _threshold_screens(
                screen_name=f"{spec.name}:{direction}",
                rows=rows,
                feature_names=(spec.name,),
                direction=direction,
                harmful_block_rate_target=harmful_block_rate_target,
                beneficial_retain_rate_target=beneficial_retain_rate_target,
                allowed_harmful_rate_target=allowed_harmful_rate_target,
                min_beneficial_candidates=min_beneficial_candidates,
                min_harmful_candidates=min_harmful_candidates,
            )
        )
    best = _best_screen(screens)
    return {
        "feature": spec.name,
        "source_field": spec.source_field,
        "direction_hint": spec.direction_hint,
        "rationale": spec.rationale,
        "coverage": _coverage(rows, spec.name),
        "auc_beneficial_vs_harmful": _auc_for_feature(rows, spec.name),
        "best_screen": best,
        "threshold_screens": screens,
    }


def _pair_reports(
    feature_reports: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    *,
    harmful_block_rate_target: float,
    beneficial_retain_rate_target: float,
    allowed_harmful_rate_target: float,
    min_beneficial_candidates: int,
    min_harmful_candidates: int,
) -> list[dict[str, Any]]:
    candidates = [
        report["best_screen"]
        for report in feature_reports
        if isinstance(report.get("best_screen"), dict)
    ]
    ranked = sorted(
        candidates,
        key=lambda row: (
            row["promising_screen"],
            row["harmful_block_rate"],
            row["beneficial_retain_rate"],
            -row["allowed_harmful_rate"],
        ),
        reverse=True,
    )[:8]
    reports = []
    for left_index, left in enumerate(ranked):
        for right in ranked[left_index + 1 :]:
            screens = _combined_screens(
                left,
                right,
                rows,
                harmful_block_rate_target=harmful_block_rate_target,
                beneficial_retain_rate_target=beneficial_retain_rate_target,
                allowed_harmful_rate_target=allowed_harmful_rate_target,
                min_beneficial_candidates=min_beneficial_candidates,
                min_harmful_candidates=min_harmful_candidates,
            )
            reports.append(
                {
                    "screen_name": f"{left['screen_name']} AND {right['screen_name']}",
                    "left": left,
                    "right": right,
                    "best_screen": _best_screen(screens),
                    "threshold_screens": screens,
                }
            )
    return sorted(
        reports,
        key=lambda row: _screen_sort_key(row.get("best_screen")),
        reverse=True,
    )[:10]


def _threshold_screens(
    *,
    screen_name: str,
    rows: list[dict[str, Any]],
    feature_names: tuple[str, ...],
    direction: str,
    harmful_block_rate_target: float,
    beneficial_retain_rate_target: float,
    allowed_harmful_rate_target: float,
    min_beneficial_candidates: int,
    min_harmful_candidates: int,
) -> list[dict[str, Any]]:
    values = np.asarray(
        [
            row["features"].get(feature_names[0], np.nan)
            for row in rows
        ],
        dtype=np.float64,
    )
    thresholds = _thresholds(values[np.isfinite(values)])
    return [
        _screen_metrics(
            rows,
            feature_names=feature_names,
            directions=(direction,),
            thresholds=(threshold,),
            screen_name=screen_name,
            harmful_block_rate_target=harmful_block_rate_target,
            beneficial_retain_rate_target=beneficial_retain_rate_target,
            allowed_harmful_rate_target=allowed_harmful_rate_target,
            min_beneficial_candidates=min_beneficial_candidates,
            min_harmful_candidates=min_harmful_candidates,
        )
        for threshold in thresholds
    ]


def _combined_screens(
    left: dict[str, Any],
    right: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    harmful_block_rate_target: float,
    beneficial_retain_rate_target: float,
    allowed_harmful_rate_target: float,
    min_beneficial_candidates: int,
    min_harmful_candidates: int,
) -> list[dict[str, Any]]:
    return [
        _screen_metrics(
            rows,
            feature_names=(
                str(left["feature_names"][0]),
                str(right["feature_names"][0]),
            ),
            directions=(str(left["directions"][0]), str(right["directions"][0])),
            thresholds=(float(left["thresholds"][0]), float(right["thresholds"][0])),
            screen_name=f"{left['screen_name']} AND {right['screen_name']}",
            harmful_block_rate_target=harmful_block_rate_target,
            beneficial_retain_rate_target=beneficial_retain_rate_target,
            allowed_harmful_rate_target=allowed_harmful_rate_target,
            min_beneficial_candidates=min_beneficial_candidates,
            min_harmful_candidates=min_harmful_candidates,
        )
    ]


def _screen_metrics(
    rows: list[dict[str, Any]],
    *,
    feature_names: tuple[str, ...],
    directions: tuple[str, ...],
    thresholds: tuple[float, ...],
    screen_name: str,
    harmful_block_rate_target: float,
    beneficial_retain_rate_target: float,
    allowed_harmful_rate_target: float,
    min_beneficial_candidates: int,
    min_harmful_candidates: int,
) -> dict[str, Any]:
    allowed = []
    considered = []
    for row in rows:
        row_allowed = True
        row_considered = True
        for feature_name, direction, threshold in zip(feature_names, directions, thresholds, strict=True):
            value = row["features"].get(feature_name)
            if value is None or not np.isfinite(float(value)):
                row_allowed = False
                row_considered = False
                break
            if direction == "allow_low":
                row_allowed = row_allowed and float(value) <= threshold + 1e-12
            elif direction == "allow_high":
                row_allowed = row_allowed and float(value) >= threshold - 1e-12
            else:
                raise ValueError(f"Unknown screen direction {direction!r}.")
        allowed.append(row_allowed)
        considered.append(row_considered)
    allowed_arr = np.asarray(allowed, dtype=bool)
    considered_arr = np.asarray(considered, dtype=bool)
    classes = np.asarray([row["class"] for row in rows], dtype=object)
    harmful = classes == CLASS_HARMFUL
    beneficial = classes == CLASS_BENEFICIAL
    neutral = classes == CLASS_NEUTRAL
    harmful_count = int(np.sum(harmful))
    beneficial_count = int(np.sum(beneficial))
    allowed_count = int(np.sum(allowed_arr))
    harmful_block_rate = _rate(np.sum(harmful & ~allowed_arr), harmful_count)
    beneficial_retain_rate = _rate(np.sum(beneficial & allowed_arr), beneficial_count)
    allowed_harmful_rate = _rate(np.sum(harmful & allowed_arr), allowed_count)
    value_deltas = np.asarray([row["outcome_value_delta_vs_top1"] for row in rows], dtype=np.float64)
    progress_deltas = np.asarray([row["progress_delta_vs_top1_m"] for row in rows], dtype=np.float64)
    promising = (
        harmful_count >= int(min_harmful_candidates)
        and beneficial_count >= int(min_beneficial_candidates)
        and harmful_block_rate >= float(harmful_block_rate_target)
        and beneficial_retain_rate >= float(beneficial_retain_rate_target)
        and allowed_harmful_rate <= float(allowed_harmful_rate_target)
    )
    return {
        "screen_name": screen_name,
        "feature_names": list(feature_names),
        "directions": list(directions),
        "thresholds": [float(value) for value in thresholds],
        "considered_candidates": int(np.sum(considered_arr)),
        "allowed_candidates": allowed_count,
        "blocked_candidates": int(len(rows) - allowed_count),
        "harmful_count": harmful_count,
        "beneficial_count": beneficial_count,
        "neutral_count": int(np.sum(neutral)),
        "harmful_block_rate": harmful_block_rate,
        "beneficial_retain_rate": beneficial_retain_rate,
        "allowed_harmful_rate": allowed_harmful_rate,
        "allowed_value_delta_mean": _mean(value_deltas[allowed_arr]),
        "allowed_progress_delta_mean_m": _mean(progress_deltas[allowed_arr]),
        "promising_screen": promising,
    }


def _validate_payload(payload: Any, candidate_count: int, label: str) -> None:
    if not isinstance(payload, dict):
        raise ValueError(f"{label} missing observable_state_logging payload.")
    expected = {
        "schema_version": OBSERVABLE_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            raise ValueError(f"{label} observable payload {field}={payload.get(field)!r}.")
    if "candidate_closed_loop_outcomes" in payload:
        raise ValueError(f"{label} observable payload embeds outcome labels.")
    if payload.get("candidate_count") != candidate_count:
        raise ValueError(f"{label} observable candidate_count mismatch.")
    finite_checks = payload.get("finite_checks")
    if not isinstance(finite_checks, dict) or not all(bool(value) for value in finite_checks.values()):
        raise ValueError(f"{label} observable finite checks failed.")


def _record_candidate_count(
    raw: dict[str, Any],
    payload: Any,
    outcomes: Any,
    label: str,
) -> int:
    candidates = raw.get("num_candidates")
    if not isinstance(candidates, int) or isinstance(candidates, bool) or candidates <= 1:
        if isinstance(payload, dict) and isinstance(payload.get("candidate_count"), int):
            candidates = payload["candidate_count"]
        elif isinstance(outcomes, list):
            candidates = len(outcomes)
    if not isinstance(candidates, int) or isinstance(candidates, bool) or candidates <= 1:
        raise ValueError(f"{label} has invalid candidate count.")
    return candidates


def _payload_scalar_vector(
    value: Any,
    candidate_count: int,
    label: str,
    source_field: str,
) -> np.ndarray | None:
    if value is None:
        return None
    array = np.asarray(value, dtype=np.float64).reshape(-1)
    if array.shape == (candidate_count,):
        return array
    original = np.asarray(value, dtype=np.float64)
    if original.ndim != 2 or original.shape[0] != candidate_count:
        raise ValueError(
            f"{label} must have shape ({candidate_count},) or "
            f"({candidate_count}, H)."
        )
    rows = [row[np.isfinite(row)] for row in original]
    if source_field in {
        "candidate_route_projection_s_m",
        "candidate_route_segment_index",
    }:
        return np.asarray(
            [float(row[-1]) if row.size else np.nan for row in rows],
            dtype=np.float64,
        )
    if source_field in {
        "candidate_route_lateral_error_m",
        "candidate_route_heading_change_rad",
    }:
        return np.asarray(
            [float(np.max(np.abs(row))) if row.size else np.nan for row in rows],
            dtype=np.float64,
        )
    if source_field == "candidate_red_stopline_distance_m":
        return np.asarray(
            [float(np.min(row)) if row.size else np.nan for row in rows],
            dtype=np.float64,
        )
    if source_field == "candidate_red_heading_alignment":
        return np.asarray(
            [float(np.mean(row)) if row.size else np.nan for row in rows],
            dtype=np.float64,
        )
    raise ValueError(f"{label} has unsupported matrix-valued source field.")


def _outcome(raw: Any, label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"{label} must be an object.")
    required = ("value", "feasible", "progress_m")
    missing = [field for field in required if field not in raw]
    if missing:
        raise ValueError(f"{label} missing {missing}.")
    value = _finite_float(raw["value"], f"{label}.value")
    progress = _finite_float(raw["progress_m"], f"{label}.progress_m")
    hard_fields = (
        "collision",
        "near_miss",
        "lane_violation",
        "red_light_violation",
    )
    hard_count = sum(int(bool(raw.get(field))) for field in hard_fields)
    return {
        "value": value,
        "feasible": bool(raw["feasible"]),
        "progress_m": progress,
        "hard_violation_count": hard_count,
    }


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") if isinstance(report, dict) else None
    if not isinstance(decision, dict):
        return {"passed": False, "status": "missing_final_decision"}
    status = decision.get("status")
    next_work = decision.get("authorized_next_work")
    passed = bool(decision.get("passed")) and status == CONTRACT_READY_STATUS and next_work == CONTRACT_NEXT_WORK
    return {
        "passed": passed,
        "status": status,
        "authorized_next_work": next_work,
    }


def _decision(
    source: dict[str, Any],
    feature_reports: list[dict[str, Any]],
    pair_reports: list[dict[str, Any]],
    *,
    formal_seed_records: int,
    class_counts: dict[str, int],
    min_beneficial_candidates: int,
    min_harmful_candidates: int,
) -> dict[str, Any]:
    promising = [row for row in _ranked_screens(feature_reports, pair_reports) if row["promising_screen"]]
    if not source["passed"]:
        status = SOURCE_BLOCKED_STATUS
        primary_gap = "matched_contract_gate_not_passed"
        next_work = "fix_matched_observable_outcome_contract_before_separability"
    elif formal_seed_records:
        status = FORMAL_SEED_STATUS
        primary_gap = "formal_seed_conflict"
        next_work = None
    elif class_counts.get(CLASS_BENEFICIAL, 0) < int(min_beneficial_candidates):
        status = REJECT_STATUS
        primary_gap = "beneficial_candidate_support_insufficient"
        next_work = "expand_matched_nonformal_label_coverage_before_selector_design"
    elif class_counts.get(CLASS_HARMFUL, 0) < int(min_harmful_candidates):
        status = REJECT_STATUS
        primary_gap = "harmful_candidate_support_insufficient"
        next_work = "expand_matched_nonformal_label_coverage_before_selector_design"
    elif promising:
        status = READY_STATUS
        primary_gap = "no_gap_promising_observable_descriptor_screen_found"
        next_work = "offline_current_tick_certificate_design_only"
    else:
        status = REJECT_STATUS
        primary_gap = "observable_descriptors_do_not_separate_beneficial_and_harmful_candidates"
        next_work = "diagnose_observable_descriptor_bottleneck_before_new_replay"
    return {
        "status": status,
        "passed": status == READY_STATUS,
        "primary_gap": primary_gap,
        "authorized_next_work": next_work,
        "promising_screen_count": len(promising),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def _failure_gap(
    feature_reports: list[dict[str, Any]],
    pair_reports: list[dict[str, Any]],
    class_counts: dict[str, int],
) -> dict[str, Any]:
    ranked = _ranked_screens(feature_reports, pair_reports)
    best = ranked[0] if ranked else None
    if class_counts.get(CLASS_BENEFICIAL, 0) < MIN_BENEFICIAL_CANDIDATES:
        primary = "beneficial_candidate_support_insufficient"
    elif class_counts.get(CLASS_HARMFUL, 0) < MIN_HARMFUL_CANDIDATES:
        primary = "harmful_candidate_support_insufficient"
    elif best is None:
        primary = "no_finite_observable_descriptor_screen"
    elif best["harmful_block_rate"] < HARMFUL_BLOCK_RATE_TARGET:
        primary = "harmful_block_rate_insufficient"
    elif best["beneficial_retain_rate"] < BENEFICIAL_RETAIN_RATE_TARGET:
        primary = "beneficial_retain_rate_insufficient"
    elif best["allowed_harmful_rate"] > ALLOWED_HARMFUL_RATE_TARGET:
        primary = "allowed_harmful_rate_too_high"
    else:
        primary = "no_gap_promising_observable_descriptor_screen_found"
    return {"primary_gap": primary, "best_screen": best}


def _class_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        cls: sum(int(row["class"] == cls) for row in rows)
        for cls in (CLASS_BENEFICIAL, CLASS_HARMFUL, CLASS_NEUTRAL)
    }


def _feature_coverage(rows: list[dict[str, Any]], feature_specs: tuple[FeatureSpec, ...]) -> dict[str, Any]:
    return {
        spec.name: _coverage(rows, spec.name)
        for spec in feature_specs
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


def _auc_for_feature(rows: list[dict[str, Any]], feature_name: str) -> dict[str, Any]:
    beneficial = np.asarray(
        [row["features"][feature_name] for row in rows if row["class"] == CLASS_BENEFICIAL and feature_name in row["features"]],
        dtype=np.float64,
    )
    harmful = np.asarray(
        [row["features"][feature_name] for row in rows if row["class"] == CLASS_HARMFUL and feature_name in row["features"]],
        dtype=np.float64,
    )
    if len(beneficial) == 0 or len(harmful) == 0:
        return {"allow_high": None, "allow_low": None}
    allow_high = _auc(beneficial, harmful)
    return {"allow_high": allow_high, "allow_low": None if allow_high is None else 1.0 - allow_high}


def _auc(positive: np.ndarray, negative: np.ndarray) -> float | None:
    if positive.size == 0 or negative.size == 0:
        return None
    total = 0.0
    count = 0
    for value in positive:
        total += float(np.sum(value > negative))
        total += 0.5 * float(np.sum(value == negative))
        count += int(negative.size)
    return total / count if count else None


def _ranked_screens(
    feature_reports: list[dict[str, Any]],
    pair_reports: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for report in feature_reports:
        best = report.get("best_screen")
        if isinstance(best, dict):
            rows.append({**best, "source": "feature"})
    for report in pair_reports:
        best = report.get("best_screen")
        if isinstance(best, dict):
            rows.append({**best, "source": "pair"})
    return sorted(rows, key=_screen_sort_key, reverse=True)


def _best_screen(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    return max(rows, key=_screen_sort_key) if rows else None


def _screen_sort_key(row: dict[str, Any] | None) -> tuple[float, float, float, float, float]:
    if not isinstance(row, dict):
        return (-1.0, -1.0, -1.0, -1.0, -1.0)
    return (
        float(bool(row.get("promising_screen"))),
        float(row.get("harmful_block_rate", 0.0)),
        float(row.get("beneficial_retain_rate", 0.0)),
        -float(row.get("allowed_harmful_rate", 1.0)),
        float(row.get("allowed_value_delta_mean") or -1e9),
    )


def _thresholds(values: np.ndarray) -> list[float]:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return []
    thresholds = np.percentile(finite, THRESHOLD_PERCENTILES)
    return sorted({float(value) for value in thresholds if np.isfinite(value)})


def _rate(numerator: Any, denominator: Any) -> float:
    denominator = int(denominator)
    return float(numerator) / denominator if denominator else 0.0


def _mean(values: np.ndarray) -> float | None:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    return None if finite.size == 0 else float(np.mean(finite))


def _record_seed(record: dict[str, Any]) -> int | None:
    for key in ("seed", "scenario_seed"):
        value = record.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    metadata = record.get("metadata")
    if isinstance(metadata, dict):
        for key in ("seed", "scenario_seed"):
            value = metadata.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                return value
    return None


def _path_seeds(path: Path) -> set[int]:
    return {
        int(match.group(1))
        for match in re.finditer(r"(?:^|[/\\])seed[_-]?(\d+)(?:[/\\]|$)", str(path))
    }


def _finite_float(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be finite.") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite.")
    return result


def _feature_payload(spec: FeatureSpec) -> dict[str, str]:
    return {
        "name": spec.name,
        "source_field": spec.source_field,
        "direction_hint": spec.direction_hint,
        "rationale": spec.rationale,
    }


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_json(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    gap = report["failure_gap"]
    lines = [
        "# DP CAMP Matched Observable Descriptor Separability",
        "",
        "This read-only audit tests whether current-tick observable descriptors "
        "can separate offline beneficial alternatives from harmful alternatives "
        "relative to DP Top-1.",
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
        "## Best Screen",
        "",
        "```json",
        json.dumps(gap.get("best_screen"), indent=2, sort_keys=True),
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
