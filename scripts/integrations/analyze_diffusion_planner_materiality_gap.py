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
from scripts.integrations.analyze_diffusion_planner_first_step_graft_potential import (  # noqa: E402
    HORIZONS,
    TOL,
    _fmt,
    _mean_third_difference_norm,
    _min_deficit_candidate,
    _outcome_float,
    _path_length,
    _safety_joint_comfort_mask,
    _summary,
)


BOOL_OUTCOMES = (
    "collision",
    "near_miss",
    "lane_violation",
    "red_light_violation",
)
VECTOR_FIELDS = {
    "raw_route_progress_delta_m": "candidate_route_progress",
    "raw_step_reach_delta_m": "candidate_step_reach",
    "raw_dp_prior_jerk_excess_delta": "candidate_dp_prior_jerk_excess_cost",
    "raw_dp_prior_lateral_excess_delta": (
        "candidate_dp_prior_lateral_acceleration_excess_cost"
    ),
    "raw_horizon_lateral_delta": "candidate_horizon_lateral_acceleration_cost",
    "raw_horizon_yaw_delta": "candidate_horizon_yaw_rate_cost",
    "tracker_first_step_reach_delta_m": (
        "candidate_perfect_tracker_first_step_reach_m"
    ),
    "tracker_tail_average_speed_delta_mps": (
        "candidate_perfect_tracker_tail_average_speed_mps"
    ),
    "tracker_target_speed_delta_mps": "candidate_perfect_tracker_target_speed_mps",
    "tracker_command_jerk_delta_mps3": (
        "candidate_perfect_tracker_jerk_magnitude_mps3"
    ),
    "tracker_command_lateral_delta_mps2": (
        "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2"
    ),
    "tracker_command_yaw_rate_delta_rps": (
        "candidate_perfect_tracker_yaw_rate_magnitude_rps"
    ),
}
ROLLOUT_METRICS = (
    "distance_m",
    "mean_vector_jerk_mps3",
    "max_vector_jerk_mps3",
    "mean_lateral_acceleration_mps2",
    "max_lateral_acceleration_mps2",
)
PREFIX_DISTANCE_THRESHOLDS_M = (0.001, 0.01, 0.1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnose where safety-preserving joint-comfort donor candidates "
            "differ from the selected candidate: raw DP proxies, "
            "PerfectTracker command, postprocessed prefix, rollout shadows, "
            "and closed-loop outcome labels."
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
    rows: list[dict[str, float]] = []
    no_donor = 0
    for record in nonfallback:
        donor_mask = _safety_joint_comfort_mask(record)
        if not donor_mask.any():
            no_donor += 1
            continue
        donor = _min_deficit_candidate(record, donor_mask)
        rows.append(_row(record, donor))

    return {
        "analysis": {
            "name": "dp_camp_materiality_gap_v1",
            "role": (
                "offline materiality attribution for safety-preserving "
                "joint-comfort oracle donor candidates"
            ),
            "label": label,
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": (
                "candidate outcomes choose oracle donors for diagnosis only; "
                "all reported current-tick layers are measured from stored log "
                "fields"
            ),
            "closed_loop_outcome_source": (
                "candidate_closed_loop_outcomes are computed from raw DP "
                "candidate trajectories, while recent projection screens "
                "operate on PerfectTracker postprocessed reference prefixes"
            ),
            "convexity_boundary": (
                "This is an audit over a fixed finite candidate set. It makes "
                "no Benders or trajectory-coordinate convexity claim."
            ),
        },
        "records": {
            "logs": len(log_paths),
            "total": len(records),
            "nonfallback": len(nonfallback),
            "fallback": len(records) - len(nonfallback),
            "with_oracle_donor": len(rows),
            "without_oracle_donor": no_donor,
        },
        "summary": {key: _summary([row[key] for row in rows]) for key in _row_keys()},
        "rates": _rates(rows),
    }


def _load_record(record: dict[str, Any], label: str) -> dict[str, Any]:
    candidate_count = int(record.get("num_candidates", 0))
    if candidate_count <= 0:
        raise ValueError(f"{label} must declare positive num_candidates.")
    selected_index = int(record.get("selected_index"))
    if selected_index < 0 or selected_index >= candidate_count:
        raise ValueError(f"{label} selected_index is out of range.")
    prefix = np.asarray(
        record.get("candidate_perfect_tracker_postprocessed_reference_prefix"),
        dtype=np.float64,
    )
    if prefix.ndim != 3 or prefix.shape[0] != candidate_count or prefix.shape[2] < 2:
        raise ValueError(
            f"{label} candidate_perfect_tracker_postprocessed_reference_prefix "
            "must have shape [K,T,D>=2]."
        )
    if prefix.shape[1] < max(HORIZONS):
        raise ValueError(f"{label} reference prefix is shorter than H{max(HORIZONS)}.")
    if not np.all(np.isfinite(prefix[:, :, :2])):
        raise ValueError(f"{label} prefix xy values must be finite.")

    loaded: dict[str, Any] = {
        "selected_index": selected_index,
        "feasible": _bool_vector(
            record.get("feasible_mask"),
            candidate_count,
            f"{label} feasible_mask",
        ),
        "outcomes": _outcomes(record.get("candidate_closed_loop_outcomes"), candidate_count, label),
        "prefix_xy": prefix[:, :, :2],
        "rollout": _rollout(record, candidate_count, label),
    }
    for output_key, field in VECTOR_FIELDS.items():
        loaded[output_key] = _vector(record.get(field), candidate_count, f"{label} {field}")
    return loaded


def _outcomes(values: Any, size: int, label: str) -> list[dict[str, Any]]:
    if not isinstance(values, list) or len(values) != size:
        raise ValueError(f"{label} must contain {size} candidate outcomes.")
    for index, outcome in enumerate(values):
        if not isinstance(outcome, dict) or outcome.get("candidate_index") != index:
            raise ValueError(f"{label} outcome indices must be contiguous.")
    return values


def _rollout(record: dict[str, Any], size: int, label: str) -> dict[str, dict[str, np.ndarray]]:
    raw = record.get("candidate_perfect_tracker_open_loop_rollout")
    if not isinstance(raw, dict):
        raise ValueError(f"{label} is missing candidate_perfect_tracker_open_loop_rollout.")
    result: dict[str, dict[str, np.ndarray]] = {}
    for horizon in HORIZONS:
        payload = raw.get(str(horizon), raw.get(horizon))
        if not isinstance(payload, dict):
            raise ValueError(f"{label} is missing rollout horizon {horizon}.")
        result[str(horizon)] = {
            metric: _vector(payload.get(metric), size, f"{label} H{horizon} {metric}")
            for metric in ROLLOUT_METRICS
        }
    return result


def _row(record: dict[str, Any], donor: int) -> dict[str, float]:
    selected = record["selected_index"]
    selected_prefix = record["prefix_xy"][selected, : max(HORIZONS)]
    donor_prefix = record["prefix_xy"][donor, : max(HORIZONS)]
    prefix_delta = donor_prefix - selected_prefix
    selected_progress = _outcome_float(record, selected, "progress_m")
    donor_progress = _outcome_float(record, donor, "progress_m")
    row: dict[str, float] = {
        "outcome_progress_delta_m": donor_progress - selected_progress,
        "outcome_progress_deficit_m": max(0.0, selected_progress - donor_progress),
        "outcome_jerk_delta_mps3": _outcome_float(record, donor, "mean_jerk_mps3")
        - _outcome_float(record, selected, "mean_jerk_mps3"),
        "outcome_lateral_delta_mps2": _outcome_float(
            record,
            donor,
            "mean_lateral_acceleration_mps2",
        )
        - _outcome_float(record, selected, "mean_lateral_acceleration_mps2"),
        "outcome_value_delta": _outcome_float(record, donor, "value")
        - _outcome_float(record, selected, "value"),
        "prefix_max_xy_distance_m": float(np.linalg.norm(prefix_delta, axis=1).max()),
        "prefix_mean_xy_distance_m": float(np.linalg.norm(prefix_delta, axis=1).mean()),
        "prefix_jerk_proxy_delta": _mean_third_difference_norm(donor_prefix)
        - _mean_third_difference_norm(selected_prefix),
    }
    for output_key in VECTOR_FIELDS:
        values = record[output_key]
        row[output_key] = float(values[donor] - values[selected])
    for horizon in HORIZONS:
        row[f"prefix_h{horizon}_displacement_delta_m"] = float(
            np.linalg.norm(donor_prefix[horizon - 1])
            - np.linalg.norm(selected_prefix[horizon - 1])
        )
        row[f"prefix_h{horizon}_path_delta_m"] = (
            _path_length(donor_prefix[:horizon])
            - _path_length(selected_prefix[:horizon])
        )
        for metric in ROLLOUT_METRICS:
            values = record["rollout"][str(horizon)][metric]
            row[f"rollout_h{horizon}_{metric}_delta"] = float(
                values[donor] - values[selected]
            )
    return row


def _row_keys() -> tuple[str, ...]:
    keys = [
        "outcome_progress_delta_m",
        "outcome_progress_deficit_m",
        "outcome_jerk_delta_mps3",
        "outcome_lateral_delta_mps2",
        "outcome_value_delta",
        *VECTOR_FIELDS.keys(),
        "prefix_max_xy_distance_m",
        "prefix_mean_xy_distance_m",
        "prefix_jerk_proxy_delta",
    ]
    for horizon in HORIZONS:
        keys.extend(
            [
                f"prefix_h{horizon}_displacement_delta_m",
                f"prefix_h{horizon}_path_delta_m",
            ]
        )
        for metric in ROLLOUT_METRICS:
            keys.append(f"rollout_h{horizon}_{metric}_delta")
    return tuple(keys)


def _rates(rows: list[dict[str, float]]) -> dict[str, float | int]:
    denom = max(len(rows), 1)
    if not rows:
        return {
            "records": 0,
            "raw_jerk_proxy_improvement_rate": 0.0,
            "raw_lateral_proxy_improvement_rate": 0.0,
            "tracker_jerk_proxy_improvement_rate": 0.0,
            "tracker_lateral_proxy_improvement_rate": 0.0,
            "prefix_jerk_proxy_improvement_rate": 0.0,
            "rollout_h3_jerk_improvement_rate": 0.0,
            "rollout_h3_lateral_improvement_rate": 0.0,
        }
    rates: dict[str, float | int] = {
        "records": len(rows),
        "raw_jerk_proxy_improvement_rate": _rate(
            rows,
            "raw_dp_prior_jerk_excess_delta",
            less_than_zero=True,
        ),
        "raw_lateral_proxy_improvement_rate": _rate(
            rows,
            "raw_horizon_lateral_delta",
            less_than_zero=True,
        ),
        "tracker_jerk_proxy_improvement_rate": _rate(
            rows,
            "tracker_command_jerk_delta_mps3",
            less_than_zero=True,
        ),
        "tracker_lateral_proxy_improvement_rate": _rate(
            rows,
            "tracker_command_lateral_delta_mps2",
            less_than_zero=True,
        ),
        "prefix_jerk_proxy_improvement_rate": _rate(
            rows,
            "prefix_jerk_proxy_delta",
            less_than_zero=True,
        ),
        "rollout_h3_jerk_improvement_rate": _rate(
            rows,
            "rollout_h3_mean_vector_jerk_mps3_delta",
            less_than_zero=True,
        ),
        "rollout_h3_lateral_improvement_rate": _rate(
            rows,
            "rollout_h3_mean_lateral_acceleration_mps2_delta",
            less_than_zero=True,
        ),
        "lower_tracker_target_speed_rate": _rate(
            rows,
            "tracker_target_speed_delta_mps",
            less_than_zero=True,
        ),
    }
    for threshold in PREFIX_DISTANCE_THRESHOLDS_M:
        label = str(threshold).replace(".", "p")
        rates[f"prefix_max_distance_ge_{label}_m_rate"] = (
            sum(row["prefix_max_xy_distance_m"] >= threshold for row in rows) / denom
        )
    return rates


def _rate(
    rows: list[dict[str, float]],
    key: str,
    *,
    less_than_zero: bool,
) -> float:
    if less_than_zero:
        return sum(row[key] < -TOL for row in rows) / max(len(rows), 1)
    return sum(row[key] > TOL for row in rows) / max(len(rows), 1)


def _vector(values: Any, size: int, label: str) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64).reshape(-1)
    if array.size != size:
        raise ValueError(f"{label} has {array.size} values; expected {size}.")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{label} must contain finite values.")
    return array


def _bool_vector(values: Any, size: int, label: str) -> np.ndarray:
    raw = np.asarray(values, dtype=object).reshape(-1)
    if raw.shape != (size,) or not all(isinstance(value, (bool, np.bool_)) for value in raw):
        raise ValueError(f"{label} must contain {size} booleans.")
    return raw.astype(bool)


def render_markdown(report: dict[str, Any]) -> str:
    label = report["analysis"].get("label") or "candidate set"
    records = report["records"]
    rates = report["rates"]
    summary = report["summary"]
    lines = [
        "# DP CAMP Materiality Gap",
        "",
        f"- Label: `{label}`",
        f"- Logs: {records['logs']}",
        f"- Records: {records['total']}",
        f"- Nonfallback records: {records['nonfallback']}",
        f"- With oracle donors: {records['with_oracle_donor']}",
        "",
        "Oracle donors are safety-nonworse candidates that strictly improve "
        "closed-loop outcome jerk and lateral acceleration with minimum "
        "outcome progress deficit. Outcome labels choose donors for this "
        "diagnostic only.",
        "",
        "## Layer Agreement",
        "",
        "| Layer proxy | Improvement rate | Mean delta | P50 | P90 |",
        "| --- | ---: | ---: | ---: | ---: |",
        _layer_row(
            "Raw DP jerk excess",
            rates["raw_jerk_proxy_improvement_rate"],
            summary["raw_dp_prior_jerk_excess_delta"],
        ),
        _layer_row(
            "Raw DP horizon lateral",
            rates["raw_lateral_proxy_improvement_rate"],
            summary["raw_horizon_lateral_delta"],
        ),
        _layer_row(
            "Tracker command jerk",
            rates["tracker_jerk_proxy_improvement_rate"],
            summary["tracker_command_jerk_delta_mps3"],
        ),
        _layer_row(
            "Tracker command lateral",
            rates["tracker_lateral_proxy_improvement_rate"],
            summary["tracker_command_lateral_delta_mps2"],
        ),
        _layer_row(
            "Postprocessed prefix jerk proxy",
            rates["prefix_jerk_proxy_improvement_rate"],
            summary["prefix_jerk_proxy_delta"],
        ),
        _layer_row(
            "H3 rollout jerk",
            rates["rollout_h3_jerk_improvement_rate"],
            summary["rollout_h3_mean_vector_jerk_mps3_delta"],
        ),
        _layer_row(
            "H3 rollout lateral",
            rates["rollout_h3_lateral_improvement_rate"],
            summary["rollout_h3_mean_lateral_acceleration_mps2_delta"],
        ),
        "",
        "## Key Deltas",
        "",
        "| Quantity | Mean | P50 | P90 | P95 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for label_text, key in (
        ("Outcome progress delta m", "outcome_progress_delta_m"),
        ("Outcome jerk delta m/s^3", "outcome_jerk_delta_mps3"),
        ("Outcome lateral delta m/s^2", "outcome_lateral_delta_mps2"),
        ("Raw route progress delta m", "raw_route_progress_delta_m"),
        ("Raw step reach delta m", "raw_step_reach_delta_m"),
        ("Tracker target speed delta m/s", "tracker_target_speed_delta_mps"),
        ("Prefix max xy distance m", "prefix_max_xy_distance_m"),
        ("Prefix H10 displacement delta m", "prefix_h10_displacement_delta_m"),
        ("Rollout H3 distance delta m", "rollout_h3_distance_m_delta"),
        ("Rollout H3 jerk delta m/s^3", "rollout_h3_mean_vector_jerk_mps3_delta"),
        (
            "Rollout H3 lateral delta m/s^2",
            "rollout_h3_mean_lateral_acceleration_mps2_delta",
        ),
    ):
        lines.append(_summary_row(label_text, summary[key]))
    lines.extend(
        [
            "",
            "## Prefix Materiality",
            "",
            "| Threshold | Rate |",
            "| ---: | ---: |",
        ]
    )
    for threshold in PREFIX_DISTANCE_THRESHOLDS_M:
        rate_key = f"prefix_max_distance_ge_{str(threshold).replace('.', 'p')}_m_rate"
        lines.append(f"| >= {threshold:.3f} m | {rates[rate_key]:.6f} |")
    lines.append("")
    return "\n".join(lines)


def _layer_row(
    label: str,
    rate: float | int,
    values: dict[str, float | int | None],
) -> str:
    return (
        f"| {label} | {float(rate):.6f} | {_fmt(values['mean'])} | "
        f"{_fmt(values['p50'])} | {_fmt(values['p90'])} |"
    )


def _summary_row(label: str, values: dict[str, float | int | None]) -> str:
    return (
        f"| {label} | {_fmt(values['mean'])} | {_fmt(values['p50'])} | "
        f"{_fmt(values['p90'])} | {_fmt(values['p95'])} |"
    )


if __name__ == "__main__":
    main()
