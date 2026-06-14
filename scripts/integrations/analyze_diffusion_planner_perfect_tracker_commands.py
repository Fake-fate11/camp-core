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


COMMAND_FIELDS = {
    "target_speed": "candidate_perfect_tracker_target_speed_mps",
    "jerk": "candidate_perfect_tracker_jerk_magnitude_mps3",
    "lateral": (
        "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2"
    ),
    "yaw_rate": "candidate_perfect_tracker_yaw_rate_magnitude_rps",
    "old_jerk": "candidate_dp_prior_jerk_excess_cost",
    "old_lateral": "candidate_horizon_lateral_acceleration_cost",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit outcome-free PerfectTracker command opportunities in fixed "
            "Diffusion Planner candidate pools."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--target_speed_epsilon_mps", type=float, default=0.0)
    parser.add_argument("--planned_red_epsilon", type=float, default=0.0)
    parser.add_argument("--jerk_epsilon_mps3", type=float, default=0.0)
    parser.add_argument(
        "--lateral_acceleration_epsilon_mps2",
        type=float,
        default=0.0,
    )
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def compute_perfect_tracker_command_report(
    paths: list[Path],
    *,
    target_speed_epsilon_mps: float = 0.0,
    planned_red_epsilon: float = 0.0,
    jerk_epsilon_mps3: float = 0.0,
    lateral_acceleration_epsilon_mps2: float = 0.0,
) -> dict[str, Any]:
    epsilons = {
        "target_speed_epsilon_mps": target_speed_epsilon_mps,
        "planned_red_epsilon": planned_red_epsilon,
        "jerk_epsilon_mps3": jerk_epsilon_mps3,
        "lateral_acceleration_epsilon_mps2": (
            lateral_acceleration_epsilon_mps2
        ),
    }
    if any(
        not np.isfinite(value) or value < 0.0
        for value in epsilons.values()
    ):
        raise ValueError(
            "PerfectTracker opportunity epsilons must be finite and nonnegative."
        )

    log_count = 0
    record_count = 0
    nonfallback_records = 0
    fallback_records = 0
    dominance_records = 0
    joint_strict_records = 0
    selected_restart_records = 0
    candidate0_restart_records = 0
    restart_changed_records = 0
    selected_target_below_candidate0_records = 0
    selected_values = {name: [] for name in COMMAND_FIELDS}
    candidate0_values = {name: [] for name in COMMAND_FIELDS}
    feasible_values = {name: [] for name in COMMAND_FIELDS}
    dominance_candidate_counts: list[int] = []
    joint_strict_candidate_counts: list[int] = []
    shadow_latencies_ms: list[float] = []

    for log_path in iter_selection_log_paths(paths):
        log_count += 1
        _validate_shadow_summary(log_path)
        records = json.loads(log_path.read_text(encoding="utf-8"))
        if not isinstance(records, list) or not records:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for record_idx, record in enumerate(records):
            record_count += 1
            if record.get("candidate_closed_loop_outcomes") is not None:
                raise ValueError(
                    f"{log_path} record {record_idx} contains closed-loop "
                    "candidate outcomes; this analysis must remain outcome-free."
                )
            feasible = np.asarray(
                record.get("feasible_mask"),
                dtype=bool,
            ).reshape(-1)
            candidate_count = feasible.size
            if candidate_count == 0:
                raise ValueError(
                    f"{log_path} record {record_idx} has no candidates."
                )
            selected_index = _selected_index(
                record,
                candidate_count,
                log_path,
                record_idx,
            )
            metrics = {
                name: _finite_vector(
                    record,
                    field,
                    candidate_count,
                    log_path,
                    record_idx,
                    nonnegative=True,
                )
                for name, field in COMMAND_FIELDS.items()
            }
            planned_red = _planned_red(
                record,
                candidate_count,
                log_path,
                record_idx,
            )
            restart = _restart_flags(
                record,
                candidate_count,
                log_path,
                record_idx,
            )
            for name, values in metrics.items():
                selected_values[name].append(float(values[selected_index]))
                candidate0_values[name].append(float(values[0]))
                feasible_values[name].extend(values[feasible].tolist())

            selected_restart_records += int(restart[selected_index])
            candidate0_restart_records += int(restart[0])
            restart_changed_records += int(
                restart[selected_index] != restart[0]
            )
            selected_target_below_candidate0_records += int(
                metrics["target_speed"][selected_index]
                < metrics["target_speed"][0] - 1e-12
            )
            shadow_latencies_ms.append(
                _finite_scalar(
                    record,
                    "latency_ms_shadow_perfect_tracker_command",
                    log_path,
                    record_idx,
                    nonnegative=True,
                )
            )

            if not feasible.any():
                fallback_records += 1
                continue
            if not feasible[selected_index]:
                raise ValueError(
                    f"{log_path} record {record_idx} selected an infeasible "
                    "candidate without fallback."
                )
            nonfallback_records += 1
            selected = {
                name: values[selected_index]
                for name, values in metrics.items()
            }
            admissible = feasible.copy()
            admissible &= (
                metrics["target_speed"]
                >= selected["target_speed"]
                - float(target_speed_epsilon_mps)
                - 1e-12
            )
            admissible &= (
                planned_red
                <= planned_red[selected_index]
                + float(planned_red_epsilon)
                + 1e-12
            )
            jerk_nonworse = (
                metrics["jerk"]
                <= selected["jerk"] + float(jerk_epsilon_mps3) + 1e-12
            )
            lateral_nonworse = (
                metrics["lateral"]
                <= selected["lateral"]
                + float(lateral_acceleration_epsilon_mps2)
                + 1e-12
            )
            jerk_strict = metrics["jerk"] < selected["jerk"] - 1e-12
            lateral_strict = (
                metrics["lateral"] < selected["lateral"] - 1e-12
            )
            dominance = (
                admissible
                & jerk_nonworse
                & lateral_nonworse
                & (jerk_strict | lateral_strict)
            )
            joint_strict = admissible & jerk_strict & lateral_strict
            dominance_candidate_counts.append(int(dominance.sum()))
            joint_strict_candidate_counts.append(int(joint_strict.sum()))
            dominance_records += int(dominance.any())
            joint_strict_records += int(joint_strict.any())

    if not log_count:
        raise ValueError("No selection logs were found.")
    feasible_denominator = nonfallback_records or 1
    record_denominator = record_count or 1
    return {
        "analysis": {
            "name": "dp_camp_perfect_tracker_command_shadow_v1",
            "interpretation": (
                "Outcome-free fixed-candidate command audit. It identifies "
                "opportunities but does not establish closed-loop improvement."
            ),
            "selection_effect": False,
            "config": {key: float(value) for key, value in epsilons.items()},
            "dominance_definition": (
                "target speed and planned red nonworse; command jerk and "
                "lateral nonworse; at least one comfort quantity strictly lower"
            ),
            "joint_strict_definition": (
                "target speed and planned red nonworse; command jerk and "
                "lateral both strictly lower"
            ),
        },
        "records": {
            "logs": log_count,
            "total": record_count,
            "nonfallback": nonfallback_records,
            "fallback": fallback_records,
        },
        "opportunities": {
            "dominance_records": dominance_records,
            "dominance_rate": dominance_records / feasible_denominator,
            "joint_strict_records": joint_strict_records,
            "joint_strict_rate": joint_strict_records / feasible_denominator,
            "mean_dominance_candidates": _mean(dominance_candidate_counts),
            "mean_joint_strict_candidates": _mean(
                joint_strict_candidate_counts
            ),
        },
        "selection_behavior": {
            "selected_restart_rate": (
                selected_restart_records / record_denominator
            ),
            "candidate0_restart_rate": (
                candidate0_restart_records / record_denominator
            ),
            "restart_changed_rate": restart_changed_records / record_denominator,
            "selected_target_below_candidate0_rate": (
                selected_target_below_candidate0_records / record_denominator
            ),
        },
        "selected_means": {
            name: _mean(values) for name, values in selected_values.items()
        },
        "candidate0_means": {
            name: _mean(values) for name, values in candidate0_values.items()
        },
        "selected_minus_candidate0_means": {
            name: float(
                np.mean(
                    np.asarray(selected_values[name], dtype=np.float64)
                    - np.asarray(candidate0_values[name], dtype=np.float64)
                )
            )
            for name in COMMAND_FIELDS
        },
        "feasible_correlations": {
            "command_jerk_vs_horizon_jerk_excess": _correlation(
                feasible_values["jerk"],
                feasible_values["old_jerk"],
            ),
            "command_lateral_vs_horizon_lateral": _correlation(
                feasible_values["lateral"],
                feasible_values["old_lateral"],
            ),
            "command_yaw_rate_vs_horizon_lateral": _correlation(
                feasible_values["yaw_rate"],
                feasible_values["old_lateral"],
            ),
        },
        "latency_ms": {
            "mean": _mean(shadow_latencies_ms),
            "p95": (
                float(np.percentile(shadow_latencies_ms, 95))
                if shadow_latencies_ms
                else None
            ),
            "max": max(shadow_latencies_ms) if shadow_latencies_ms else None,
        },
    }


def _validate_shadow_summary(log_path: Path) -> None:
    summary_path = log_path.with_name("camp_validation_summary.json")
    if not summary_path.is_file():
        raise ValueError(f"Missing completed-run summary for {log_path}.")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    metadata = summary.get("camp_shadow_perfect_tracker_command")
    if (
        summary.get("advance_mode") != "perfect"
        or not isinstance(metadata, dict)
        or metadata.get("enabled") is not True
        or metadata.get("selection_effect") is not False
        or metadata.get("tracker_class")
        != "scenario_generation.mpc_tracker.PerfectTracker"
    ):
        raise ValueError(
            f"{summary_path} does not certify an outcome-free "
            "PerfectTracker command shadow."
        )


def _selected_index(
    record: dict[str, Any],
    candidate_count: int,
    log_path: Path,
    record_idx: int,
) -> int:
    selected_index = record.get("selected_index")
    if (
        isinstance(selected_index, bool)
        or not isinstance(selected_index, int)
        or not 0 <= selected_index < candidate_count
    ):
        raise ValueError(
            f"{log_path} record {record_idx} has invalid selected_index."
        )
    return selected_index


def _planned_red(
    record: dict[str, Any],
    candidate_count: int,
    log_path: Path,
    record_idx: int,
) -> np.ndarray:
    rewards = record.get("dp_candidate_rewards")
    if not isinstance(rewards, list) or len(rewards) != candidate_count:
        raise ValueError(
            f"{log_path} record {record_idx} lacks complete DP rewards."
        )
    values = np.asarray(
        [
            max(-float(reward.get("red_light", 0.0)), 0.0)
            for reward in rewards
        ],
        dtype=np.float64,
    )
    if not np.all(np.isfinite(values)):
        raise ValueError(
            f"{log_path} record {record_idx} has invalid planned-red values."
        )
    return values


def _restart_flags(
    record: dict[str, Any],
    candidate_count: int,
    log_path: Path,
    record_idx: int,
) -> np.ndarray:
    values = record.get("candidate_perfect_tracker_restart_push")
    if (
        not isinstance(values, list)
        or len(values) != candidate_count
        or any(not isinstance(value, bool) for value in values)
    ):
        raise ValueError(
            f"{log_path} record {record_idx} has invalid restart flags."
        )
    return np.asarray(values, dtype=bool)


def _finite_vector(
    record: dict[str, Any],
    field: str,
    candidate_count: int,
    log_path: Path,
    record_idx: int,
    *,
    nonnegative: bool,
) -> np.ndarray:
    values = np.asarray(record.get(field), dtype=np.float64).reshape(-1)
    if (
        values.shape != (candidate_count,)
        or not np.all(np.isfinite(values))
        or (nonnegative and np.any(values < 0.0))
    ):
        raise ValueError(
            f"{log_path} record {record_idx} has invalid {field}."
        )
    return values


def _finite_scalar(
    record: dict[str, Any],
    field: str,
    log_path: Path,
    record_idx: int,
    *,
    nonnegative: bool,
) -> float:
    try:
        value = float(record.get(field))
    except (TypeError, ValueError):
        value = float("nan")
    if not np.isfinite(value) or (nonnegative and value < 0.0):
        raise ValueError(
            f"{log_path} record {record_idx} has invalid {field}."
        )
    return value


def _mean(values: list[float] | list[int]) -> float | None:
    return float(np.mean(values)) if values else None


def _correlation(left: list[float], right: list[float]) -> float | None:
    x = np.asarray(left, dtype=np.float64)
    y = np.asarray(right, dtype=np.float64)
    if (
        x.shape != y.shape
        or x.size < 2
        or float(np.std(x)) <= 1e-12
        or float(np.std(y)) <= 1e-12
    ):
        return None
    return float(np.corrcoef(x, y)[0, 1])


def render_markdown(report: dict[str, Any]) -> str:
    records = report["records"]
    opportunities = report["opportunities"]
    behavior = report["selection_behavior"]
    correlations = report["feasible_correlations"]
    latency = report["latency_ms"]
    lines = [
        "# DP+CAMP PerfectTracker Command-Shadow Audit",
        "",
        report["analysis"]["interpretation"],
        "",
        f"- Logs / records: `{records['logs']}` / `{records['total']}`",
        f"- Nonfallback / fallback: `{records['nonfallback']}` / "
        f"`{records['fallback']}`",
        f"- Dominance opportunity rate: "
        f"`{opportunities['dominance_rate']:.6f}`",
        f"- Joint-strict opportunity rate: "
        f"`{opportunities['joint_strict_rate']:.6f}`",
        f"- Selected target below candidate 0 rate: "
        f"`{behavior['selected_target_below_candidate0_rate']:.6f}`",
        f"- Restart-change rate: `{behavior['restart_changed_rate']:.6f}`",
        f"- Command jerk vs horizon jerk correlation: "
        f"`{_format_optional(correlations['command_jerk_vs_horizon_jerk_excess'])}`",
        f"- Command lateral vs horizon lateral correlation: "
        f"`{_format_optional(correlations['command_lateral_vs_horizon_lateral'])}`",
        f"- Shadow latency mean / p95 / max: "
        f"`{_format_optional(latency['mean'])}` / "
        f"`{_format_optional(latency['p95'])}` / "
        f"`{_format_optional(latency['max'])}` ms",
    ]
    return "\n".join(lines) + "\n"


def _format_optional(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.6f}"


def main() -> None:
    args = parse_args()
    paths = [*args.root, *args.selection_log]
    if not paths:
        raise ValueError("At least one --root or --selection_log is required.")
    report = compute_perfect_tracker_command_report(
        paths,
        target_speed_epsilon_mps=args.target_speed_epsilon_mps,
        planned_red_epsilon=args.planned_red_epsilon,
        jerk_epsilon_mps3=args.jerk_epsilon_mps3,
        lateral_acceleration_epsilon_mps2=(
            args.lateral_acceleration_epsilon_mps2
        ),
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
