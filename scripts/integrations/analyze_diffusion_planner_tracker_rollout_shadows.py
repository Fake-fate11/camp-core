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

            if bool(record.get("used_fallback", False)):
                fallback_records += 1
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

            for horizon in HORIZONS:
                metrics = rollout.get(str(horizon))
                if not isinstance(metrics, dict):
                    raise ValueError(f"{label} lacks rollout horizon {horizon}.")
                distance = _vector(
                    metrics.get("distance_m"),
                    count,
                    f"{label} H{horizon} distance",
                    nonnegative=True,
                )
                jerk = _vector(
                    metrics.get("mean_vector_jerk_mps3"),
                    count,
                    f"{label} H{horizon} vector jerk",
                    nonnegative=True,
                )
                lateral = _vector(
                    metrics.get("mean_lateral_acceleration_mps2"),
                    count,
                    f"{label} H{horizon} lateral",
                    nonnegative=True,
                )
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
    lines.extend(
        [
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
