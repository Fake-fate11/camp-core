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


HORIZONS = (3, 5, 10)
SAFETY_DETAIL_HORIZON = 3
PROGRESS_LOSS_BUDGETS_M = (0.5, 1.0, 1.5)
H3_DISTANCE_LOSS_BUDGETS_M = (0.05, 0.1)
H3_MAX_LATERAL_GUARD_MPS2 = 2.0
ROLLOUT_METRICS = (
    "distance_m",
    "mean_vector_jerk_mps3",
    "mean_lateral_acceleration_mps2",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Screen outcome-free full-red and fixed-candidate PerfectTracker "
            "rollout shadows before implementing an online selector."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def analyze(paths: list[Path]) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")

    total_records = 0
    fallback_records = 0
    nonfallback_records = 0
    candidate_count = 0
    short_safe_full_red_candidates = 0
    short_red_full_safe_candidates = 0
    selected_short_safe_full_red_records = 0
    selected_full_red_records = 0
    selected_short_safe_full_red_events: list[dict[str, Any]] = []
    selected_short_safe_full_red_breakdown = {
        "fallback": 0,
        "nonfallback": 0,
        "with_lower_union_red_feasible_candidate": 0,
        "without_lower_union_red_feasible_candidate": 0,
        "fallback_with_lower_union_red_feasible_candidate": 0,
        "nonfallback_with_lower_union_red_feasible_candidate": 0,
    }
    budget_rows = {
        (progress_budget, distance_budget): []
        for progress_budget in PROGRESS_LOSS_BUDGETS_M
        for distance_budget in H3_DISTANCE_LOSS_BUDGETS_M
    }
    budget_candidate_counts = {
        key: []
        for key in budget_rows
    }
    horizon_rows = {
        horizon: {
            "rollout_pareto": [],
            "command_and_rollout_pareto": [],
            "red_improving_progress_distance": [],
            "red_improving_rollout_pareto": [],
            "red_minimum_best_progress": [],
            "eligible_candidates": [],
            "strict_eligible_candidates": [],
            "red_improving_candidates": [],
            "red_improving_pareto_candidates": [],
            "red_minimum_candidates": [],
        }
        for horizon in HORIZONS
    }
    correlations = {
        horizon: {
            "command_jerk": [],
            "command_lateral": [],
            "rollout_jerk": [],
            "rollout_lateral": [],
        }
        for horizon in HORIZONS
    }

    for log_path in log_paths:
        log_context = _load_log_context(log_path)
        records = json.loads(log_path.read_text(encoding="utf-8"))
        if not isinstance(records, list) or not records:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for record_index, record in enumerate(records):
            label = f"{log_path} record {record_index}"
            total_records += 1
            selected = int(record["selected_index"])
            feasible = np.asarray(record["feasible_mask"], dtype=bool).reshape(-1)
            count = feasible.size
            if count < 1 or not 0 <= selected < count:
                raise ValueError(f"{label} has invalid candidate selection.")
            candidate_count += count

            progress, short_red = _reward_metrics(record, count, label)
            full_red = _vector(
                record.get("candidate_full_horizon_planned_red_light_cost"),
                count,
                f"{label} full red",
                nonnegative=True,
            )
            red_certificate = _vector(
                record.get("candidate_horizon_union_planned_red_light_cost"),
                count,
                f"{label} red horizon-union certificate",
                nonnegative=True,
            )
            if not np.allclose(
                red_certificate,
                np.maximum(short_red, full_red),
                atol=1e-9,
                rtol=1e-9,
            ):
                raise ValueError(
                    f"{label} red horizon-union certificate is invalid."
                )
            short_safe_full_red_candidates += int(
                np.sum((short_red <= 0.0) & (full_red > 0.0))
            )
            short_red_full_safe_candidates += int(
                np.sum((short_red > 0.0) & (full_red <= 0.0))
            )
            selected_short_safe_full_red_records += int(
                short_red[selected] <= 0.0 and full_red[selected] > 0.0
            )
            selected_full_red_records += int(full_red[selected] > 0.0)
            selected_is_h30_missed = (
                short_red[selected] <= 0.0 and full_red[selected] > 0.0
            )
            lower_union_red_feasible = feasible & (
                red_certificate < red_certificate[selected]
            )
            lower_union_red_feasible[selected] = False
            lower_union_red_indices = np.flatnonzero(
                lower_union_red_feasible
            )

            if bool(record.get("used_fallback", False)):
                fallback_records += 1
                if selected_is_h30_missed:
                    selected_short_safe_full_red_breakdown["fallback"] += 1
                    if lower_union_red_indices.size:
                        selected_short_safe_full_red_breakdown[
                            "with_lower_union_red_feasible_candidate"
                        ] += 1
                        selected_short_safe_full_red_breakdown[
                            "fallback_with_lower_union_red_feasible_candidate"
                        ] += 1
                    else:
                        selected_short_safe_full_red_breakdown[
                            "without_lower_union_red_feasible_candidate"
                        ] += 1
                    selected_short_safe_full_red_events.append(
                        _red_miss_event_row(
                            log_path=log_path,
                            log_context=log_context,
                            record_index=record_index,
                            record=record,
                            selected=selected,
                            used_fallback=True,
                            progress=progress,
                            short_red=short_red,
                            full_red=full_red,
                            red_certificate=red_certificate,
                            lower_union_red_indices=lower_union_red_indices,
                        )
                    )
                continue
            nonfallback_records += 1
            scores = _selection_scores(
                record.get("selection_scores"),
                feasible,
                f"{label} selection scores",
            )
            command_target = _vector(
                record.get("candidate_perfect_tracker_target_speed_mps"),
                count,
                f"{label} command target speed",
                nonnegative=True,
            )
            command_jerk = _vector(
                record.get("candidate_perfect_tracker_jerk_magnitude_mps3"),
                count,
                f"{label} command jerk",
                nonnegative=True,
            )
            command_lateral = _vector(
                record.get(
                    "candidate_perfect_tracker_"
                    "lateral_acceleration_magnitude_mps2"
                ),
                count,
                f"{label} command lateral",
                nonnegative=True,
            )
            rollout = record.get("candidate_perfect_tracker_open_loop_rollout")
            if not isinstance(rollout, dict):
                raise ValueError(f"{label} lacks rollout metrics.")
            detail_metrics = _rollout_metrics(
                rollout,
                SAFETY_DETAIL_HORIZON,
                count,
                label,
            )
            if selected_is_h30_missed:
                selected_short_safe_full_red_breakdown["nonfallback"] += 1
                if lower_union_red_indices.size:
                    selected_short_safe_full_red_breakdown[
                        "with_lower_union_red_feasible_candidate"
                    ] += 1
                    selected_short_safe_full_red_breakdown[
                        "nonfallback_with_lower_union_red_feasible_candidate"
                    ] += 1
                else:
                    selected_short_safe_full_red_breakdown[
                        "without_lower_union_red_feasible_candidate"
                    ] += 1
                selected_short_safe_full_red_events.append(
                    _red_miss_event_row(
                        log_path=log_path,
                        log_context=log_context,
                        record_index=record_index,
                        record=record,
                        selected=selected,
                        used_fallback=False,
                        progress=progress,
                        short_red=short_red,
                        full_red=full_red,
                        red_certificate=red_certificate,
                        lower_union_red_indices=lower_union_red_indices,
                        scores=scores,
                        command_target=command_target,
                        command_jerk=command_jerk,
                        command_lateral=command_lateral,
                        h3_metrics=detail_metrics,
                    )
                )
                for progress_budget in PROGRESS_LOSS_BUDGETS_M:
                    for distance_budget in H3_DISTANCE_LOSS_BUDGETS_M:
                        admissible = (
                            lower_union_red_feasible
                            & (
                                progress
                                >= progress[selected] - progress_budget
                            )
                            & (
                                detail_metrics["distance_m"]
                                >= (
                                    detail_metrics["distance_m"][selected]
                                    - distance_budget
                                )
                            )
                            & (
                                detail_metrics[
                                    "max_lateral_acceleration_mps2"
                                ]
                                <= H3_MAX_LATERAL_GUARD_MPS2
                            )
                        )
                        admissible_indices = np.flatnonzero(admissible)
                        key = (progress_budget, distance_budget)
                        budget_candidate_counts[key].append(
                            int(admissible_indices.size)
                        )
                        if admissible_indices.size:
                            chosen = min(
                                admissible_indices.tolist(),
                                key=lambda idx: (
                                    float(red_certificate[idx]),
                                    float(scores[idx]),
                                    int(idx),
                                ),
                            )
                            budget_rows[key].append(
                                _delta_row(
                                    selected,
                                    chosen,
                                    progress=progress,
                                    full_red=red_certificate,
                                    distance=detail_metrics["distance_m"],
                                    jerk=detail_metrics[
                                        "mean_vector_jerk_mps3"
                                    ],
                                    lateral=detail_metrics[
                                        "mean_lateral_acceleration_mps2"
                                    ],
                                    command_target=command_target,
                                    command_jerk=command_jerk,
                                    command_lateral=command_lateral,
                                )
                                | {
                                    "selected_full_red": float(
                                        full_red[selected]
                                    ),
                                    "chosen_full_red": float(
                                        full_red[chosen]
                                    ),
                                    "chosen_h3_max_lateral": float(
                                        detail_metrics[
                                            "max_lateral_acceleration_mps2"
                                        ][chosen]
                                    ),
                                }
                            )

            for horizon in HORIZONS:
                metrics = _rollout_metrics(rollout, horizon, count, label)
                distance = metrics["distance_m"]
                jerk = metrics["mean_vector_jerk_mps3"]
                lateral = metrics["mean_lateral_acceleration_mps2"]
                feasible_indices = np.flatnonzero(feasible)
                correlations[horizon]["command_jerk"].extend(
                    command_jerk[feasible_indices].tolist()
                )
                correlations[horizon]["command_lateral"].extend(
                    command_lateral[feasible_indices].tolist()
                )
                correlations[horizon]["rollout_jerk"].extend(
                    jerk[feasible_indices].tolist()
                )
                correlations[horizon]["rollout_lateral"].extend(
                    lateral[feasible_indices].tolist()
                )

                common = (
                    feasible
                    & (progress >= progress[selected])
                    & (red_certificate <= red_certificate[selected])
                    & (distance >= distance[selected])
                    & (jerk <= jerk[selected])
                    & (lateral <= lateral[selected])
                    & (
                        (jerk < jerk[selected])
                        | (lateral < lateral[selected])
                    )
                )
                strict = (
                    common
                    & (command_target >= command_target[selected])
                    & (command_jerk <= command_jerk[selected])
                    & (command_lateral <= command_lateral[selected])
                )
                red_improving = (
                    feasible
                    & (red_certificate < red_certificate[selected])
                    & (progress >= progress[selected])
                    & (distance >= distance[selected])
                )
                red_improving_pareto = (
                    red_improving
                    & (jerk <= jerk[selected])
                    & (lateral <= lateral[selected])
                )
                red_minimum = feasible & (
                    red_certificate < red_certificate[selected]
                )
                common[selected] = False
                strict[selected] = False
                red_improving[selected] = False
                red_improving_pareto[selected] = False
                red_minimum[selected] = False
                common_indices = np.flatnonzero(common)
                strict_indices = np.flatnonzero(strict)
                red_improving_indices = np.flatnonzero(red_improving)
                red_improving_pareto_indices = np.flatnonzero(
                    red_improving_pareto
                )
                red_minimum_indices = np.flatnonzero(red_minimum)
                horizon_rows[horizon]["eligible_candidates"].append(
                    int(common_indices.size)
                )
                horizon_rows[horizon]["strict_eligible_candidates"].append(
                    int(strict_indices.size)
                )
                horizon_rows[horizon]["red_improving_candidates"].append(
                    int(red_improving_indices.size)
                )
                horizon_rows[horizon][
                    "red_improving_pareto_candidates"
                ].append(int(red_improving_pareto_indices.size))
                horizon_rows[horizon]["red_minimum_candidates"].append(
                    int(red_minimum_indices.size)
                )
                if common_indices.size:
                    chosen = min(
                        common_indices.tolist(),
                        key=lambda idx: (
                            float(jerk[idx]),
                            float(lateral[idx]),
                            float(scores[idx]),
                            int(idx),
                        ),
                    )
                    horizon_rows[horizon]["rollout_pareto"].append(
                        _delta_row(
                            selected,
                            chosen,
                            progress=progress,
                            full_red=red_certificate,
                            distance=distance,
                            jerk=jerk,
                            lateral=lateral,
                            command_target=command_target,
                            command_jerk=command_jerk,
                            command_lateral=command_lateral,
                        )
                    )
                if strict_indices.size:
                    chosen = min(
                        strict_indices.tolist(),
                        key=lambda idx: (
                            float(jerk[idx]),
                            float(lateral[idx]),
                            float(command_jerk[idx]),
                            float(command_lateral[idx]),
                            float(scores[idx]),
                            int(idx),
                        ),
                    )
                    horizon_rows[horizon][
                        "command_and_rollout_pareto"
                    ].append(
                        _delta_row(
                            selected,
                            chosen,
                            progress=progress,
                            full_red=red_certificate,
                            distance=distance,
                            jerk=jerk,
                            lateral=lateral,
                            command_target=command_target,
                            command_jerk=command_jerk,
                            command_lateral=command_lateral,
                        )
                    )
                if red_improving_indices.size:
                    chosen = min(
                        red_improving_indices.tolist(),
                        key=lambda idx: (
                            float(red_certificate[idx]),
                            float(jerk[idx]),
                            float(lateral[idx]),
                            float(scores[idx]),
                            int(idx),
                        ),
                    )
                    horizon_rows[horizon][
                        "red_improving_progress_distance"
                    ].append(
                        _delta_row(
                            selected,
                            chosen,
                            progress=progress,
                            full_red=red_certificate,
                            distance=distance,
                            jerk=jerk,
                            lateral=lateral,
                            command_target=command_target,
                            command_jerk=command_jerk,
                            command_lateral=command_lateral,
                        )
                    )
                if red_improving_pareto_indices.size:
                    chosen = min(
                        red_improving_pareto_indices.tolist(),
                        key=lambda idx: (
                            float(red_certificate[idx]),
                            float(jerk[idx]),
                            float(lateral[idx]),
                            float(scores[idx]),
                            int(idx),
                        ),
                    )
                    horizon_rows[horizon][
                        "red_improving_rollout_pareto"
                    ].append(
                        _delta_row(
                            selected,
                            chosen,
                            progress=progress,
                            full_red=red_certificate,
                            distance=distance,
                            jerk=jerk,
                            lateral=lateral,
                            command_target=command_target,
                            command_jerk=command_jerk,
                            command_lateral=command_lateral,
                        )
                    )
                if red_minimum_indices.size:
                    minimum_red = float(
                        np.min(red_certificate[red_minimum_indices])
                    )
                    minimum_indices = red_minimum_indices[
                        red_certificate[red_minimum_indices] == minimum_red
                    ]
                    chosen = min(
                        minimum_indices.tolist(),
                        key=lambda idx: (
                            -float(progress[idx]),
                            -float(distance[idx]),
                            float(jerk[idx]),
                            float(lateral[idx]),
                            float(scores[idx]),
                            int(idx),
                        ),
                    )
                    horizon_rows[horizon][
                        "red_minimum_best_progress"
                    ].append(
                        _delta_row(
                            selected,
                            chosen,
                            progress=progress,
                            full_red=red_certificate,
                            distance=distance,
                            jerk=jerk,
                            lateral=lateral,
                            command_target=command_target,
                            command_jerk=command_jerk,
                            command_lateral=command_lateral,
                        )
                    )

    horizon_reports = {}
    for horizon in HORIZONS:
        rows = horizon_rows[horizon]
        horizon_reports[str(horizon)] = {
            "rollout_pareto": _summarize_screen(
                rows["rollout_pareto"],
                nonfallback_records,
                rows["eligible_candidates"],
            ),
            "command_and_rollout_pareto": _summarize_screen(
                rows["command_and_rollout_pareto"],
                nonfallback_records,
                rows["strict_eligible_candidates"],
            ),
            "red_improving_progress_distance": _summarize_screen(
                rows["red_improving_progress_distance"],
                nonfallback_records,
                rows["red_improving_candidates"],
            ),
            "red_improving_rollout_pareto": _summarize_screen(
                rows["red_improving_rollout_pareto"],
                nonfallback_records,
                rows["red_improving_pareto_candidates"],
            ),
            "red_minimum_best_progress": _summarize_screen(
                rows["red_minimum_best_progress"],
                nonfallback_records,
                rows["red_minimum_candidates"],
            ),
            "feasible_correlations": {
                "command_jerk_vs_rollout_vector_jerk": _correlation(
                    correlations[horizon]["command_jerk"],
                    correlations[horizon]["rollout_jerk"],
                ),
                "command_lateral_vs_rollout_lateral": _correlation(
                    correlations[horizon]["command_lateral"],
                    correlations[horizon]["rollout_lateral"],
                ),
            },
        }

    return {
        "analysis": {
            "name": "dp_camp_tracker_rollout_shadow_screen_v1",
            "selection_effect": False,
            "online_feature_eligible": True,
            "closed_loop_guarantee": False,
            "interpretation": (
                "Outcome-free fixed-candidate screening. Passing this screen "
                "does not establish improvement under future DP replanning."
            ),
        },
        "records": {
            "logs": len(log_paths),
            "total": total_records,
            "fallback": fallback_records,
            "nonfallback": nonfallback_records,
            "candidates": candidate_count,
        },
        "full_horizon_red_light": {
            "short_safe_full_red_candidates": short_safe_full_red_candidates,
            "short_safe_full_red_candidate_rate": (
                short_safe_full_red_candidates / candidate_count
                if candidate_count
                else 0.0
            ),
            "short_red_full_safe_candidates": short_red_full_safe_candidates,
            "selected_short_safe_full_red_records": (
                selected_short_safe_full_red_records
            ),
            "selected_full_red_records": selected_full_red_records,
            "selected_short_safe_full_red_breakdown": (
                selected_short_safe_full_red_breakdown
            ),
            "selected_short_safe_full_red_events": (
                selected_short_safe_full_red_events
            ),
            "predeclared_budget_sensitivity_h3": (
                _summarize_budget_sensitivity(
                    rows_by_budget=budget_rows,
                    candidate_counts_by_budget=budget_candidate_counts,
                    event_count=selected_short_safe_full_red_records,
                )
            ),
        },
        "horizons": horizon_reports,
    }


def _reward_metrics(
    record: dict[str, Any],
    candidate_count: int,
    label: str,
) -> tuple[np.ndarray, np.ndarray]:
    rewards = record.get("dp_candidate_rewards")
    if not isinstance(rewards, list) or len(rewards) != candidate_count:
        raise ValueError(f"{label} lacks DP reward metrics.")
    progress = np.asarray(
        [float(reward.get("progress", 0.0)) for reward in rewards],
        dtype=np.float64,
    )
    red = np.asarray(
        [
            max(-float(reward.get("red_light", 0.0)), 0.0)
            for reward in rewards
        ],
        dtype=np.float64,
    )
    if not np.all(np.isfinite(progress)) or not np.all(np.isfinite(red)):
        raise ValueError(f"{label} has nonfinite DP reward metrics.")
    return progress, red


def _rollout_metrics(
    rollout: dict[str, Any],
    horizon: int,
    candidate_count: int,
    label: str,
) -> dict[str, np.ndarray]:
    metrics = rollout.get(str(horizon))
    if not isinstance(metrics, dict):
        raise ValueError(f"{label} lacks rollout horizon {horizon}.")
    return {
        "distance_m": _vector(
            metrics.get("distance_m"),
            candidate_count,
            f"{label} H{horizon} distance",
            nonnegative=True,
        ),
        "mean_vector_jerk_mps3": _vector(
            metrics.get("mean_vector_jerk_mps3"),
            candidate_count,
            f"{label} H{horizon} vector jerk",
            nonnegative=True,
        ),
        "max_vector_jerk_mps3": _vector(
            metrics.get("max_vector_jerk_mps3"),
            candidate_count,
            f"{label} H{horizon} max vector jerk",
            nonnegative=True,
        ),
        "mean_lateral_acceleration_mps2": _vector(
            metrics.get("mean_lateral_acceleration_mps2"),
            candidate_count,
            f"{label} H{horizon} lateral",
            nonnegative=True,
        ),
        "max_lateral_acceleration_mps2": _vector(
            metrics.get("max_lateral_acceleration_mps2"),
            candidate_count,
            f"{label} H{horizon} max lateral",
            nonnegative=True,
        ),
    }


def _load_log_context(log_path: Path) -> dict[str, Any]:
    summary_path = log_path.parent / "camp_replay_summary.json"
    if not summary_path.exists():
        return {}
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    benchmark = summary.get("benchmark")
    if not isinstance(benchmark, dict):
        return {}
    keys = (
        "variant",
        "route",
        "seed",
        "max_npcs",
        "traffic_lights",
        "advance_mode",
    )
    return {key: benchmark.get(key) for key in keys}


def _vector(
    values: Any,
    candidate_count: int,
    label: str,
    *,
    nonnegative: bool = False,
) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64).reshape(-1)
    if (
        array.shape != (candidate_count,)
        or not np.all(np.isfinite(array))
        or (nonnegative and np.any(array < 0.0))
    ):
        raise ValueError(f"{label} is invalid.")
    return array


def _selection_scores(
    values: Any,
    feasible: np.ndarray,
    label: str,
) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64).reshape(-1)
    if (
        array.shape != feasible.shape
        or np.any(np.isnan(array))
        or np.any(np.isneginf(array))
        or not np.all(np.isfinite(array[feasible]))
    ):
        raise ValueError(f"{label} is invalid.")
    return array


def _delta_row(
    baseline: int,
    candidate: int,
    **metrics: np.ndarray,
) -> dict[str, float]:
    return {
        name: float(values[candidate] - values[baseline])
        for name, values in metrics.items()
    }


def _red_miss_event_row(
    *,
    log_path: Path,
    log_context: dict[str, Any],
    record_index: int,
    record: dict[str, Any],
    selected: int,
    used_fallback: bool,
    progress: np.ndarray,
    short_red: np.ndarray,
    full_red: np.ndarray,
    red_certificate: np.ndarray,
    lower_union_red_indices: np.ndarray,
    scores: np.ndarray | None = None,
    command_target: np.ndarray | None = None,
    command_jerk: np.ndarray | None = None,
    command_lateral: np.ndarray | None = None,
    h3_metrics: dict[str, np.ndarray] | None = None,
) -> dict[str, Any]:
    best_lower_red: dict[str, Any] | None = None
    if lower_union_red_indices.size:
        chosen = min(
            lower_union_red_indices.tolist(),
            key=lambda idx: (
                float(red_certificate[idx]),
                (
                    float(scores[idx])
                    if scores is not None and np.isfinite(scores[idx])
                    else 0.0
                ),
                int(idx),
            ),
        )
        best_lower_red = {
            "candidate_index": int(chosen),
            "delta": _delta_row(
                selected,
                chosen,
                progress=progress,
                full_red=red_certificate,
                **(
                    {
                        "distance": h3_metrics["distance_m"],
                        "jerk": h3_metrics["mean_vector_jerk_mps3"],
                        "lateral": h3_metrics[
                            "mean_lateral_acceleration_mps2"
                        ],
                    }
                    if h3_metrics is not None
                    else {}
                ),
                **(
                    {
                        "command_target": command_target,
                        "command_jerk": command_jerk,
                        "command_lateral": command_lateral,
                    }
                    if command_target is not None
                    and command_jerk is not None
                    and command_lateral is not None
                    else {}
                ),
            ),
            "absolute": _candidate_absolute_row(
                chosen,
                progress=progress,
                short_red=short_red,
                full_red=full_red,
                red_certificate=red_certificate,
                scores=scores,
                command_target=command_target,
                command_jerk=command_jerk,
                command_lateral=command_lateral,
                h3_metrics=h3_metrics,
            ),
        }
    return {
        "selection_log": str(log_path),
        "record_index": int(record_index),
        "selection_step": record.get("selection_step"),
        "context": log_context,
        "selected_index": int(selected),
        "used_fallback": bool(used_fallback),
        "current_speed_mps": _nested_number(
            record,
            ("perfect_tracker_command_inputs", "current_speed_mps"),
        ),
        "lower_union_red_feasible_candidates": int(
            lower_union_red_indices.size
        ),
        "selected": _candidate_absolute_row(
            selected,
            progress=progress,
            short_red=short_red,
            full_red=full_red,
            red_certificate=red_certificate,
            scores=scores,
            command_target=command_target,
            command_jerk=command_jerk,
            command_lateral=command_lateral,
            h3_metrics=h3_metrics,
        ),
        "best_lower_union_red_feasible_candidate": best_lower_red,
    }


def _candidate_absolute_row(
    index: int,
    *,
    progress: np.ndarray,
    short_red: np.ndarray,
    full_red: np.ndarray,
    red_certificate: np.ndarray,
    scores: np.ndarray | None,
    command_target: np.ndarray | None,
    command_jerk: np.ndarray | None,
    command_lateral: np.ndarray | None,
    h3_metrics: dict[str, np.ndarray] | None,
) -> dict[str, float | None]:
    row: dict[str, float | None] = {
        "progress": float(progress[index]),
        "short_horizon_red": float(short_red[index]),
        "full_horizon_red": float(full_red[index]),
        "union_red_certificate": float(red_certificate[index]),
        "selection_score": (
            float(scores[index])
            if scores is not None and np.isfinite(scores[index])
            else None
        ),
    }
    if (
        command_target is not None
        and command_jerk is not None
        and command_lateral is not None
    ):
        row.update(
            {
                "command_target_speed_mps": float(command_target[index]),
                "command_jerk_mps3": float(command_jerk[index]),
                "command_lateral_mps2": float(command_lateral[index]),
            }
        )
    if h3_metrics is not None:
        row.update(
            {
                "h3_distance_m": float(h3_metrics["distance_m"][index]),
                "h3_mean_vector_jerk_mps3": float(
                    h3_metrics["mean_vector_jerk_mps3"][index]
                ),
                "h3_max_vector_jerk_mps3": float(
                    h3_metrics["max_vector_jerk_mps3"][index]
                ),
                "h3_mean_lateral_mps2": float(
                    h3_metrics["mean_lateral_acceleration_mps2"][index]
                ),
                "h3_max_lateral_mps2": float(
                    h3_metrics["max_lateral_acceleration_mps2"][index]
                ),
            }
        )
    return row


def _nested_number(record: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    value: Any = record
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def _summarize_screen(
    rows: list[dict[str, float]],
    nonfallback_records: int,
    candidate_counts: list[int],
) -> dict[str, Any]:
    metric_names = (
        "progress",
        "full_red",
        "distance",
        "jerk",
        "lateral",
        "command_target",
        "command_jerk",
        "command_lateral",
    )
    return {
        "changed_records": len(rows),
        "change_rate": (
            len(rows) / nonfallback_records if nonfallback_records else 0.0
        ),
        "mean_eligible_candidates": (
            float(np.mean(candidate_counts)) if candidate_counts else 0.0
        ),
        "mean_deltas_on_changed_records": {
            name: (
                float(np.mean([row[name] for row in rows]))
                if rows
                else None
            )
            for name in metric_names
        },
        "delta_quantiles_on_changed_records": {
            name: (
                {
                    "p10": float(
                        np.percentile([row[name] for row in rows], 10)
                    ),
                    "p50": float(
                        np.percentile([row[name] for row in rows], 50)
                    ),
                    "p90": float(
                        np.percentile([row[name] for row in rows], 90)
                    ),
                }
                if rows
                else None
            )
            for name in metric_names
        },
    }


def _summarize_budget_sensitivity(
    *,
    rows_by_budget: dict[tuple[float, float], list[dict[str, float]]],
    candidate_counts_by_budget: dict[tuple[float, float], list[int]],
    event_count: int,
) -> dict[str, Any]:
    cells = []
    for progress_budget, distance_budget in sorted(rows_by_budget):
        rows = rows_by_budget[(progress_budget, distance_budget)]
        candidate_counts = candidate_counts_by_budget[
            (progress_budget, distance_budget)
        ]
        summary = _summarize_screen(rows, event_count, candidate_counts)
        cells.append(
            {
                "progress_loss_budget_m": float(progress_budget),
                "h3_distance_loss_budget_m": float(distance_budget),
                "h3_max_lateral_guard_mps2": H3_MAX_LATERAL_GUARD_MPS2,
                "selection_rule": "min_union_red_then_camp_score_then_index",
                **summary,
                "selected_full_red_mean": (
                    float(np.mean([row["selected_full_red"] for row in rows]))
                    if rows
                    else None
                ),
                "chosen_full_red_mean": (
                    float(np.mean([row["chosen_full_red"] for row in rows]))
                    if rows
                    else None
                ),
                "chosen_h3_max_lateral_mean": (
                    float(
                        np.mean(
                            [row["chosen_h3_max_lateral"] for row in rows]
                        )
                    )
                    if rows
                    else None
                ),
            }
        )
    return {
        "event_denominator": event_count,
        "progress_loss_budgets_m": list(PROGRESS_LOSS_BUDGETS_M),
        "h3_distance_loss_budgets_m": list(H3_DISTANCE_LOSS_BUDGETS_M),
        "h3_max_lateral_guard_mps2": H3_MAX_LATERAL_GUARD_MPS2,
        "jerk_guard": None,
        "jerk_guard_note": (
            "No physical jerk threshold is applied here; jerk remains a "
            "reported tradeoff until a specification-backed limit is chosen."
        ),
        "cells": cells,
    }


def _correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) < 2 or len(right) != len(left):
        return None
    left_array = np.asarray(left, dtype=np.float64)
    right_array = np.asarray(right, dtype=np.float64)
    if np.std(left_array) <= 1e-12 or np.std(right_array) <= 1e-12:
        return None
    return float(np.corrcoef(left_array, right_array)[0, 1])


def render_markdown(report: dict[str, Any]) -> str:
    records = report["records"]
    red = report["full_horizon_red_light"]
    lines = [
        "# PerfectTracker Rollout Shadow Screen",
        "",
        f"- Logs: {records['logs']}",
        f"- Records: {records['total']}",
        f"- Non-fallback records: {records['nonfallback']}",
        (
            "- h30-safe candidates with a full-horizon red violation: "
            f"{red['short_safe_full_red_candidates']}"
        ),
        (
            "- Selected h30-safe records with a full-horizon red violation: "
            f"{red['selected_short_safe_full_red_records']}"
        ),
        (
            "- Selected h30-safe/full-red records with a lower union-red "
            "base-feasible candidate: "
            f"{red['selected_short_safe_full_red_breakdown']['with_lower_union_red_feasible_candidate']}"
        ),
        (
            "- Selected h30-safe/full-red fallback records: "
            f"{red['selected_short_safe_full_red_breakdown']['fallback']}"
        ),
        "",
        "| Horizon | Screen | Changes | Rate | Progress | Full red | Distance | "
        "Vector jerk | Lateral |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for horizon, horizon_report in report["horizons"].items():
        for screen in (
            "rollout_pareto",
            "command_and_rollout_pareto",
            "red_improving_progress_distance",
            "red_improving_rollout_pareto",
            "red_minimum_best_progress",
        ):
            row = horizon_report[screen]
            delta = row["mean_deltas_on_changed_records"]
            lines.append(
                f"| {horizon} | {screen} | {row['changed_records']} | "
                f"{row['change_rate']:.6f} | {_fmt(delta['progress'])} | "
                f"{_fmt(delta['full_red'])} | {_fmt(delta['distance'])} | "
                f"{_fmt(delta['jerk'])} | {_fmt(delta['lateral'])} |"
            )
    budget = red["predeclared_budget_sensitivity_h3"]
    lines.extend(
        [
            "",
            "## H3 Safety Budget Sensitivity",
            "",
            (
                "Rows are predeclared offline sensitivity checks for h30-safe "
                "selected records with full-horizon red exposure. The rule is "
                "safety-first over the union-red certificate, then original "
                "CAMP score and candidate index. Jerk is reported as a "
                "tradeoff, not hard-filtered."
            ),
            "",
            "| Progress loss budget | H3 distance loss budget | Changes | Rate | "
            "Union red | Progress | H3 distance | H3 vector jerk | H3 lateral |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for cell in budget["cells"]:
        delta = cell["mean_deltas_on_changed_records"]
        lines.append(
            f"| {cell['progress_loss_budget_m']:.2f} m | "
            f"{cell['h3_distance_loss_budget_m']:.2f} m | "
            f"{cell['changed_records']} | {cell['change_rate']:.6f} | "
            f"{_fmt(delta['full_red'])} | {_fmt(delta['progress'])} | "
            f"{_fmt(delta['distance'])} | {_fmt(delta['jerk'])} | "
            f"{_fmt(delta['lateral'])} |"
        )
    lines.extend(
        [
            "",
            budget["jerk_guard_note"],
            "",
            "This is an outcome-free fixed-candidate screen, not a guarantee "
            "about future Diffusion Planner replanning.",
            "",
        ]
    )
    return "\n".join(lines)


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:+.6f}"


def main() -> None:
    args = parse_args()
    paths = list(args.root) + list(args.selection_log)
    if not paths:
        raise SystemExit("Provide at least one --root or --selection_log.")
    report = analyze(paths)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")


if __name__ == "__main__":
    main()
