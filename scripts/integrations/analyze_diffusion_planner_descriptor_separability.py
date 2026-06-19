#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
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
from scripts.integrations.analyze_diffusion_planner_material_atom_schema_availability import (  # noqa: E402
    _log_context,
)
from scripts.integrations.analyze_diffusion_planner_material_atom_weight_sensitivity import (  # noqa: E402
    PREDECLARED_VARIANTS,
    WeightVariant,
    _load_record,
    _scales,
    _select,
    _weights,
)
from scripts.integrations.analyze_diffusion_planner_material_weight_failure_attribution import (  # noqa: E402
    CLASS_BENEFICIAL,
    CLASS_HARMFUL,
    CLASS_NEUTRAL,
    CLASS_NON_SWITCH,
    _event,
)
from scripts.integrations.analyze_diffusion_planner_strong_progress_support_certificate import (  # noqa: E402
    REJECT_STATUS as STRONG_CERTIFICATE_REJECT_STATUS,
)
from scripts.integrations.compare_diffusion_planner_camp_replays import (  # noqa: E402
    _load_scenario_bucket_manifest,
)


READY_STATUS = "descriptor_separability_promising_for_offline_certificate_design"
REJECT_STATUS = "descriptor_separability_rejected"
SOURCE_BLOCKED_STATUS = "descriptor_separability_source_not_rejected"
FORMAL_SEED_STATUS = "descriptor_separability_formal_seed_conflict"

PROGRESS_LOSS_BUDGET_M = 0.05
HARMFUL_BLOCK_RATE_TARGET = 0.75
BENEFICIAL_RETAIN_RATE_TARGET = 0.75
HARD_NONWORSE_RATE_TARGET = 0.99
SEPARABILITY_AUC_TARGET = 0.70
EPS = 1e-12

THRESHOLD_PERCENTILES = (0.0, 5.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 95.0, 100.0)

BLOCKED_ACTIONS = (
    "closed_loop_smoke_authorized",
    "online_selector_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
)


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    direction: str
    rationale: str


FEATURE_SPECS: tuple[FeatureSpec, ...] = (
    FeatureSpec("progress_loss_m", "block_high", "planned route progress or step reach loss"),
    FeatureSpec("first_step_loss_m", "block_high", "PerfectTracker first-step reach loss"),
    FeatureSpec("speed_loss_mps", "block_high", "target or tail speed loss"),
    FeatureSpec("jerk_worse_mps3", "block_high", "tracker jerk regression"),
    FeatureSpec("lateral_worse_mps2", "block_high", "tracker lateral acceleration regression"),
    FeatureSpec("yaw_worse_rps", "block_high", "tracker yaw-rate regression"),
    FeatureSpec("absolute_lateral_mps2", "block_high", "absolute tracker lateral acceleration"),
    FeatureSpec("top1_shape_gain", "block_high", "improvement toward DP Top-1 shape"),
    FeatureSpec("traffic_gain", "block_low", "planned traffic-rule exposure reduction"),
    FeatureSpec("traffic_remaining", "block_high", "candidate planned traffic-rule exposure"),
    FeatureSpec("comfort_gain", "block_low", "tracker comfort improvement"),
)

PAIR_SPECS: tuple[tuple[str, str], ...] = (
    ("progress_loss_m", "traffic_gain"),
    ("progress_loss_m", "top1_shape_gain"),
    ("progress_loss_m", "lateral_worse_mps2"),
    ("progress_loss_m", "speed_loss_mps"),
    ("traffic_gain", "top1_shape_gain"),
    ("traffic_gain", "comfort_gain"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline no-leak descriptor separability audit for harmful vs "
            "beneficial switches proposed by rejected DP-CAMP material weights."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--scenario_bucket_manifest", type=Path, default=None)
    parser.add_argument("--strong_certificate_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--scale_percentile", type=float, default=95.0)
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
        strong_certificate_report=_load_json(args.strong_certificate_json),
        scenario_bucket_manifest=args.scenario_bucket_manifest,
        label=args.label,
        scale_percentile=args.scale_percentile,
        fail_on_formal_seeds=args.fail_on_formal_seeds,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")


def analyze(
    paths: list[Path],
    *,
    strong_certificate_report: dict[str, Any],
    scenario_bucket_manifest: Path | None = None,
    label: str | None = None,
    scale_percentile: float = 95.0,
    fail_on_formal_seeds: bool = False,
) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    manifest = _load_scenario_bucket_manifest(scenario_bucket_manifest)
    items: list[dict[str, Any]] = []
    for log_path in log_paths:
        context = _log_context(log_path, manifest)
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for index, raw in enumerate(payload):
            if not isinstance(raw, dict):
                raise ValueError(f"{log_path} record {index} must be an object.")
            items.append({"raw": raw, "context": {**context, "record_index": index}})
    return analyze_records(
        items,
        strong_certificate_report=strong_certificate_report,
        label=label,
        scenario_bucket_manifest=(
            None if scenario_bucket_manifest is None else str(scenario_bucket_manifest)
        ),
        scale_percentile=scale_percentile,
        fail_on_formal_seeds=fail_on_formal_seeds,
    )


def analyze_records(
    items: list[dict[str, Any]],
    *,
    strong_certificate_report: dict[str, Any],
    label: str | None = None,
    scenario_bucket_manifest: str | None = None,
    scale_percentile: float = 95.0,
    fail_on_formal_seeds: bool = False,
    variants: tuple[WeightVariant, ...] = PREDECLARED_VARIANTS,
    feature_specs: tuple[FeatureSpec, ...] = FEATURE_SPECS,
    pair_specs: tuple[tuple[str, str], ...] = PAIR_SPECS,
    progress_loss_budget_m: float = PROGRESS_LOSS_BUDGET_M,
    harmful_block_rate_target: float = HARMFUL_BLOCK_RATE_TARGET,
    beneficial_retain_rate_target: float = BENEFICIAL_RETAIN_RATE_TARGET,
    hard_nonworse_rate_target: float = HARD_NONWORSE_RATE_TARGET,
    separability_auc_target: float = SEPARABILITY_AUC_TARGET,
) -> dict[str, Any]:
    if not items:
        raise ValueError("At least one selection record is required.")
    source = _source_gate(strong_certificate_report)
    records: list[dict[str, Any]] = []
    descriptors: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        records.append(_load_record(item["raw"], item["context"], f"record {index}"))
        descriptors.append(_descriptor_record(item["raw"], item["context"], f"record {index}"))
    formal_seed_records = sum(int(record["context"]["formal_seed"]) for record in records)
    if fail_on_formal_seeds and formal_seed_records:
        raise ValueError("Formal seed records are forbidden.")
    scales = _scales(records, scale_percentile)
    variant_reports = [
        _variant_report(
            variant,
            records,
            descriptors,
            scales,
            feature_specs=feature_specs,
            pair_specs=pair_specs,
            progress_loss_budget_m=progress_loss_budget_m,
            harmful_block_rate_target=harmful_block_rate_target,
            beneficial_retain_rate_target=beneficial_retain_rate_target,
            hard_nonworse_rate_target=hard_nonworse_rate_target,
            separability_auc_target=separability_auc_target,
        )
        for variant in variants
    ]
    decision = _decision(source, variant_reports, formal_seed_records=formal_seed_records)
    return {
        "analysis": {
            "name": "dp_camp_descriptor_separability_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_labels_used_for_descriptors": False,
            "future_outcome_labels_used_for_thresholds": True,
            "future_outcome_labels_used_for_evaluation": True,
            "thresholds_are_offline_oracle_diagnostics": True,
            "scenario_bucket_manifest": scenario_bucket_manifest,
            "feature_specs": [_feature_payload(spec) for spec in feature_specs],
            "pair_specs": [list(pair) for pair in pair_specs],
            "accept_criteria": {
                "harmful_block_rate": f">= {harmful_block_rate_target}",
                "beneficial_retain_rate": f">= {beneficial_retain_rate_target}",
                "allowed_safety_delta_mean": "<= 0",
                "allowed_progress_delta_mean": f">= -{progress_loss_budget_m}",
                "final_hard_nonworse_rate": f">= {hard_nonworse_rate_target}",
                "feature_auc": f">= {separability_auc_target} for descriptor-level evidence",
            },
            "math_boundary": (
                "DP remains a frozen black-box candidate generator. Descriptors "
                "are fixed current-tick finite-candidate quantities computed "
                "before any closed-loop outcome label is consulted. Fixed CAMP "
                "material weights still define affine scores score_k(w)=a_k^T w "
                "over fixed atoms. The simplex/CVaR/L2 robust master convexity "
                "boundary is unchanged. Thresholds in this report are offline "
                "oracle diagnostics for separability only; they are not online "
                "selector parameters, not training labels, and not a DP-side "
                "classical Benders decomposition, dual, or valid cut."
            ),
            "formal_seed_policy": "forbidden" if fail_on_formal_seeds else "reported_only",
        },
        "source_strong_certificate_gate": source,
        "records": _record_summary(records, formal_seed_records),
        "descriptor_coverage": _descriptor_coverage(descriptors),
        "variants": variant_reports,
        "ranked_feature_screens": _rank_feature_screens(variant_reports),
        "ranked_pair_screens": _rank_pair_screens(variant_reports),
        "failure_gap": _failure_gap(variant_reports),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": decision,
    }


def _variant_report(
    variant: WeightVariant,
    records: list[dict[str, Any]],
    descriptors: list[dict[str, Any]],
    scales: dict[str, float],
    *,
    feature_specs: tuple[FeatureSpec, ...],
    pair_specs: tuple[tuple[str, str], ...],
    progress_loss_budget_m: float,
    harmful_block_rate_target: float,
    beneficial_retain_rate_target: float,
    hard_nonworse_rate_target: float,
    separability_auc_target: float,
) -> dict[str, Any]:
    weights = _weights(variant)
    events = [
        {
            **_event(
                record,
                _select(record, weights, scales),
                weights,
                scales,
                progress_loss_budget_m=progress_loss_budget_m,
            ),
            "record_index": index,
        }
        for index, record in enumerate(records)
    ]
    changed = [event for event in events if event["changed"]]
    feature_reports = [
        _feature_report(
            spec,
            changed,
            descriptors,
            progress_loss_budget_m=progress_loss_budget_m,
            harmful_block_rate_target=harmful_block_rate_target,
            beneficial_retain_rate_target=beneficial_retain_rate_target,
            hard_nonworse_rate_target=hard_nonworse_rate_target,
            separability_auc_target=separability_auc_target,
        )
        for spec in feature_specs
    ]
    feature_by_name = {report["feature"]: report for report in feature_reports}
    pair_reports = [
        _pair_report(
            pair,
            feature_by_name,
            changed,
            descriptors,
            progress_loss_budget_m=progress_loss_budget_m,
            harmful_block_rate_target=harmful_block_rate_target,
            beneficial_retain_rate_target=beneficial_retain_rate_target,
            hard_nonworse_rate_target=hard_nonworse_rate_target,
        )
        for pair in pair_specs
        if pair[0] in feature_by_name and pair[1] in feature_by_name
    ]
    return {
        "name": variant.name,
        "changed_switches": len(changed),
        "classification_counts": _class_counts(events),
        "feature_reports": feature_reports,
        "pair_reports": pair_reports,
        "best_feature_screen": _best_screen(
            [screen for report in feature_reports for screen in report["threshold_screens"]]
        ),
        "best_pair_screen": _best_screen(
            [screen for report in pair_reports for screen in report["threshold_screens"]]
        ),
        "scenario_bucket_breakdown": _bucket_breakdown(changed),
    }


def _feature_report(
    spec: FeatureSpec,
    changed: list[dict[str, Any]],
    descriptors: list[dict[str, Any]],
    *,
    progress_loss_budget_m: float,
    harmful_block_rate_target: float,
    beneficial_retain_rate_target: float,
    hard_nonworse_rate_target: float,
    separability_auc_target: float,
) -> dict[str, Any]:
    values = _feature_values_for_events(spec.name, changed, descriptors)
    harmful_values = values[_class_mask(changed, CLASS_HARMFUL)]
    beneficial_values = values[_class_mask(changed, CLASS_BENEFICIAL)]
    oriented = _oriented_values(values, spec.direction)
    oriented_harmful = oriented[_class_mask(changed, CLASS_HARMFUL)]
    oriented_beneficial = oriented[_class_mask(changed, CLASS_BENEFICIAL)]
    auc = _auc(oriented_harmful, oriented_beneficial)
    screens = [
        _screen_row(
            changed,
            values,
            _allow_mask(values, spec.direction, threshold),
            screen_name=f"{spec.name}:{spec.direction}:{threshold:.12g}",
            feature=spec.name,
            direction=spec.direction,
            threshold=float(threshold),
            progress_loss_budget_m=progress_loss_budget_m,
            harmful_block_rate_target=harmful_block_rate_target,
            beneficial_retain_rate_target=beneficial_retain_rate_target,
            hard_nonworse_rate_target=hard_nonworse_rate_target,
        )
        for threshold in _thresholds(values)
    ]
    return {
        "feature": spec.name,
        "direction": spec.direction,
        "rationale": spec.rationale,
        "auc_harmful_vs_beneficial": auc,
        "meets_auc_target": bool(auc is not None and auc >= separability_auc_target),
        "harmful_distribution": _summary(harmful_values),
        "beneficial_distribution": _summary(beneficial_values),
        "neutral_distribution": _summary(values[_class_mask(changed, CLASS_NEUTRAL)]),
        "threshold_screens": screens,
        "best_screen": _best_screen(screens),
    }


def _pair_report(
    pair: tuple[str, str],
    feature_by_name: dict[str, dict[str, Any]],
    changed: list[dict[str, Any]],
    descriptors: list[dict[str, Any]],
    *,
    progress_loss_budget_m: float,
    harmful_block_rate_target: float,
    beneficial_retain_rate_target: float,
    hard_nonworse_rate_target: float,
) -> dict[str, Any]:
    left = feature_by_name[pair[0]]
    right = feature_by_name[pair[1]]
    left_values = _feature_values_for_events(pair[0], changed, descriptors)
    right_values = _feature_values_for_events(pair[1], changed, descriptors)
    screens = []
    for left_threshold in _thresholds(left_values):
        left_mask = _allow_mask(left_values, left["direction"], left_threshold)
        for right_threshold in _thresholds(right_values):
            right_mask = _allow_mask(right_values, right["direction"], right_threshold)
            screens.append(
                _screen_row(
                    changed,
                    np.maximum(left_values, right_values),
                    left_mask & right_mask,
                    screen_name=(
                        f"{pair[0]}:{left['direction']}:{left_threshold:.12g}+"
                        f"{pair[1]}:{right['direction']}:{right_threshold:.12g}"
                    ),
                    feature="+".join(pair),
                    direction="pair_and",
                    threshold=None,
                    progress_loss_budget_m=progress_loss_budget_m,
                    harmful_block_rate_target=harmful_block_rate_target,
                    beneficial_retain_rate_target=beneficial_retain_rate_target,
                    hard_nonworse_rate_target=hard_nonworse_rate_target,
                    extra={
                        "left_feature": pair[0],
                        "left_direction": left["direction"],
                        "left_threshold": float(left_threshold),
                        "right_feature": pair[1],
                        "right_direction": right["direction"],
                        "right_threshold": float(right_threshold),
                    },
                )
            )
    return {
        "features": list(pair),
        "threshold_screens": screens,
        "best_screen": _best_screen(screens),
    }


def _screen_row(
    changed: list[dict[str, Any]],
    values: np.ndarray,
    allow_mask: np.ndarray,
    *,
    screen_name: str,
    feature: str,
    direction: str,
    threshold: float | None,
    progress_loss_budget_m: float,
    harmful_block_rate_target: float,
    beneficial_retain_rate_target: float,
    hard_nonworse_rate_target: float,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    harmful_mask = _class_mask(changed, CLASS_HARMFUL)
    beneficial_mask = _class_mask(changed, CLASS_BENEFICIAL)
    harmful_count = int(np.sum(harmful_mask))
    beneficial_count = int(np.sum(beneficial_mask))
    allowed_harmful = int(np.sum(allow_mask & harmful_mask))
    allowed_beneficial = int(np.sum(allow_mask & beneficial_mask))
    harmful_block_rate = 1.0 - allowed_harmful / max(harmful_count, 1)
    beneficial_retain_rate = allowed_beneficial / max(beneficial_count, 1)
    allowed_events = [event for event, allowed in zip(changed, allow_mask) if allowed]
    final_events = [
        event
        if allowed
        else {**event, "safety_delta": 0.0, "progress_delta": 0.0, "hard_worse": False}
        for event, allowed in zip(changed, allow_mask)
    ]
    allowed_safety_mean = _mean([event["safety_delta"] for event in allowed_events])
    allowed_progress_mean = _mean([event["progress_delta"] for event in allowed_events])
    final_hard_nonworse_rate = _hard_nonworse_rate(final_events)
    promising = bool(
        harmful_count
        and beneficial_count
        and harmful_block_rate >= harmful_block_rate_target
        and beneficial_retain_rate >= beneficial_retain_rate_target
        and (allowed_safety_mean is not None and allowed_safety_mean <= 0.0)
        and (
            allowed_progress_mean is not None
            and allowed_progress_mean >= -float(progress_loss_budget_m)
        )
        and final_hard_nonworse_rate >= hard_nonworse_rate_target
    )
    row = {
        "screen_name": screen_name,
        "feature": feature,
        "direction": direction,
        "threshold": threshold,
        "changed_switches": len(changed),
        "allowed_switches": int(np.sum(allow_mask)),
        "blocked_switches": int(len(changed) - np.sum(allow_mask)),
        "harmful_switches": harmful_count,
        "beneficial_switches": beneficial_count,
        "allowed_harmful_switches": allowed_harmful,
        "allowed_beneficial_switches": allowed_beneficial,
        "harmful_block_rate": harmful_block_rate,
        "beneficial_retain_rate": beneficial_retain_rate,
        "allowed_safety_delta_mean": allowed_safety_mean,
        "allowed_progress_delta_mean": allowed_progress_mean,
        "final_safety_delta_mean": _mean([event["safety_delta"] for event in final_events]),
        "final_progress_delta_mean": _mean([event["progress_delta"] for event in final_events]),
        "final_hard_nonworse_rate": final_hard_nonworse_rate,
        "promising_descriptor_screen": promising,
        "allowed_feature_distribution": _summary(values[allow_mask]),
        "blocked_feature_distribution": _summary(values[~allow_mask]),
    }
    if extra:
        row.update(extra)
    return row


def _descriptor_record(raw: dict[str, Any], context: dict[str, Any], label: str) -> dict[str, Any]:
    candidate_count = int(raw.get("num_candidates", 0))
    if candidate_count <= 0:
        raise ValueError(f"{label} must declare positive num_candidates.")
    selected = int(raw.get("selected_index"))
    if selected < 0 or selected >= candidate_count:
        raise ValueError(f"{label} selected_index is out of range.")
    progress = _first_present_vector(
        raw,
        candidate_count,
        label,
        ("candidate_route_progress", "candidate_step_reach"),
        nonnegative=False,
    )
    first_step = _loss_vector(
        raw,
        candidate_count,
        selected,
        label,
        ("candidate_perfect_tracker_first_step_reach_m",),
        higher_is_better=True,
    )
    target_speed = _loss_vector(
        raw,
        candidate_count,
        selected,
        label,
        ("candidate_perfect_tracker_target_speed_mps",),
        higher_is_better=True,
    )
    tail_speed = _loss_vector(
        raw,
        candidate_count,
        selected,
        label,
        ("candidate_perfect_tracker_tail_average_speed_mps",),
        higher_is_better=True,
    )
    jerk_worse, jerk_gain = _worse_and_gain(
        raw,
        candidate_count,
        selected,
        label,
        "candidate_perfect_tracker_jerk_magnitude_mps3",
    )
    lateral_worse, lateral_gain = _worse_and_gain(
        raw,
        candidate_count,
        selected,
        label,
        "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2",
    )
    yaw_worse, yaw_gain = _worse_and_gain(
        raw,
        candidate_count,
        selected,
        label,
        "candidate_perfect_tracker_yaw_rate_magnitude_rps",
    )
    dp_prior = _optional_vector(
        raw,
        candidate_count,
        label,
        "candidate_dp_prior_deviation_cost",
        nonnegative=True,
    )
    traffic = _traffic_exposure(raw, candidate_count, label)
    progress_loss = None
    if progress is not None:
        progress_loss = np.maximum(float(progress[selected]) - progress, 0.0)
    speed_loss = _component_max_optional([target_speed, tail_speed])
    comfort_gain = _component_max_optional([jerk_gain, lateral_gain, yaw_gain])
    return {
        "context": context,
        "candidate_count": candidate_count,
        "selected_index": selected,
        "values": {
            "progress_loss_m": progress_loss,
            "first_step_loss_m": first_step,
            "speed_loss_mps": speed_loss,
            "jerk_worse_mps3": jerk_worse,
            "lateral_worse_mps2": lateral_worse,
            "yaw_worse_rps": yaw_worse,
            "absolute_lateral_mps2": _optional_vector(
                raw,
                candidate_count,
                label,
                "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2",
                nonnegative=True,
            ),
            "top1_shape_gain": (
                None
                if dp_prior is None
                else np.maximum(float(dp_prior[selected]) - dp_prior, 0.0)
            ),
            "traffic_gain": (
                None
                if traffic is None
                else np.maximum(float(traffic[selected]) - traffic, 0.0)
            ),
            "traffic_remaining": traffic,
            "comfort_gain": comfort_gain,
        },
    }


def _feature_values_for_events(
    feature: str,
    events: list[dict[str, Any]],
    descriptors: list[dict[str, Any]],
) -> np.ndarray:
    values: list[float] = []
    for event in events:
        descriptor = descriptors[int(event["record_index"])]
        vector = descriptor["values"].get(feature)
        if vector is None:
            values.append(np.inf)
        else:
            values.append(float(vector[int(event["chosen"])]))
    return np.asarray(values, dtype=np.float64)


def _allow_mask(values: np.ndarray, direction: str, threshold: float) -> np.ndarray:
    finite = np.isfinite(values)
    if direction == "block_high":
        return finite & (values <= float(threshold) + EPS)
    if direction == "block_low":
        return finite & (values >= float(threshold) - EPS)
    raise ValueError(f"Unsupported feature direction: {direction}")


def _oriented_values(values: np.ndarray, direction: str) -> np.ndarray:
    if direction == "block_high":
        return values
    if direction == "block_low":
        return -values
    raise ValueError(f"Unsupported feature direction: {direction}")


def _thresholds(values: np.ndarray) -> np.ndarray:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return np.asarray([0.0], dtype=np.float64)
    raw = np.percentile(finite, THRESHOLD_PERCENTILES)
    return np.unique(np.asarray(raw, dtype=np.float64))


def _first_present_vector(
    raw: dict[str, Any],
    size: int,
    label: str,
    keys: tuple[str, ...],
    *,
    nonnegative: bool,
) -> np.ndarray | None:
    for key in keys:
        values = _optional_vector(raw, size, label, key, nonnegative=nonnegative)
        if values is not None:
            return values
    return None


def _loss_vector(
    raw: dict[str, Any],
    size: int,
    selected: int,
    label: str,
    keys: tuple[str, ...],
    *,
    higher_is_better: bool,
) -> np.ndarray | None:
    values = _first_present_vector(raw, size, label, keys, nonnegative=True)
    if values is None:
        return None
    selected_value = float(values[selected])
    if higher_is_better:
        return np.maximum(selected_value - values, 0.0)
    return np.maximum(values - selected_value, 0.0)


def _worse_and_gain(
    raw: dict[str, Any],
    size: int,
    selected: int,
    label: str,
    key: str,
) -> tuple[np.ndarray | None, np.ndarray | None]:
    values = _optional_vector(raw, size, label, key, nonnegative=True)
    if values is None:
        return None, None
    selected_value = float(values[selected])
    return (
        np.maximum(values - selected_value, 0.0),
        np.maximum(selected_value - values, 0.0),
    )


def _traffic_exposure(raw: dict[str, Any], size: int, label: str) -> np.ndarray | None:
    vectors = []
    for key in (
        "candidate_horizon_union_planned_red_light_cost",
        "candidate_full_horizon_planned_red_light_cost",
        "candidate_red_stopping_margin_cost",
        "candidate_planned_red_light_cost",
        "candidate_horizon_planned_red_light_cost",
        "candidate_red_light_cost",
    ):
        values = _optional_vector(raw, size, label, key, nonnegative=True)
        if values is not None:
            vectors.append(values)
    return _component_max_optional(vectors)


def _optional_vector(
    raw: dict[str, Any],
    size: int,
    label: str,
    key: str,
    *,
    nonnegative: bool,
) -> np.ndarray | None:
    if key not in raw or raw.get(key) is None:
        return None
    values = np.asarray(raw[key], dtype=np.float64).reshape(-1)
    if values.shape != (size,):
        raise ValueError(f"{label} {key} must have shape [{size}].")
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{label} {key} must contain finite values.")
    if nonnegative and np.any(values < -EPS):
        raise ValueError(f"{label} {key} must be nonnegative.")
    return values


def _component_max_optional(vectors: list[np.ndarray | None]) -> np.ndarray | None:
    present = [vector for vector in vectors if vector is not None]
    if not present:
        return None
    return np.max(np.vstack(present), axis=0)


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    status = decision.get("status")
    return {
        "status": status,
        "passed": status == STRONG_CERTIFICATE_REJECT_STATUS,
        "authorized_next_work": decision.get("authorized_next_work"),
        "records": (report.get("records") or {}).get("total"),
        "candidate_rows": (report.get("records") or {}).get("candidate_rows"),
        "primary_gap": (report.get("failure_gap") or {}).get("primary_gap"),
    }


def _decision(
    source: dict[str, Any],
    variants: list[dict[str, Any]],
    *,
    formal_seed_records: int,
) -> dict[str, Any]:
    promising = [
        row
        for row in [*_rank_feature_screens(variants), *_rank_pair_screens(variants)]
        if row["promising_descriptor_screen"]
    ]
    if not source["passed"]:
        status = SOURCE_BLOCKED_STATUS
        next_step = "Do not run descriptor separability unless the strong certificate gate was rejected."
    elif formal_seed_records:
        status = FORMAL_SEED_STATUS
        next_step = "Exclude formal seeds before using descriptor separability evidence."
    elif promising:
        status = READY_STATUS
        next_step = (
            "Design only an offline no-leak conditional certificate around the "
            "promising separability rows. Replay, formal seeds, online selector "
            "promotion, and retraining remain blocked."
        )
    else:
        status = REJECT_STATUS
        next_step = (
            "Reject threshold tuning over the audited descriptors. The next gate "
            "should redesign the atom schema or add a new current-tick descriptor "
            "with better harmful/beneficial separability."
        )
    return {
        "status": status,
        "promising_screens": promising[:20],
        "closed_loop_smoke_authorized": False,
        "online_selector_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "authorized_next_work": (
            "offline_conditional_certificate_design_only"
            if status == READY_STATUS
            else None
        ),
        "next_step": next_step,
    }


def _failure_gap(variants: list[dict[str, Any]]) -> dict[str, Any]:
    feature_rows = _rank_feature_screens(variants)
    pair_rows = _rank_pair_screens(variants)
    all_rows = [*feature_rows, *pair_rows]
    best = all_rows[0] if all_rows else None
    best_auc = _best_auc(variants)
    if best is None:
        primary = "no_screen_rows"
    elif best["promising_descriptor_screen"]:
        primary = "no_gap_promising_descriptor_screen_found"
    elif best["beneficial_retain_rate"] < BENEFICIAL_RETAIN_RATE_TARGET:
        primary = "beneficial_and_harmful_descriptor_overlap"
    elif best["harmful_block_rate"] < HARMFUL_BLOCK_RATE_TARGET:
        primary = "descriptor_too_permissive_for_harmful_switches"
    elif (best["allowed_safety_delta_mean"] is None) or best["allowed_safety_delta_mean"] > 0.0:
        primary = "allowed_switches_remain_safety_negative"
    elif (
        best["allowed_progress_delta_mean"] is None
        or best["allowed_progress_delta_mean"] < -PROGRESS_LOSS_BUDGET_M
    ):
        primary = "allowed_switches_remain_progress_negative"
    else:
        primary = "unclassified_separability_gap"
    return {
        "primary_gap": primary,
        "best_auc": best_auc,
        "best_screen": _screen_digest(best),
    }


def _best_auc(variants: list[dict[str, Any]]) -> dict[str, Any] | None:
    rows = []
    for variant in variants:
        for report in variant["feature_reports"]:
            auc = report["auc_harmful_vs_beneficial"]
            if auc is not None:
                rows.append(
                    {
                        "variant": variant["name"],
                        "feature": report["feature"],
                        "direction": report["direction"],
                        "auc_harmful_vs_beneficial": auc,
                    }
                )
    if not rows:
        return None
    return sorted(rows, key=lambda row: -float(row["auc_harmful_vs_beneficial"]))[0]


def _rank_feature_screens(variants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for variant in variants:
        for report in variant["feature_reports"]:
            for screen in report["threshold_screens"]:
                rows.append({"variant": variant["name"], **screen})
    return _rank_screens(rows)


def _rank_pair_screens(variants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for variant in variants:
        for report in variant["pair_reports"]:
            for screen in report["threshold_screens"]:
                rows.append({"variant": variant["name"], **screen})
    return _rank_screens(rows)


def _rank_screens(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            not row["promising_descriptor_screen"],
            -float(row["harmful_block_rate"]),
            -float(row["beneficial_retain_rate"]),
            float(row["allowed_safety_delta_mean"] or 0.0),
            float(row["allowed_progress_delta_mean"] or 0.0),
        ),
    )


def _best_screen(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    ranked = _rank_screens(rows)
    return ranked[0] if ranked else None


def _screen_digest(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    keys = (
        "variant",
        "screen_name",
        "feature",
        "direction",
        "threshold",
        "harmful_block_rate",
        "beneficial_retain_rate",
        "allowed_safety_delta_mean",
        "allowed_progress_delta_mean",
        "final_hard_nonworse_rate",
        "promising_descriptor_screen",
    )
    return {key: row.get(key) for key in keys}


def _record_summary(records: list[dict[str, Any]], formal_seed_records: int) -> dict[str, Any]:
    return {
        "logs": len({record["context"].get("log_path") for record in records}),
        "total": len(records),
        "candidate_rows": int(sum(record["candidate_count"] for record in records)),
        "candidate_count_values": sorted({record["candidate_count"] for record in records}),
        "formal_seed_records": int(formal_seed_records),
    }


def _descriptor_coverage(descriptors: list[dict[str, Any]]) -> dict[str, Any]:
    if not descriptors:
        return {}
    keys = sorted(descriptors[0]["values"])
    total = len(descriptors)
    candidate_rows = int(sum(row["candidate_count"] for row in descriptors))
    return {
        key: {
            "records_available": int(sum(row["values"].get(key) is not None for row in descriptors)),
            "records_total": total,
            "candidate_rows_available": int(
                sum(
                    row["candidate_count"]
                    for row in descriptors
                    if row["values"].get(key) is not None
                )
            ),
            "candidate_rows_total": candidate_rows,
        }
        for key in keys
    }


def _class_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    return {
        CLASS_HARMFUL: sum(int(event["class"] == CLASS_HARMFUL) for event in events),
        CLASS_BENEFICIAL: sum(int(event["class"] == CLASS_BENEFICIAL) for event in events),
        CLASS_NEUTRAL: sum(int(event["class"] == CLASS_NEUTRAL) for event in events),
        CLASS_NON_SWITCH: sum(int(event["class"] == CLASS_NON_SWITCH) for event in events),
    }


def _bucket_breakdown(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        for bucket in event["context"].get("scenario_buckets", ["overall"]):
            grouped.setdefault(bucket, []).append(event)
    rows = []
    for bucket, bucket_events in sorted(grouped.items()):
        counts = _class_counts(bucket_events)
        rows.append(
            {
                "bucket": bucket,
                "events": len(bucket_events),
                "classification_counts": counts,
                "harmful_rate": counts[CLASS_HARMFUL] / max(len(bucket_events), 1),
                "beneficial_rate": counts[CLASS_BENEFICIAL] / max(len(bucket_events), 1),
            }
        )
    return rows


def _class_mask(events: list[dict[str, Any]], class_name: str) -> np.ndarray:
    return np.asarray([event["class"] == class_name for event in events], dtype=bool)


def _hard_nonworse_rate(events: list[dict[str, Any]]) -> float:
    if not events:
        return 1.0
    return float(np.mean([not bool(event.get("hard_worse")) for event in events]))


def _auc(positive: np.ndarray, negative: np.ndarray) -> float | None:
    pos = np.asarray(positive, dtype=np.float64)
    neg = np.asarray(negative, dtype=np.float64)
    pos = pos[np.isfinite(pos)]
    neg = neg[np.isfinite(neg)]
    if pos.size == 0 or neg.size == 0:
        return None
    values = np.concatenate([pos, neg])
    labels = np.concatenate(
        [np.ones(pos.size, dtype=bool), np.zeros(neg.size, dtype=bool)]
    )
    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]
    ranks = np.empty(values.size, dtype=np.float64)
    start = 0
    while start < values.size:
        end = start + 1
        while end < values.size and sorted_values[end] == sorted_values[start]:
            end += 1
        avg_rank = (start + 1 + end) / 2.0
        ranks[order[start:end]] = avg_rank
        start = end
    pos_rank_sum = float(np.sum(ranks[labels]))
    auc = (pos_rank_sum - pos.size * (pos.size + 1) / 2.0) / (pos.size * neg.size)
    return float(auc)


def _mean(values: list[float]) -> float | None:
    return None if not values else float(np.mean(np.asarray(values, dtype=np.float64)))


def _summary(values: Any) -> dict[str, Any]:
    arr = np.asarray(values, dtype=np.float64).reshape(-1)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return {"n": 0, "mean": None, "min": None, "p10": None, "p50": None, "p90": None, "max": None}
    return {
        "n": int(finite.size),
        "mean": float(np.mean(finite)),
        "min": float(np.min(finite)),
        "p10": float(np.percentile(finite, 10.0)),
        "p50": float(np.percentile(finite, 50.0)),
        "p90": float(np.percentile(finite, 90.0)),
        "max": float(np.max(finite)),
    }


def _feature_payload(spec: FeatureSpec) -> dict[str, str]:
    return {
        "name": spec.name,
        "direction": spec.direction,
        "rationale": spec.rationale,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    gap = report["failure_gap"]
    lines = [
        "# Descriptor Separability Audit",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Decision: `{decision['status']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Primary gap: `{gap['primary_gap']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "## Records",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| `logs` | `{report['records']['logs']}` |",
        f"| `total` | `{report['records']['total']}` |",
        f"| `candidate_rows` | `{report['records']['candidate_rows']}` |",
        f"| `formal_seed_records` | `{report['records']['formal_seed_records']}` |",
        "",
        "## Best Feature Screens",
        "",
        "| Variant | Feature | Direction | Threshold | Promising | Harmful Block | Beneficial Retain | Allowed Safety Mean | Allowed Progress Mean |",
        "| --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in report["ranked_feature_screens"][:20]:
        lines.append(_screen_markdown_row(row, include_threshold=True))
    lines.extend(
        [
            "",
            "## Best Pair Screens",
            "",
            "| Variant | Feature | Direction | Threshold | Promising | Harmful Block | Beneficial Retain | Allowed Safety Mean | Allowed Progress Mean |",
            "| --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in report["ranked_pair_screens"][:20]:
        lines.append(_screen_markdown_row(row, include_threshold=False))
    lines.extend(
        [
            "",
            "This is an offline separability audit only. It does not train "
            "weights, change online selection, run replay, modify DP, or "
            "authorize formal seeds.",
            "",
        ]
    )
    return "\n".join(lines)


def _screen_markdown_row(row: dict[str, Any], *, include_threshold: bool) -> str:
    threshold = row.get("threshold") if include_threshold else None
    threshold_text = _fmt(threshold) if threshold is not None else "`see_json`"
    return (
        f"| `{row['variant']}` | `{row['feature']}` | `{row['direction']}` | "
        f"{threshold_text} | `{row['promising_descriptor_screen']}` | "
        f"{_fmt(row['harmful_block_rate'])} | "
        f"{_fmt(row['beneficial_retain_rate'])} | "
        f"{_fmt(row['allowed_safety_delta_mean'])} | "
        f"{_fmt(row['allowed_progress_delta_mean'])} |"
    )


def _fmt(value: Any) -> str:
    if value is None:
        return "`n/a`"
    try:
        result = float(value)
    except (TypeError, ValueError):
        return "`n/a`"
    if not np.isfinite(result):
        return "`n/a`"
    return f"`{result:.6g}`"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
