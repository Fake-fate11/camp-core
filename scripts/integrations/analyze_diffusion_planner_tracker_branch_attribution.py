#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


BENCHMARK_KEYS = (
    "route",
    "seed",
    "steps",
    "max_npcs",
    "spawn_probability",
    "traffic_lights",
    "advance_mode",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Attribute paired closed-loop branch changes after the rejected "
            "PerfectTracker command postselection."
        )
    )
    parser.add_argument("--baseline_root", type=Path, required=True)
    parser.add_argument("--variant_root", type=Path, required=True)
    parser.add_argument("--horizons", type=str, default="3,5,10")
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def compute_tracker_branch_attribution(
    baseline_root: Path,
    variant_root: Path,
    *,
    horizons: tuple[int, ...] = (3, 5, 10),
) -> dict[str, Any]:
    horizons = _validate_horizons(horizons)
    baseline_root = baseline_root.resolve()
    variant_root = variant_root.resolve()
    variant_logs = sorted(variant_root.rglob("camp_selection_log.json"))
    if not variant_logs:
        raise ValueError(f"No selection logs found under {variant_root}.")

    events: list[dict[str, Any]] = []
    run_reports: list[dict[str, Any]] = []
    target_alignment_errors: list[float] = []
    heading_alignment_errors: list[float] = []
    planned_status_differences: list[dict[str, Any]] = []

    for variant_log in variant_logs:
        relative = variant_log.relative_to(variant_root)
        baseline_log = baseline_root / relative
        if not baseline_log.is_file():
            raise ValueError(f"Missing paired baseline log: {baseline_log}.")
        variant_dir = variant_log.parent
        baseline_dir = baseline_log.parent
        baseline_summary = _read_summary(baseline_dir)
        variant_summary = _read_summary(variant_dir)
        _validate_pair(baseline_summary, variant_summary, variant_dir)

        baseline_selection = _read_list(baseline_log)
        variant_selection = _read_list(variant_log)
        baseline_trajectory = _read_list(baseline_dir / "trajectory_log.json")
        variant_trajectory = _read_list(variant_dir / "trajectory_log.json")
        baseline_metrics = _read_list(baseline_dir / "camp_metric_log.json")
        variant_metrics = _read_list(variant_dir / "camp_metric_log.json")
        lengths = {
            len(baseline_selection),
            len(variant_selection),
            len(baseline_trajectory),
            len(variant_trajectory),
            len(baseline_metrics),
            len(variant_metrics),
        }
        if len(lengths) != 1:
            raise ValueError(f"{variant_dir} has misaligned paired logs.")
        for record_idx, record in enumerate(variant_selection):
            if record.get("candidate_closed_loop_outcomes") is not None:
                raise ValueError(
                    f"{variant_log} record {record_idx} contains candidate "
                    "closed-loop outcomes."
                )

        changed_steps = [
            idx
            for idx, record in enumerate(variant_selection)
            if bool(
                (record.get("perfect_tracker_command_postselection") or {}).get(
                    "changed"
                )
            )
        ]
        baseline_motion = _motion_arrays(baseline_trajectory)
        variant_motion = _motion_arrays(variant_trajectory)

        for step in range(len(variant_selection) - 1):
            record = variant_selection[step]
            selected = _selected_index(record, variant_log, step)
            target = _candidate_vector(
                record,
                "candidate_perfect_tracker_target_speed_mps",
            )[selected]
            heading = _candidate_heading(record)[selected]
            actual_heading_delta = _wrapped_delta(
                float(variant_trajectory[step + 1]["heading"]),
                float(variant_trajectory[step]["heading"]),
            )
            target_alignment_errors.append(
                abs(target - float(variant_trajectory[step + 1]["speed"]))
            )
            heading_alignment_errors.append(
                abs(_wrapped_delta(heading, actual_heading_delta))
            )

        for step in range(len(variant_selection)):
            baseline_red = float(baseline_metrics[step]["pred_red_light"]) < -0.5
            variant_red = float(variant_metrics[step]["pred_red_light"]) < -0.5
            if baseline_red == variant_red:
                continue
            prior_changes = [value for value in changed_steps if value <= step]
            planned_status_differences.append(
                {
                    "run": str(relative.parent),
                    "step": step,
                    "baseline_violation": baseline_red,
                    "variant_violation": variant_red,
                    "lag_from_latest_change": (
                        step - max(prior_changes) if prior_changes else None
                    ),
                }
            )

        for step in changed_steps:
            events.append(
                _event_row(
                    run=str(relative.parent),
                    step=step,
                    changed_steps=changed_steps,
                    baseline_selection=baseline_selection,
                    variant_selection=variant_selection,
                    baseline_trajectory=baseline_trajectory,
                    variant_trajectory=variant_trajectory,
                    baseline_metrics=baseline_metrics,
                    variant_metrics=variant_metrics,
                    baseline_motion=baseline_motion,
                    variant_motion=variant_motion,
                    horizons=horizons,
                )
            )

        run_reports.append(
            {
                "run": str(relative.parent),
                "steps": len(variant_selection),
                "changed_steps": changed_steps,
                "changed_records": len(changed_steps),
                "command_shadow_schema_version": (
                    variant_summary.get(
                        "camp_shadow_perfect_tracker_command",
                        {},
                    ).get("schema_version")
                ),
            }
        )

    return _build_report(
        baseline_root=baseline_root,
        variant_root=variant_root,
        horizons=horizons,
        run_reports=run_reports,
        events=events,
        target_alignment_errors=target_alignment_errors,
        heading_alignment_errors=heading_alignment_errors,
        planned_status_differences=planned_status_differences,
    )


def _event_row(
    *,
    run: str,
    step: int,
    changed_steps: list[int],
    baseline_selection: list[dict[str, Any]],
    variant_selection: list[dict[str, Any]],
    baseline_trajectory: list[dict[str, Any]],
    variant_trajectory: list[dict[str, Any]],
    baseline_metrics: list[dict[str, Any]],
    variant_metrics: list[dict[str, Any]],
    baseline_motion: dict[str, np.ndarray],
    variant_motion: dict[str, np.ndarray],
    horizons: tuple[int, ...],
) -> dict[str, Any]:
    record = variant_selection[step]
    baseline_index = record.get(
        "camp_selected_index_before_tracker_postselection"
    )
    selected_index = _selected_index(record, Path(run), step)
    candidate_count = len(record["feasible_mask"])
    if (
        isinstance(baseline_index, bool)
        or not isinstance(baseline_index, int)
        or not 0 <= baseline_index < candidate_count
    ):
        raise ValueError(f"{run} record {step} has invalid baseline index.")

    progress, red = _reward_metrics(record)
    candidate_fields = {
        "target_speed": _candidate_vector(
            record,
            "candidate_perfect_tracker_target_speed_mps",
        ),
        "command_jerk": _candidate_vector(
            record,
            "candidate_perfect_tracker_jerk_magnitude_mps3",
        ),
        "command_lateral": _candidate_vector(
            record,
            "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2",
        ),
        "horizon_jerk": _candidate_vector(
            record,
            "candidate_dp_prior_jerk_excess_cost",
        ),
        "horizon_lateral": _candidate_vector(
            record,
            "candidate_horizon_lateral_acceleration_cost",
        ),
    }
    immediate = {
        name: float(values[selected_index] - values[baseline_index])
        for name, values in candidate_fields.items()
    }
    immediate["progress"] = float(
        progress[selected_index] - progress[baseline_index]
    )
    immediate["h30_planned_red"] = float(
        red[selected_index] - red[baseline_index]
    )

    baseline_state = baseline_trajectory[step]
    variant_state = variant_trajectory[step]
    position_delta = math.hypot(
        float(variant_state["x"]) - float(baseline_state["x"]),
        float(variant_state["y"]) - float(baseline_state["y"]),
    )
    scene_delta = float(
        np.linalg.norm(
            np.asarray(
                variant_selection[step]["dp_scene_features"],
                dtype=np.float64,
            )
            - np.asarray(
                baseline_selection[step]["dp_scene_features"],
                dtype=np.float64,
            )
        )
    )
    prestate = {
        "position_delta_m": position_delta,
        "speed_delta_mps": (
            float(variant_state["speed"]) - float(baseline_state["speed"])
        ),
        "heading_delta_rad": abs(
            _wrapped_delta(
                float(variant_state["heading"]),
                float(baseline_state["heading"]),
            )
        ),
        "scene_feature_l2": scene_delta,
    }
    prestate["matched"] = bool(
        position_delta <= 1e-3
        and abs(prestate["speed_delta_mps"]) <= 1e-3
        and prestate["heading_delta_rad"] <= 1e-4
        and scene_delta <= 1e-3
    )

    window_responses = {}
    for horizon in horizons:
        end = min(step + horizon, len(variant_trajectory) - 1)
        planned_end = min(step + horizon, len(variant_metrics))
        baseline_distance = _window_distance(
            baseline_motion["positions"],
            step,
            end,
        )
        variant_distance = _window_distance(
            variant_motion["positions"],
            step,
            end,
        )
        baseline_red_steps = sum(
            float(row["pred_red_light"]) < -0.5
            for row in baseline_metrics[step:planned_end]
        )
        variant_red_steps = sum(
            float(row["pred_red_light"]) < -0.5
            for row in variant_metrics[step:planned_end]
        )
        window_responses[str(horizon)] = {
            "distance_delta_m": variant_distance - baseline_distance,
            "planned_red_step_delta": (
                variant_red_steps - baseline_red_steps
            ),
            "mean_vector_jerk_delta_mps3": _window_mean_delta(
                baseline_motion["jerk"],
                variant_motion["jerk"],
                max(step - 1, 0),
                max(end - 1, 0),
            ),
            "mean_lateral_acceleration_delta_mps2": _window_mean_delta(
                baseline_motion["lateral"],
                variant_motion["lateral"],
                step,
                end,
            ),
            "contains_later_change": any(
                step < other <= end for other in changed_steps
            ),
        }

    return {
        "run": run,
        "step": step,
        "baseline_index": baseline_index,
        "selected_index": selected_index,
        "prestate": prestate,
        "immediate_candidate_deltas": immediate,
        "paired_full_plan_red": {
            "baseline_pred_red_light": float(
                baseline_metrics[step]["pred_red_light"]
            ),
            "variant_pred_red_light": float(
                variant_metrics[step]["pred_red_light"]
            ),
        },
        "window_responses": window_responses,
    }


def _build_report(
    *,
    baseline_root: Path,
    variant_root: Path,
    horizons: tuple[int, ...],
    run_reports: list[dict[str, Any]],
    events: list[dict[str, Any]],
    target_alignment_errors: list[float],
    heading_alignment_errors: list[float],
    planned_status_differences: list[dict[str, Any]],
) -> dict[str, Any]:
    immediate_names = (
        "target_speed",
        "progress",
        "h30_planned_red",
        "command_jerk",
        "command_lateral",
        "horizon_jerk",
        "horizon_lateral",
    )
    immediate = {
        name: _distribution(
            [
                event["immediate_candidate_deltas"][name]
                for event in events
            ]
        )
        for name in immediate_names
    }
    windows = {}
    for horizon in horizons:
        key = str(horizon)
        windows[key] = {
            name: _distribution(
                [
                    event["window_responses"][key][name]
                    for event in events
                ]
            )
            for name in (
                "distance_delta_m",
                "planned_red_step_delta",
                "mean_vector_jerk_delta_mps3",
                "mean_lateral_acceleration_delta_mps2",
            )
        }
        windows[key]["contaminated_events"] = sum(
            bool(event["window_responses"][key]["contains_later_change"])
            for event in events
        )

    variant_extra = [
        row
        for row in planned_status_differences
        if row["variant_violation"] and not row["baseline_violation"]
    ]
    baseline_extra = [
        row
        for row in planned_status_differences
        if row["baseline_violation"] and not row["variant_violation"]
    ]
    return {
        "analysis": {
            "name": "dp_camp_tracker_branch_attribution_v1",
            "selection_effect": False,
            "uses_realized_branch_metrics": True,
            "online_feature_eligible": False,
            "interpretation": (
                "Offline paired branch attribution. Realized responses are "
                "diagnostic evidence only and must not be used as online "
                "selector features or training labels."
            ),
            "causal_limit": (
                "Only matched-prestate events approximate isolated first "
                "branch changes. Later events include accumulated state and "
                "candidate-pool drift."
            ),
        },
        "roots": {
            "baseline": str(baseline_root),
            "variant": str(variant_root),
        },
        "pairing": {
            "runs": len(run_reports),
            "total_steps": sum(row["steps"] for row in run_reports),
            "changed_runs": sum(row["changed_records"] > 0 for row in run_reports),
            "changed_records": len(events),
        },
        "command_shadow_versions": sorted(
            {
                str(row["command_shadow_schema_version"])
                for row in run_reports
            }
        ),
        "execution_alignment": {
            "target_to_next_speed_error_mps": _error_summary(
                target_alignment_errors
            ),
            "heading_to_next_heading_error_rad": _error_summary(
                heading_alignment_errors
            ),
        },
        "event_prestate": {
            "matched_records": sum(
                bool(event["prestate"]["matched"]) for event in events
            ),
            "position_delta_m": _distribution(
                [event["prestate"]["position_delta_m"] for event in events]
            ),
            "scene_feature_l2": _distribution(
                [event["prestate"]["scene_feature_l2"] for event in events]
            ),
        },
        "immediate_candidate_deltas": immediate,
        "planned_red_status_differences": {
            "total": len(planned_status_differences),
            "variant_extra": len(variant_extra),
            "baseline_extra": len(baseline_extra),
            "variant_extra_lags": _lag_counts(variant_extra),
            "rows": planned_status_differences,
        },
        "window_responses": windows,
        "runs": run_reports,
        "events": events,
    }


def _read_summary(output_dir: Path) -> dict[str, Any]:
    path = output_dir / "camp_validation_summary.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return value


def _read_list(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list) or not value:
        raise ValueError(f"{path} must contain a nonempty JSON list.")
    return value


def _validate_pair(
    baseline_summary: dict[str, Any],
    variant_summary: dict[str, Any],
    variant_dir: Path,
) -> None:
    baseline_benchmark = baseline_summary.get("benchmark")
    variant_benchmark = variant_summary.get("benchmark")
    if not isinstance(baseline_benchmark, dict) or not isinstance(
        variant_benchmark,
        dict,
    ):
        raise ValueError(f"{variant_dir} lacks benchmark metadata.")
    for key in BENCHMARK_KEYS:
        if baseline_benchmark.get(key) != variant_benchmark.get(key):
            raise ValueError(f"{variant_dir} is not paired on benchmark {key}.")
    metadata = variant_summary.get(
        "camp_perfect_tracker_command_postselection"
    )
    if (
        variant_summary.get("advance_mode") != "perfect"
        or not isinstance(metadata, dict)
        or metadata.get("enabled") is not True
        or metadata.get("selection_effect") is not True
    ):
        raise ValueError(
            f"{variant_dir} does not certify PerfectTracker postselection."
        )


def _selected_index(
    record: dict[str, Any],
    log_path: Path,
    record_idx: int,
) -> int:
    selected = record.get("selected_index")
    candidate_count = len(record.get("feasible_mask", []))
    if (
        isinstance(selected, bool)
        or not isinstance(selected, int)
        or not 0 <= selected < candidate_count
    ):
        raise ValueError(f"{log_path} record {record_idx} has invalid index.")
    return selected


def _candidate_vector(record: dict[str, Any], field: str) -> np.ndarray:
    values = np.asarray(record.get(field), dtype=np.float64).reshape(-1)
    candidate_count = len(record.get("feasible_mask", []))
    if (
        values.shape != (candidate_count,)
        or not np.all(np.isfinite(values))
    ):
        raise ValueError(f"Invalid candidate field {field}.")
    return values


def _candidate_heading(record: dict[str, Any]) -> np.ndarray:
    field = (
        "candidate_perfect_tracker_reference_first_heading_rad"
        if "candidate_perfect_tracker_reference_first_heading_rad" in record
        else "candidate_first_reference_heading_rad"
    )
    return _candidate_vector(record, field)


def _reward_metrics(record: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    rewards = record.get("dp_candidate_rewards")
    candidate_count = len(record.get("feasible_mask", []))
    if not isinstance(rewards, list) or len(rewards) != candidate_count:
        raise ValueError("Selection record lacks complete candidate rewards.")
    progress = np.asarray(
        [float(reward["progress"]) for reward in rewards],
        dtype=np.float64,
    )
    red = np.asarray(
        [max(-float(reward.get("red_light", 0.0)), 0.0) for reward in rewards],
        dtype=np.float64,
    )
    return progress, red


def _motion_arrays(records: list[dict[str, Any]]) -> dict[str, np.ndarray]:
    positions = np.asarray(
        [[float(row["x"]), float(row["y"])] for row in records],
        dtype=np.float64,
    )
    speed = np.asarray([float(row["speed"]) for row in records])
    heading = np.asarray([float(row["heading"]) for row in records])
    velocity = np.column_stack(
        [speed * np.cos(heading), speed * np.sin(heading)]
    )
    acceleration = np.diff(velocity, axis=0) / 0.1
    jerk = np.linalg.norm(np.diff(acceleration, axis=0) / 0.1, axis=1)
    heading_delta = np.arctan2(
        np.sin(np.diff(heading)),
        np.cos(np.diff(heading)),
    )
    lateral = np.abs(speed[1:] * heading_delta / 0.1)
    return {
        "positions": positions,
        "jerk": jerk,
        "lateral": lateral,
    }


def _window_distance(positions: np.ndarray, start: int, end: int) -> float:
    if end <= start:
        return 0.0
    return float(
        np.sum(np.linalg.norm(np.diff(positions[start : end + 1], axis=0), axis=1))
    )


def _window_mean_delta(
    baseline: np.ndarray,
    variant: np.ndarray,
    start: int,
    end: int,
) -> float | None:
    start = max(start, 0)
    end = min(end, len(baseline), len(variant))
    if end <= start:
        return None
    return float(np.mean(variant[start:end]) - np.mean(baseline[start:end]))


def _wrapped_delta(left: float, right: float) -> float:
    return math.atan2(math.sin(left - right), math.cos(left - right))


def _distribution(values: list[float | None]) -> dict[str, Any]:
    array = np.asarray(
        [float(value) for value in values if value is not None],
        dtype=np.float64,
    )
    if not array.size:
        return {
            "n": 0,
            "mean": None,
            "positive": 0,
            "negative": 0,
            "zero": 0,
        }
    return {
        "n": int(array.size),
        "mean": float(np.mean(array)),
        "positive": int(np.sum(array > 1e-12)),
        "negative": int(np.sum(array < -1e-12)),
        "zero": int(np.sum(np.abs(array) <= 1e-12)),
    }


def _error_summary(values: list[float]) -> dict[str, Any]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "n": int(array.size),
        "mean": float(np.mean(array)) if array.size else None,
        "p95": float(np.percentile(array, 95)) if array.size else None,
        "max": float(np.max(array)) if array.size else None,
    }


def _lag_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        lag = row["lag_from_latest_change"]
        key = "none" if lag is None else str(lag)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _validate_horizons(values: tuple[int, ...]) -> tuple[int, ...]:
    horizons = tuple(sorted(set(int(value) for value in values)))
    if not horizons or any(value <= 0 for value in horizons):
        raise ValueError("horizons must contain positive integers.")
    return horizons


def render_markdown(report: dict[str, Any]) -> str:
    pairing = report["pairing"]
    alignment = report["execution_alignment"]
    prestate = report["event_prestate"]
    red = report["planned_red_status_differences"]
    immediate = report["immediate_candidate_deltas"]
    lines = [
        "# DP+CAMP Tracker Branch Attribution",
        "",
        report["analysis"]["interpretation"],
        "",
        f"- Paired runs / steps: `{pairing['runs']}` / "
        f"`{pairing['total_steps']}`",
        f"- Changed runs / records: `{pairing['changed_runs']}` / "
        f"`{pairing['changed_records']}`",
        f"- Matched-prestate events: `{prestate['matched_records']}`",
        f"- Target-to-next-speed max error: "
        f"`{alignment['target_to_next_speed_error_mps']['max']:.6g}` m/s",
        f"- Heading-to-next-heading max error: "
        f"`{alignment['heading_to_next_heading_error_rad']['max']:.6g}` rad",
        f"- Paired planned-red status differences: `{red['total']}` "
        f"(variant extra `{red['variant_extra']}`)",
        "",
        "## Immediate Candidate Deltas",
        "",
        "| Quantity | Mean | Positive | Negative | Zero |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name, values in immediate.items():
        lines.append(
            f"| {name} | {values['mean']:.6g} | {values['positive']} | "
            f"{values['negative']} | {values['zero']} |"
        )
    lines.extend(
        [
            "",
            "## Window Responses",
            "",
            "| Horizon | Distance | Planned red steps | Vector jerk | Lateral | "
            "Contaminated |",
            "| ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for horizon, values in report["window_responses"].items():
        lines.append(
            f"| {horizon} | "
            f"{values['distance_delta_m']['mean']:.6g} | "
            f"{values['planned_red_step_delta']['mean']:.6g} | "
            f"{values['mean_vector_jerk_delta_mps3']['mean']:.6g} | "
            f"{values['mean_lateral_acceleration_delta_mps2']['mean']:.6g} | "
            f"{values['contaminated_events']} |"
        )
    lines.extend(["", report["analysis"]["causal_limit"], ""])
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    horizons = tuple(
        int(part.strip())
        for part in args.horizons.split(",")
        if part.strip()
    )
    report = compute_tracker_branch_attribution(
        args.baseline_root,
        args.variant_root,
        horizons=horizons,
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


if __name__ == "__main__":
    main()
