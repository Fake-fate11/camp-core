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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit outcome-free progress-preserving comfort opportunities in "
            "fixed Diffusion Planner candidate pools."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--reference_candidate_count", type=int, default=8)
    parser.add_argument("--step_reach_epsilon_m", type=float, default=0.0)
    parser.add_argument("--progress_epsilon_m", type=float, default=0.0)
    parser.add_argument("--planned_red_epsilon", type=float, default=0.0)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def compute_candidate_pool_opportunity_report(
    paths: list[Path],
    *,
    reference_candidate_count: int = 8,
    step_reach_epsilon_m: float = 0.0,
    progress_epsilon_m: float = 0.0,
    planned_red_epsilon: float = 0.0,
) -> dict[str, Any]:
    if reference_candidate_count <= 0:
        raise ValueError("reference_candidate_count must be positive.")
    epsilons = (
        step_reach_epsilon_m,
        progress_epsilon_m,
        planned_red_epsilon,
    )
    if any(not np.isfinite(value) or value < 0.0 for value in epsilons):
        raise ValueError("Opportunity epsilons must be finite and nonnegative.")

    log_count = 0
    record_count = 0
    fallback_records = 0
    feasible_records = 0
    selected_extra_records = 0
    weak_opportunity_records = 0
    joint_strict_opportunity_records = 0
    extra_weak_opportunity_records = 0
    extra_only_weak_opportunity_records = 0
    extra_joint_strict_opportunity_records = 0
    admissible_candidate_counts: list[int] = []
    weak_candidate_counts: list[int] = []
    joint_strict_candidate_counts: list[int] = []

    for log_path in iter_selection_log_paths(paths):
        log_count += 1
        records = json.loads(log_path.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            raise ValueError(f"{log_path} must contain a JSON list.")
        for record_idx, record in enumerate(records):
            record_count += 1
            outcomes = record.get("candidate_closed_loop_outcomes")
            if outcomes is not None:
                raise ValueError(
                    f"{log_path} record {record_idx} contains closed-loop "
                    "candidate outcomes; this audit must remain outcome-free."
                )
            feasible = np.asarray(
                record.get("feasible_mask"),
                dtype=bool,
            ).reshape(-1)
            candidate_count = feasible.size
            if candidate_count < reference_candidate_count:
                raise ValueError(
                    f"{log_path} record {record_idx} has {candidate_count} "
                    "candidates; expected at least "
                    f"{reference_candidate_count}."
                )
            if not feasible.any():
                fallback_records += 1
                continue
            feasible_records += 1
            selected_index = _selected_index(
                record,
                candidate_count,
                log_path,
                record_idx,
            )
            if not feasible[selected_index]:
                raise ValueError(
                    f"{log_path} record {record_idx} selected an infeasible "
                    "candidate without fallback."
                )
            selected_extra_records += int(
                selected_index >= reference_candidate_count
            )

            metrics = _candidate_metrics(
                record,
                candidate_count,
                log_path,
                record_idx,
            )
            selected = {
                name: float(values[selected_index])
                for name, values in metrics.items()
            }
            admissible = feasible.copy()
            admissible &= (
                metrics["step_reach"]
                >= selected["step_reach"] - float(step_reach_epsilon_m) - 1e-12
            )
            admissible &= (
                metrics["progress"]
                >= selected["progress"] - float(progress_epsilon_m) - 1e-12
            )
            admissible &= (
                metrics["planned_red"]
                <= selected["planned_red"] + float(planned_red_epsilon) + 1e-12
            )
            admissible_candidate_counts.append(int(admissible.sum()))

            jerk_nonworse = (
                metrics["jerk_excess"] <= selected["jerk_excess"] + 1e-12
            )
            lateral_nonworse = (
                metrics["lateral_absolute"]
                <= selected["lateral_absolute"] + 1e-12
            )
            jerk_strict = (
                metrics["jerk_excess"] < selected["jerk_excess"] - 1e-12
            )
            lateral_strict = (
                metrics["lateral_absolute"]
                < selected["lateral_absolute"] - 1e-12
            )
            weak = (
                admissible
                & jerk_nonworse
                & lateral_nonworse
                & (jerk_strict | lateral_strict)
            )
            joint_strict = admissible & jerk_strict & lateral_strict
            weak_candidate_counts.append(int(weak.sum()))
            joint_strict_candidate_counts.append(int(joint_strict.sum()))

            extra_mask = (
                np.arange(candidate_count, dtype=np.int64)
                >= reference_candidate_count
            )
            base_mask = ~extra_mask
            has_weak = bool(weak.any())
            has_joint_strict = bool(joint_strict.any())
            has_extra_weak = bool((weak & extra_mask).any())
            weak_opportunity_records += int(has_weak)
            joint_strict_opportunity_records += int(has_joint_strict)
            extra_weak_opportunity_records += int(has_extra_weak)
            extra_only_weak_opportunity_records += int(
                has_extra_weak and not (weak & base_mask).any()
            )
            extra_joint_strict_opportunity_records += int(
                (joint_strict & extra_mask).any()
            )

    if not log_count:
        raise ValueError("No selection logs were found.")
    denominator = feasible_records or 1
    return {
        "analysis": {
            "name": "dp_camp_candidate_pool_pareto_opportunity",
            "interpretation": (
                "Outcome-free fixed-candidate opportunity audit. It does not "
                "establish closed-loop improvement."
            ),
            "reference_candidate_count": reference_candidate_count,
            "expanded_candidate_indices_start_at": reference_candidate_count,
            "config": {
                "step_reach_epsilon_m": float(step_reach_epsilon_m),
                "progress_epsilon_m": float(progress_epsilon_m),
                "planned_red_epsilon": float(planned_red_epsilon),
            },
            "weak_comfort_pareto_definition": (
                "step reach/progress/red nonworse; jerk and lateral nonworse; "
                "at least one comfort metric strictly improves"
            ),
            "joint_strict_definition": (
                "step reach/progress/red nonworse; jerk and lateral both "
                "strictly improve"
            ),
        },
        "records": {
            "logs": log_count,
            "total": record_count,
            "feasible": feasible_records,
            "fallback": fallback_records,
        },
        "selection": {
            "selected_extra_records": selected_extra_records,
            "selected_extra_rate": selected_extra_records / denominator,
        },
        "opportunities": {
            "weak_records": weak_opportunity_records,
            "weak_rate": weak_opportunity_records / denominator,
            "joint_strict_records": joint_strict_opportunity_records,
            "joint_strict_rate": (
                joint_strict_opportunity_records / denominator
            ),
            "extra_weak_records": extra_weak_opportunity_records,
            "extra_weak_rate": extra_weak_opportunity_records / denominator,
            "extra_only_weak_records": extra_only_weak_opportunity_records,
            "extra_only_weak_rate": (
                extra_only_weak_opportunity_records / denominator
            ),
            "extra_joint_strict_records": (
                extra_joint_strict_opportunity_records
            ),
            "extra_joint_strict_rate": (
                extra_joint_strict_opportunity_records / denominator
            ),
        },
        "candidate_counts": {
            "mean_admissible": _mean(admissible_candidate_counts),
            "mean_weak": _mean(weak_candidate_counts),
            "mean_joint_strict": _mean(joint_strict_candidate_counts),
        },
    }


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


def _candidate_metrics(
    record: dict[str, Any],
    candidate_count: int,
    log_path: Path,
    record_idx: int,
) -> dict[str, np.ndarray]:
    rewards = record.get("dp_candidate_rewards")
    if not isinstance(rewards, list) or len(rewards) != candidate_count:
        raise ValueError(
            f"{log_path} record {record_idx} lacks complete DP rewards."
        )
    progress = np.asarray(
        [float(reward["progress"]) for reward in rewards],
        dtype=np.float64,
    )
    planned_red = np.asarray(
        [
            max(-float(reward.get("red_light", 0.0)), 0.0)
            for reward in rewards
        ],
        dtype=np.float64,
    )
    metrics = {
        "step_reach": _finite_vector(
            record,
            "candidate_step_reach",
            candidate_count,
            log_path,
            record_idx,
        ),
        "progress": progress,
        "planned_red": planned_red,
        "jerk_excess": _finite_vector(
            record,
            "candidate_dp_prior_jerk_excess_cost",
            candidate_count,
            log_path,
            record_idx,
        ),
        "lateral_absolute": _finite_vector(
            record,
            "candidate_horizon_lateral_acceleration_cost",
            candidate_count,
            log_path,
            record_idx,
        ),
    }
    if any(
        not np.all(np.isfinite(values)) or np.any(values < 0.0)
        for values in metrics.values()
    ):
        raise ValueError(
            f"{log_path} record {record_idx} has invalid candidate metrics."
        )
    return metrics


def _finite_vector(
    record: dict[str, Any],
    field: str,
    candidate_count: int,
    log_path: Path,
    record_idx: int,
) -> np.ndarray:
    values = np.asarray(record.get(field), dtype=np.float64).reshape(-1)
    if values.shape != (candidate_count,) or not np.all(np.isfinite(values)):
        raise ValueError(
            f"{log_path} record {record_idx} has invalid {field}."
        )
    return values


def _mean(values: list[int]) -> float | None:
    return float(np.mean(values)) if values else None


def render_markdown(report: dict[str, Any]) -> str:
    analysis = report["analysis"]
    records = report["records"]
    selection = report["selection"]
    opportunities = report["opportunities"]
    counts = report["candidate_counts"]
    lines = [
        "# DP+CAMP Expanded Candidate-Pool Opportunity Audit",
        "",
        analysis["interpretation"],
        "",
        f"- Reference candidate count: `{analysis['reference_candidate_count']}`",
        f"- Logs / records: `{records['logs']}` / `{records['total']}`",
        f"- Feasible / fallback records: `{records['feasible']}` / "
        f"`{records['fallback']}`",
        f"- Selected expanded-candidate rate: "
        f"`{selection['selected_extra_rate']:.6f}`",
        f"- Weak comfort-Pareto opportunity rate: "
        f"`{opportunities['weak_rate']:.6f}`",
        f"- Expanded-candidate weak opportunity rate: "
        f"`{opportunities['extra_weak_rate']:.6f}`",
        f"- Expanded-only weak opportunity rate: "
        f"`{opportunities['extra_only_weak_rate']:.6f}`",
        f"- Expanded-candidate joint-strict opportunity rate: "
        f"`{opportunities['extra_joint_strict_rate']:.6f}`",
        f"- Mean admissible / weak / joint-strict candidates: "
        f"`{counts['mean_admissible']:.6f}` / `{counts['mean_weak']:.6f}` / "
        f"`{counts['mean_joint_strict']:.6f}`",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    paths = [*args.root, *args.selection_log]
    if not paths:
        raise ValueError("At least one --root or --selection_log is required.")
    report = compute_candidate_pool_opportunity_report(
        paths,
        reference_candidate_count=args.reference_candidate_count,
        step_reach_epsilon_m=args.step_reach_epsilon_m,
        progress_epsilon_m=args.progress_epsilon_m,
        planned_red_epsilon=args.planned_red_epsilon,
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
