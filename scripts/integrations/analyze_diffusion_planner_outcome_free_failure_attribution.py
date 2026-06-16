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
    TOL,
    _fmt,
    _mean_third_difference_norm,
    _summary,
)
from scripts.integrations.analyze_diffusion_planner_outcome_free_bounded_selector import (  # noqa: E402
    SCREENS,
    _admissible_mask,
    _choose,
    _load_record,
    _result_row,
)


DEFAULT_SCREENS = (
    "balanced_lateral_jerk_nondegrading",
    "relaxed_lateral_jerk_nondegrading",
)
VECTOR_FEATURES = (
    {
        "key": "raw_dp_prior_lateral_excess_delta",
        "field": "candidate_dp_prior_lateral_acceleration_excess_cost",
        "guard": "lower",
    },
    {
        "key": "raw_dp_prior_acceleration_excess_delta",
        "field": "candidate_dp_prior_acceleration_excess_cost",
        "guard": "lower",
    },
    {
        "key": "raw_dp_prior_deviation_delta",
        "field": "candidate_dp_prior_deviation_cost",
        "guard": "lower",
    },
    {
        "key": "raw_dp_prior_yaw_rate_excess_delta",
        "field": "candidate_dp_prior_yaw_rate_excess_cost",
        "guard": "lower",
    },
    {
        "key": "raw_horizon_yaw_rate_delta",
        "field": "candidate_horizon_yaw_rate_cost",
        "guard": "lower",
    },
    {
        "key": "tracker_command_jerk_delta_mps3",
        "field": "candidate_perfect_tracker_jerk_magnitude_mps3",
        "guard": "lower",
    },
    {
        "key": "tracker_command_lateral_delta_mps2",
        "field": "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2",
        "guard": "lower",
    },
    {
        "key": "tracker_command_yaw_rate_delta_rps",
        "field": "candidate_perfect_tracker_yaw_rate_magnitude_rps",
        "guard": "lower",
    },
    {
        "key": "tracker_command_abs_acceleration_delta_mps2",
        "field": "candidate_perfect_tracker_acceleration_mps2",
        "guard": "lower_abs",
    },
    {
        "key": "tracker_tail_average_speed_delta_mps",
        "field": "candidate_perfect_tracker_tail_average_speed_mps",
        "guard": "higher",
    },
)
ROLLOUT_HORIZONS = (3, 5, 10)
ROLLOUT_FEATURES = (
    ("mean_vector_jerk_mps3", "lower"),
    ("max_vector_jerk_mps3", "lower"),
    ("mean_lateral_acceleration_mps2", "lower"),
    ("max_lateral_acceleration_mps2", "lower"),
    ("distance_m", "higher"),
)
DERIVED_FEATURES = (
    {"key": "prefix_jerk_proxy_delta", "guard": "lower"},
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Attribute posterior joint-comfort failures for outcome-free "
            "bounded selector screens. Selection uses current-tick finite "
            "candidate fields only; outcomes classify pass/fail posteriorly."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--screen", action="append", default=[])
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        [*args.root, *args.selection_log],
        label=args.label,
        screen_names=tuple(args.screen) or DEFAULT_SCREENS,
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
    label: str | None = None,
    screen_names: tuple[str, ...] = DEFAULT_SCREENS,
) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    screens = _selected_screens(screen_names)
    rows_by_screen: dict[str, list[dict[str, Any]]] = {screen["name"]: [] for screen in screens}
    total_records = 0
    nonfallback_records = 0
    fallback_records = 0
    for log_path in log_paths:
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for record_index, raw_record in enumerate(payload):
            label_text = f"{log_path} record {record_index}"
            total_records += 1
            record = _load_record(raw_record, label_text)
            fallback = not record["feasible"].any()
            fallback_records += int(fallback)
            nonfallback_records += int(not fallback)
            if fallback:
                continue
            features = _feature_vectors(raw_record, int(raw_record["num_candidates"]), label_text)
            for screen in screens:
                admissible = _admissible_mask(record, screen)
                if not admissible.any():
                    continue
                chosen = _choose(record, admissible)
                result = _result_row(record, chosen, opportunity=True, fallback=False)
                if not result["changed"]:
                    continue
                rows_by_screen[screen["name"]].append(
                    _attribution_row(
                        result,
                        record,
                        chosen,
                        features,
                        log_path=log_path,
                        record_index=record_index,
                    )
                )
    return {
        "analysis": {
            "name": "dp_camp_outcome_free_failure_attribution_v1",
            "role": (
                "offline attribution of posterior joint-comfort failures for "
                "outcome-free finite-candidate selector screens"
            ),
            "label": label,
            "screens": [screen["name"] for screen in screens],
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": (
                "outcomes classify posterior pass/fail only; all guard "
                "features are fixed current-tick candidate diagnostics"
            ),
            "convexity_boundary": (
                "Each audited guard feature is a fixed finite-candidate "
                "constant at the current tick. If atomized as a nonnegative "
                "cost, CAMP scoring remains affine in w over the fixed "
                "candidate set. This is not Benders and makes no "
                "trajectory-coordinate convexity claim."
            ),
        },
        "records": {
            "logs": len(log_paths),
            "total": total_records,
            "nonfallback": nonfallback_records,
            "fallback": fallback_records,
        },
        "screens": [_screen_report(name, rows) for name, rows in rows_by_screen.items()],
    }


def _selected_screens(screen_names: tuple[str, ...]) -> tuple[dict[str, Any], ...]:
    by_name = {screen["name"]: screen for screen in SCREENS}
    missing = [name for name in screen_names if name not in by_name]
    if missing:
        raise ValueError(f"Unknown screen(s): {', '.join(missing)}")
    return tuple(by_name[name] for name in screen_names)


def _feature_vectors(
    record: dict[str, Any],
    candidate_count: int,
    label: str,
) -> dict[str, np.ndarray]:
    features: dict[str, np.ndarray] = {}
    for spec in VECTOR_FEATURES:
        raw_values = record.get(str(spec["field"]))
        if raw_values is None:
            continue
        values = _vector(raw_values, candidate_count, f"{label} {spec['field']}")
        if spec["guard"] == "lower_abs":
            values = np.abs(values)
        features[str(spec["key"])] = values

    prefix = np.asarray(
        record.get("candidate_perfect_tracker_postprocessed_reference_prefix"),
        dtype=np.float64,
    )
    if prefix.ndim == 3 and prefix.shape[0] == candidate_count and prefix.shape[2] >= 2:
        prefix_xy = prefix[:, :, :2]
        if np.all(np.isfinite(prefix_xy)):
            features["prefix_jerk_proxy_delta"] = np.asarray(
                [_mean_third_difference_norm(prefix_xy[index]) for index in range(candidate_count)],
                dtype=np.float64,
            )

    rollout = record.get("candidate_perfect_tracker_open_loop_rollout")
    if isinstance(rollout, dict):
        for horizon in ROLLOUT_HORIZONS:
            payload = rollout.get(str(horizon), rollout.get(horizon))
            if not isinstance(payload, dict):
                continue
            for metric, _guard in ROLLOUT_FEATURES:
                raw_values = payload.get(metric)
                if raw_values is None:
                    continue
                features[f"rollout_h{horizon}_{metric}_delta"] = _vector(
                    raw_values,
                    candidate_count,
                    f"{label} H{horizon} {metric}",
                )
    return features


def _attribution_row(
    result: dict[str, Any],
    record: dict[str, Any],
    chosen: int,
    feature_vectors: dict[str, np.ndarray],
    *,
    log_path: Path,
    record_index: int,
) -> dict[str, Any]:
    selected = int(record["selected_index"])
    feature_deltas = {
        key: float(values[chosen] - values[selected])
        for key, values in feature_vectors.items()
        if values.size > max(chosen, selected) and np.isfinite(values[chosen] - values[selected])
    }
    return {
        "log_path": str(log_path),
        "record_index": int(record_index),
        "selected_index": selected,
        "chosen_index": int(chosen),
        "posterior_joint_comfort_improvement": bool(
            result["posterior_joint_comfort_improvement"]
        ),
        "outcome_safety_regression": bool(result["outcome_safety_regression"]),
        "outcome_progress_delta_m": float(result["outcome_progress_m_delta"]),
        "outcome_jerk_delta_mps3": float(result["outcome_mean_jerk_mps3_delta"]),
        "outcome_lateral_delta_mps2": float(
            result["outcome_mean_lateral_acceleration_mps2_delta"]
        ),
        "outcome_value_delta": float(result["outcome_value_delta"]),
        "progress_proxy_loss_m": float(result["progress_proxy_loss_m"]),
        "target_speed_loss_mps": float(result["target_speed_loss_mps"]),
        "h10_displacement_loss_m": float(result["h10_displacement_loss_m"]),
        "raw_lateral_delta": float(result["raw_lateral_delta"]),
        "raw_jerk_delta": float(result["raw_jerk_delta"]),
        "feature_deltas": feature_deltas,
    }


def _screen_report(name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    successes = [row for row in rows if row["posterior_joint_comfort_improvement"]]
    failures = [row for row in rows if not row["posterior_joint_comfort_improvement"]]
    return {
        "name": name,
        "records": {
            "changed": len(rows),
            "posterior_joint_comfort_success": len(successes),
            "posterior_joint_comfort_failure": len(failures),
        },
        "failure_modes": _failure_modes(failures),
        "outcome_delta_summary": {
            group: _outcome_summary(group_rows)
            for group, group_rows in (
                ("all", rows),
                ("success", successes),
                ("failure", failures),
            )
        },
        "feature_delta_summary": _feature_delta_summary(rows, successes, failures),
        "single_nonworse_guards": _single_guard_reports(rows, successes, failures),
        "failure_examples": _failure_examples(failures),
    }


def _failure_modes(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "safety_regression": sum(int(row["outcome_safety_regression"]) for row in rows),
        "jerk_not_improved": sum(int(row["outcome_jerk_delta_mps3"] >= -TOL) for row in rows),
        "lateral_not_improved": sum(
            int(row["outcome_lateral_delta_mps2"] >= -TOL) for row in rows
        ),
        "both_comfort_not_improved": sum(
            int(
                row["outcome_jerk_delta_mps3"] >= -TOL
                and row["outcome_lateral_delta_mps2"] >= -TOL
            )
            for row in rows
        ),
    }


def _outcome_summary(rows: list[dict[str, Any]]) -> dict[str, dict[str, float | int | None]]:
    return {
        "progress_m": _summary([float(row["outcome_progress_delta_m"]) for row in rows]),
        "jerk_mps3": _summary([float(row["outcome_jerk_delta_mps3"]) for row in rows]),
        "lateral_mps2": _summary([float(row["outcome_lateral_delta_mps2"]) for row in rows]),
        "value": _summary([float(row["outcome_value_delta"]) for row in rows]),
    }


def _feature_delta_summary(
    rows: list[dict[str, Any]],
    successes: list[dict[str, Any]],
    failures: list[dict[str, Any]],
) -> dict[str, dict[str, dict[str, float | int | None]]]:
    result: dict[str, dict[str, dict[str, float | int | None]]] = {}
    for key in _feature_keys(rows):
        result[key] = {
            "all": _summary(_feature_values(rows, key)),
            "success": _summary(_feature_values(successes, key)),
            "failure": _summary(_feature_values(failures, key)),
        }
    return result


def _single_guard_reports(
    rows: list[dict[str, Any]],
    successes: list[dict[str, Any]],
    failures: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    reports = []
    for key in _feature_keys(rows):
        spec = _feature_spec(key)
        applicable = [row for row in rows if key in row["feature_deltas"]]
        if not applicable:
            continue
        kept = [row for row in applicable if _passes_guard(float(row["feature_deltas"][key]), spec)]
        kept_success = [row for row in kept if row["posterior_joint_comfort_improvement"]]
        kept_failure = [row for row in kept if not row["posterior_joint_comfort_improvement"]]
        applicable_success = [row for row in successes if key in row["feature_deltas"]]
        applicable_failure = [row for row in failures if key in row["feature_deltas"]]
        removed_failure = len(applicable_failure) - len(kept_failure)
        removed_success = len(applicable_success) - len(kept_success)
        reports.append(
            {
                "feature": key,
                "guard": spec["guard"],
                "applicable": len(applicable),
                "kept": len(kept),
                "kept_success": len(kept_success),
                "kept_failure": len(kept_failure),
                "removed_success": removed_success,
                "removed_failure": removed_failure,
                "success_keep_rate": len(kept_success) / max(len(applicable_success), 1),
                "failure_removal_rate": removed_failure / max(len(applicable_failure), 1),
                "precision_after_guard": len(kept_success) / max(len(kept), 1),
                "kept_outcome_delta_summary": _outcome_summary(kept),
            }
        )
    reports.sort(
        key=lambda item: (
            float(item["failure_removal_rate"]),
            float(item["precision_after_guard"]),
            float(item["success_keep_rate"]),
        ),
        reverse=True,
    )
    return reports


def _feature_spec(key: str) -> dict[str, str]:
    for spec in (*VECTOR_FEATURES, *DERIVED_FEATURES):
        if spec["key"] == key:
            return {"guard": str(spec["guard"])}
    for horizon in ROLLOUT_HORIZONS:
        prefix = f"rollout_h{horizon}_"
        if key.startswith(prefix):
            metric_name = key[len(prefix) : -len("_delta")]
            for metric, guard in ROLLOUT_FEATURES:
                if metric == metric_name:
                    return {"guard": guard}
    return {"guard": "lower"}


def _passes_guard(delta: float, spec: dict[str, str]) -> bool:
    guard = spec["guard"]
    if guard in {"lower", "lower_abs"}:
        return delta <= TOL
    if guard == "higher":
        return delta >= -TOL
    raise ValueError(f"Unsupported guard direction: {guard}")


def _failure_examples(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(
        rows,
        key=lambda row: (
            float(row["outcome_jerk_delta_mps3"]),
            float(row["outcome_lateral_delta_mps2"]),
            float(row["outcome_value_delta"]),
        ),
        reverse=True,
    )
    return [
        {
            "log_path": row["log_path"],
            "record_index": row["record_index"],
            "selected_index": row["selected_index"],
            "chosen_index": row["chosen_index"],
            "outcome_progress_delta_m": row["outcome_progress_delta_m"],
            "outcome_jerk_delta_mps3": row["outcome_jerk_delta_mps3"],
            "outcome_lateral_delta_mps2": row["outcome_lateral_delta_mps2"],
            "progress_proxy_loss_m": row["progress_proxy_loss_m"],
            "target_speed_loss_mps": row["target_speed_loss_mps"],
            "h10_displacement_loss_m": row["h10_displacement_loss_m"],
            "feature_deltas": row["feature_deltas"],
        }
        for row in ordered[:10]
    ]


def _feature_keys(rows: list[dict[str, Any]]) -> list[str]:
    keys = sorted({key for row in rows for key in row["feature_deltas"]})
    return keys


def _feature_values(rows: list[dict[str, Any]], key: str) -> list[float]:
    return [float(row["feature_deltas"][key]) for row in rows if key in row["feature_deltas"]]


def _vector(values: Any, size: int, label: str) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64).reshape(-1)
    if array.size != size:
        raise ValueError(f"{label} has {array.size} values; expected {size}.")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{label} must contain finite values.")
    return array


def render_markdown(report: dict[str, Any]) -> str:
    label = report["analysis"].get("label") or "candidate set"
    records = report["records"]
    lines = [
        "# DP CAMP Outcome-Free Failure Attribution",
        "",
        f"- Label: `{label}`",
        f"- Logs: {records['logs']}",
        f"- Records: {records['total']}",
        f"- Nonfallback records: {records['nonfallback']}",
        "",
        "This audit replays the stored outcome-free selector screens and uses "
        "candidate outcomes only to classify changed records as posterior "
        "joint-comfort success or failure.",
        "",
    ]
    for screen in report["screens"]:
        rec = screen["records"]
        modes = screen["failure_modes"]
        lines.extend(
            [
                f"## `{screen['name']}`",
                "",
                f"- Changed records: {rec['changed']}",
                f"- Posterior joint-comfort successes: {rec['posterior_joint_comfort_success']}",
                f"- Posterior joint-comfort failures: {rec['posterior_joint_comfort_failure']}",
                f"- Failure modes: safety {modes['safety_regression']}, "
                f"jerk-not-improved {modes['jerk_not_improved']}, "
                f"lateral-not-improved {modes['lateral_not_improved']}, "
                f"both {modes['both_comfort_not_improved']}",
                "",
                "### Single Nonworse Guards",
                "",
                "| Feature | Guard | Kept | Kept success | Kept failure | Success keep | Failure removal | Precision after guard |",
                "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for guard in screen["single_nonworse_guards"]:
            lines.append(
                f"| `{guard['feature']}` | `{guard['guard']}` | {guard['kept']} | "
                f"{guard['kept_success']} | {guard['kept_failure']} | "
                f"{guard['success_keep_rate']:.6f} | "
                f"{guard['failure_removal_rate']:.6f} | "
                f"{guard['precision_after_guard']:.6f} |"
            )
        lines.extend(
            [
                "",
                "### Pass/Fail Feature Means",
                "",
                "| Feature | Success mean | Failure mean | All P95 |",
                "| --- | ---: | ---: | ---: |",
            ]
        )
        for key, summary in list(screen["feature_delta_summary"].items())[:16]:
            lines.append(
                f"| `{key}` | {_fmt(summary['success']['mean'])} | "
                f"{_fmt(summary['failure']['mean'])} | {_fmt(summary['all']['p95'])} |"
            )
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
