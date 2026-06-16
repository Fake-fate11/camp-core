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


BOOL_OUTCOMES = (
    "collision",
    "near_miss",
    "lane_violation",
    "red_light_violation",
)
REQUIRED_VECTOR_FIELDS = (
    "candidate_step_reach",
    "candidate_perfect_tracker_first_step_reach_m",
    "candidate_perfect_tracker_tail_average_speed_mps",
    "candidate_perfect_tracker_target_speed_mps",
    "candidate_perfect_tracker_jerk_magnitude_mps3",
    "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2",
    "candidate_dp_prior_jerk_excess_cost",
    "candidate_horizon_lateral_acceleration_cost",
    "candidate_horizon_union_planned_red_light_cost",
    "candidate_red_stopping_margin_cost",
)
ROLLOUT_HORIZONS = ("3", "5", "10")
TOL = 1e-12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Attribute outcome progress deficits for safety-preserving "
            "joint-comfort DP+CAMP candidates to current-tick PerfectTracker "
            "and proxy quantities. Uses candidate outcomes as offline labels "
            "only."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze([*args.root, *args.selection_log], label=args.label)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")


def analyze(paths: list[Path], *, label: str | None = None) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    records: list[dict[str, Any]] = []
    for log_path in log_paths:
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for index, record in enumerate(payload):
            records.append(_load_record(record, f"{log_path} record {index}"))

    nonfallback = [record for record in records if record["feasible"].any()]
    selected_rows: list[dict[str, float | bool]] = []
    no_joint_comfort = 0
    for record in nonfallback:
        mask = _safety_joint_comfort_mask(record)
        if not mask.any():
            no_joint_comfort += 1
            continue
        best = _min_deficit_candidate(record, mask)
        selected_rows.append(_candidate_delta_row(record, best))

    return {
        "analysis": {
            "name": "dp_camp_progress_deficit_attribution_v1",
            "role": "offline attribution of progress deficits for candidate-generation design",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": "candidate outcomes are offline labels only",
            "candidate_rule": (
                "for each nonfallback record, select the safety-preserving "
                "joint-comfort candidate with minimum outcome progress deficit; "
                "ties break by lower deficit, lower jerk, lower lateral, then "
                "candidate index"
            ),
        },
        "records": {
            "logs": len(log_paths),
            "total": len(records),
            "nonfallback": len(nonfallback),
            "fallback": len(records) - len(nonfallback),
            "with_safety_joint_comfort": len(selected_rows),
            "without_safety_joint_comfort": no_joint_comfort,
        },
        "progress_deficit_m": _summary(
            [float(row["progress_deficit_m"]) for row in selected_rows]
        ),
        "delta_summary": {
            key: _summary([float(row[key]) for row in selected_rows])
            for key in _delta_keys()
        },
        "rates": _rates(selected_rows),
    }


def _load_record(record: dict[str, Any], label: str) -> dict[str, Any]:
    candidate_count = int(record.get("num_candidates", 0))
    if candidate_count <= 0:
        raise ValueError(f"{label} must declare positive num_candidates.")
    selected_index = int(record.get("selected_index"))
    if selected_index < 0 or selected_index >= candidate_count:
        raise ValueError(f"{label} selected_index is out of range.")
    loaded = {
        "selected_index": selected_index,
        "feasible": _bool_vector(
            record.get("feasible_mask"), candidate_count, f"{label} feasible_mask"
        ),
        "outcomes": _outcomes(record.get("candidate_closed_loop_outcomes"), candidate_count, label),
        "restart_push": _bool_vector(
            record.get("candidate_perfect_tracker_restart_push"),
            candidate_count,
            f"{label} candidate_perfect_tracker_restart_push",
        ),
    }
    for field in REQUIRED_VECTOR_FIELDS:
        loaded[field] = _vector(record.get(field), candidate_count, f"{label} {field}")
    loaded["rollout_distance"] = {
        horizon: _rollout_vector(record, horizon, candidate_count, label)
        for horizon in ROLLOUT_HORIZONS
    }
    return loaded


def _outcomes(values: Any, size: int, label: str) -> list[dict[str, Any]]:
    if not isinstance(values, list) or len(values) != size:
        raise ValueError(f"{label} must contain {size} candidate outcomes.")
    for index, outcome in enumerate(values):
        if not isinstance(outcome, dict) or outcome.get("candidate_index") != index:
            raise ValueError(f"{label} outcome indices must be contiguous.")
    return values


def _rollout_vector(
    record: dict[str, Any],
    horizon: str,
    size: int,
    label: str,
) -> np.ndarray:
    rollout = record.get("candidate_perfect_tracker_open_loop_rollout")
    if not isinstance(rollout, dict) or horizon not in rollout:
        raise ValueError(f"{label} is missing rollout horizon {horizon}.")
    horizon_payload = rollout[horizon]
    if not isinstance(horizon_payload, dict):
        raise ValueError(f"{label} rollout horizon {horizon} must be an object.")
    return _vector(
        horizon_payload.get("distance_m"),
        size,
        f"{label} rollout distance H{horizon}",
    )


def _safety_joint_comfort_mask(record: dict[str, Any]) -> np.ndarray:
    selected = record["selected_index"]
    size = record["feasible"].size
    mask = record["feasible"].copy()
    mask[selected] = False
    for field in BOOL_OUTCOMES:
        selected_value = bool(record["outcomes"][selected].get(field))
        mask &= np.asarray(
            [
                float(bool(record["outcomes"][idx].get(field)))
                <= float(selected_value)
                for idx in range(size)
            ],
            dtype=bool,
        )
    jerk = np.asarray(
        [_outcome_float(record, idx, "mean_jerk_mps3") for idx in range(size)]
    )
    lateral = np.asarray(
        [
            _outcome_float(record, idx, "mean_lateral_acceleration_mps2")
            for idx in range(size)
        ]
    )
    return mask & (jerk < jerk[selected] - TOL) & (lateral < lateral[selected] - TOL)


def _min_deficit_candidate(record: dict[str, Any], mask: np.ndarray) -> int:
    selected = record["selected_index"]
    indices = np.flatnonzero(mask)
    selected_progress = _outcome_float(record, selected, "progress_m")
    deficits = np.asarray(
        [
            max(0.0, selected_progress - _outcome_float(record, int(idx), "progress_m"))
            for idx in indices
        ],
        dtype=np.float64,
    )
    jerk = np.asarray(
        [_outcome_float(record, int(idx), "mean_jerk_mps3") for idx in indices],
        dtype=np.float64,
    )
    lateral = np.asarray(
        [
            _outcome_float(record, int(idx), "mean_lateral_acceleration_mps2")
            for idx in indices
        ],
        dtype=np.float64,
    )
    order = np.lexsort((indices, lateral, jerk, deficits))
    return int(indices[order[0]])


def _candidate_delta_row(record: dict[str, Any], candidate: int) -> dict[str, float | bool]:
    selected = record["selected_index"]
    row: dict[str, float | bool] = {
        "progress_deficit_m": max(
            0.0,
            _outcome_float(record, selected, "progress_m")
            - _outcome_float(record, candidate, "progress_m"),
        ),
        "outcome_progress_delta_m": _outcome_float(record, candidate, "progress_m")
        - _outcome_float(record, selected, "progress_m"),
        "outcome_jerk_delta_mps3": _outcome_float(record, candidate, "mean_jerk_mps3")
        - _outcome_float(record, selected, "mean_jerk_mps3"),
        "outcome_lateral_delta_mps2": _outcome_float(
            record,
            candidate,
            "mean_lateral_acceleration_mps2",
        )
        - _outcome_float(record, selected, "mean_lateral_acceleration_mps2"),
        "candidate_restart_push": bool(record["restart_push"][candidate]),
        "selected_restart_push": bool(record["restart_push"][selected]),
        "restart_push_delta": float(record["restart_push"][candidate])
        - float(record["restart_push"][selected]),
    }
    for output_key, field in (
        ("candidate_step_reach_delta_m", "candidate_step_reach"),
        (
            "perfect_tracker_first_step_reach_delta_m",
            "candidate_perfect_tracker_first_step_reach_m",
        ),
        (
            "perfect_tracker_tail_average_speed_delta_mps",
            "candidate_perfect_tracker_tail_average_speed_mps",
        ),
        (
            "perfect_tracker_target_speed_delta_mps",
            "candidate_perfect_tracker_target_speed_mps",
        ),
        (
            "perfect_tracker_command_jerk_delta_mps3",
            "candidate_perfect_tracker_jerk_magnitude_mps3",
        ),
        (
            "perfect_tracker_command_lateral_delta_mps2",
            "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2",
        ),
        ("dp_prior_jerk_excess_delta", "candidate_dp_prior_jerk_excess_cost"),
        ("horizon_lateral_delta", "candidate_horizon_lateral_acceleration_cost"),
        ("union_red_delta", "candidate_horizon_union_planned_red_light_cost"),
        ("red_stopping_delta", "candidate_red_stopping_margin_cost"),
    ):
        row[output_key] = float(record[field][candidate] - record[field][selected])
    for horizon in ROLLOUT_HORIZONS:
        row[f"rollout_h{horizon}_distance_delta_m"] = float(
            record["rollout_distance"][horizon][candidate]
            - record["rollout_distance"][horizon][selected]
        )
    return row


def _delta_keys() -> tuple[str, ...]:
    return (
        "outcome_progress_delta_m",
        "outcome_jerk_delta_mps3",
        "outcome_lateral_delta_mps2",
        "candidate_step_reach_delta_m",
        "perfect_tracker_first_step_reach_delta_m",
        "perfect_tracker_tail_average_speed_delta_mps",
        "perfect_tracker_target_speed_delta_mps",
        "perfect_tracker_command_jerk_delta_mps3",
        "perfect_tracker_command_lateral_delta_mps2",
        "rollout_h3_distance_delta_m",
        "rollout_h5_distance_delta_m",
        "rollout_h10_distance_delta_m",
        "dp_prior_jerk_excess_delta",
        "horizon_lateral_delta",
        "union_red_delta",
        "red_stopping_delta",
    )


def _rates(rows: list[dict[str, float | bool]]) -> dict[str, float | int]:
    denom = max(len(rows), 1)
    if not rows:
        return {
            "records": 0,
            "candidate_progress_no_loss_rate": 0.0,
            "candidate_lower_target_speed_rate": 0.0,
            "candidate_lower_first_step_reach_rate": 0.0,
            "candidate_lower_h3_distance_rate": 0.0,
            "candidate_restart_push_rate": 0.0,
            "selected_restart_push_rate": 0.0,
            "restart_push_changed_rate": 0.0,
        }
    return {
        "records": len(rows),
        "candidate_progress_no_loss_rate": sum(
            float(row["progress_deficit_m"]) <= TOL for row in rows
        )
        / denom,
        "candidate_lower_target_speed_rate": sum(
            float(row["perfect_tracker_target_speed_delta_mps"]) < -TOL
            for row in rows
        )
        / denom,
        "candidate_lower_first_step_reach_rate": sum(
            float(row["perfect_tracker_first_step_reach_delta_m"]) < -TOL
            for row in rows
        )
        / denom,
        "candidate_lower_h3_distance_rate": sum(
            float(row["rollout_h3_distance_delta_m"]) < -TOL for row in rows
        )
        / denom,
        "candidate_restart_push_rate": sum(
            bool(row["candidate_restart_push"]) for row in rows
        )
        / denom,
        "selected_restart_push_rate": sum(
            bool(row["selected_restart_push"]) for row in rows
        )
        / denom,
        "restart_push_changed_rate": sum(
            bool(row["candidate_restart_push"]) != bool(row["selected_restart_push"])
            for row in rows
        )
        / denom,
    }


def _outcome_float(record: dict[str, Any], index: int, field: str) -> float:
    value = float(record["outcomes"][index].get(field))
    if not np.isfinite(value) or value < 0.0:
        raise ValueError(f"Outcome {field} must be finite and nonnegative.")
    return value


def _vector(values: Any, size: int, label: str) -> np.ndarray:
    vector = np.asarray(values, dtype=np.float64).reshape(-1)
    if vector.shape != (size,):
        raise ValueError(f"{label} must have shape [{size}].")
    if not np.all(np.isfinite(vector)) or np.any(vector < 0.0):
        raise ValueError(f"{label} must be finite and nonnegative.")
    return vector


def _bool_vector(values: Any, size: int, label: str) -> np.ndarray:
    raw = np.asarray(values, dtype=object).reshape(-1)
    if raw.shape != (size,) or not all(isinstance(value, (bool, np.bool_)) for value in raw):
        raise ValueError(f"{label} must contain {size} booleans.")
    return raw.astype(bool)


def _summary(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {
            "count": 0,
            "mean": None,
            "p50": None,
            "p90": None,
            "p95": None,
        }
    arr = np.asarray(values, dtype=np.float64)
    return {
        "count": int(arr.size),
        "mean": float(np.mean(arr)),
        "p50": float(np.percentile(arr, 50.0)),
        "p90": float(np.percentile(arr, 90.0)),
        "p95": float(np.percentile(arr, 95.0)),
    }


def _fmt(value: float | int | None) -> str:
    return "n/a" if value is None else f"{float(value):.6f}"


def render_markdown(report: dict[str, Any]) -> str:
    label = report["analysis"].get("label") or "candidate set"
    records = report["records"]
    rates = report["rates"]
    lines = [
        "# DP CAMP Progress-Deficit Attribution",
        "",
        f"- Label: `{label}`",
        f"- Logs: {records['logs']}",
        f"- Records: {records['total']}",
        f"- Nonfallback records: {records['nonfallback']}",
        f"- With safety-preserving joint-comfort candidates: "
        f"{records['with_safety_joint_comfort']}",
        "",
        "For each qualifying record, this report compares the selected "
        "candidate with the safety-preserving joint-comfort candidate that has "
        "the smallest outcome progress deficit. Candidate outcomes are offline "
        "labels only.",
        "",
        f"- No-progress-loss rate: `{rates['candidate_progress_no_loss_rate']:.6f}`",
        f"- Lower PerfectTracker target-speed rate: "
        f"`{rates['candidate_lower_target_speed_rate']:.6f}`",
        f"- Lower first-step reach rate: "
        f"`{rates['candidate_lower_first_step_reach_rate']:.6f}`",
        f"- Lower H3 rollout-distance rate: "
        f"`{rates['candidate_lower_h3_distance_rate']:.6f}`",
        f"- Candidate restart-push rate: `{rates['candidate_restart_push_rate']:.6f}`",
        f"- Selected restart-push rate: `{rates['selected_restart_push_rate']:.6f}`",
        f"- Restart-push changed rate: `{rates['restart_push_changed_rate']:.6f}`",
        "",
        "| Quantity | Mean | P50 | P90 | P95 |",
        "| --- | ---: | ---: | ---: | ---: |",
        _summary_row("Progress deficit m", report["progress_deficit_m"]),
    ]
    for label_text, key in (
        ("Outcome progress delta m", "outcome_progress_delta_m"),
        ("Outcome jerk delta m/s^3", "outcome_jerk_delta_mps3"),
        ("Outcome lateral delta m/s^2", "outcome_lateral_delta_mps2"),
        ("Candidate step reach delta m", "candidate_step_reach_delta_m"),
        (
            "PerfectTracker first-step reach delta m",
            "perfect_tracker_first_step_reach_delta_m",
        ),
        (
            "PerfectTracker target speed delta m/s",
            "perfect_tracker_target_speed_delta_mps",
        ),
        (
            "PerfectTracker tail average speed delta m/s",
            "perfect_tracker_tail_average_speed_delta_mps",
        ),
        ("H3 rollout distance delta m", "rollout_h3_distance_delta_m"),
        ("H5 rollout distance delta m", "rollout_h5_distance_delta_m"),
        ("H10 rollout distance delta m", "rollout_h10_distance_delta_m"),
        ("Command jerk delta m/s^3", "perfect_tracker_command_jerk_delta_mps3"),
        (
            "Command lateral delta m/s^2",
            "perfect_tracker_command_lateral_delta_mps2",
        ),
        ("DP-prior jerk-excess delta", "dp_prior_jerk_excess_delta"),
        ("Horizon lateral delta", "horizon_lateral_delta"),
        ("Union-red delta", "union_red_delta"),
        ("Red-stopping delta", "red_stopping_delta"),
    ):
        lines.append(_summary_row(label_text, report["delta_summary"][key]))
    lines.append("")
    return "\n".join(lines)


def _summary_row(label: str, values: dict[str, float | int | None]) -> str:
    return (
        f"| {label} | {_fmt(values['mean'])} | {_fmt(values['p50'])} | "
        f"{_fmt(values['p90'])} | {_fmt(values['p95'])} |"
    )


if __name__ == "__main__":
    main()
