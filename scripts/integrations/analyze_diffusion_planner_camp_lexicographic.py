#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

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
from scripts.integrations.run_diffusion_planner_camp_replay import (  # noqa: E402
    _apply_lexicographic_admissible_filter,
)


MetricExtractor = Callable[[dict[str, Any]], np.ndarray]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline fixed-candidate audit of the nonempty CAMP lexicographic "
            "preselection. This is a definition screen, not closed-loop evidence."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument(
        "--ignore_infeasibility_reason",
        action="append",
        default=[],
        help=(
            "Reason introduced by an earlier experimental guard that should be "
            "removed when reconstructing the base hard-feasible set."
        ),
    )
    parser.add_argument("--progress_epsilon_m", type=float, required=True)
    parser.add_argument("--red_epsilon", type=float, default=0.0)
    parser.add_argument("--jerk_epsilon", type=float, default=0.0)
    parser.add_argument("--lateral_epsilon", type=float, default=0.0)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def compute_lexicographic_counterfactual_report(
    paths: list[Path],
    *,
    ignored_infeasibility_reasons: tuple[str, ...] = (),
    progress_epsilon_m: float,
    red_epsilon: float,
    jerk_epsilon: float,
    lateral_epsilon: float,
) -> dict[str, Any]:
    epsilons = (
        progress_epsilon_m,
        red_epsilon,
        jerk_epsilon,
        lateral_epsilon,
    )
    if any(not np.isfinite(value) or value < 0.0 for value in epsilons):
        raise ValueError("Lexicographic epsilons must be finite and nonnegative.")
    ignored = frozenset(ignored_infeasibility_reasons)
    rows: list[dict[str, Any]] = []
    log_count = 0
    record_count = 0
    all_infeasible_records = 0
    reason_counts: dict[str, int] = {}
    stage_count_rows: list[dict[str, int]] = []

    for log_path in iter_selection_log_paths(paths):
        log_count += 1
        records = json.loads(log_path.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            raise ValueError(f"{log_path} must contain a JSON list.")
        for record_idx, record in enumerate(records):
            record_count += 1
            reasons = record.get("infeasibility_reasons")
            if not isinstance(reasons, list):
                raise ValueError(
                    f"{log_path} record {record_idx} lacks infeasibility reasons."
                )
            candidate_count = len(reasons)
            for candidate_reasons in reasons:
                for reason in candidate_reasons:
                    reason_counts[str(reason)] = reason_counts.get(str(reason), 0) + 1
            base_feasible = np.asarray(
                [
                    all(str(reason) in ignored for reason in candidate_reasons)
                    for candidate_reasons in reasons
                ],
                dtype=bool,
            )
            scores = _finite_vector(
                record,
                "scores",
                candidate_count,
                log_path,
                record_idx,
            )
            if not base_feasible.any():
                all_infeasible_records += 1
                continue
            metrics = _candidate_metrics(
                record,
                candidate_count,
                log_path,
                record_idx,
            )
            baseline_index = int(
                np.argmin(np.where(base_feasible, scores, np.inf))
            )
            filtered, _, stage_counts = _apply_lexicographic_admissible_filter(
                base_feasible,
                tuple(tuple() for _ in range(candidate_count)),
                candidate_progress=metrics["progress"],
                candidate_planned_red_light_cost=metrics["planned_red"],
                candidate_dp_prior_jerk_excess_cost=metrics["jerk_excess"],
                candidate_horizon_lateral_acceleration_cost=metrics[
                    "lateral_absolute"
                ],
                progress_epsilon_m=progress_epsilon_m,
                red_epsilon=red_epsilon,
                jerk_epsilon=jerk_epsilon,
                lateral_epsilon=lateral_epsilon,
            )
            if filtered is None or not np.asarray(filtered, dtype=bool).any():
                raise RuntimeError("Lexicographic preselection created fallback.")
            filtered_arr = np.asarray(filtered, dtype=bool)
            selected_index = int(
                np.argmin(np.where(filtered_arr, scores, np.inf))
            )
            if stage_counts is None:
                raise RuntimeError("Lexicographic stage counts were not produced.")
            stage_count_rows.append(stage_counts)
            rows.append(
                {
                    "baseline_index": baseline_index,
                    "selected_index": selected_index,
                    "source_selected_index": int(record["selected_index"]),
                    "baseline": {
                        **{
                            key: float(values[baseline_index])
                            for key, values in metrics.items()
                        },
                        "score": float(scores[baseline_index]),
                    },
                    "selected": {
                        **{
                            key: float(values[selected_index])
                            for key, values in metrics.items()
                        },
                        "score": float(scores[selected_index]),
                    },
                }
            )

    if not rows:
        raise ValueError("No base-feasible records were available for analysis.")
    metric_names = tuple(rows[0]["baseline"])
    return {
        "analysis": {
            "name": "dp_camp_lexicographic_fixed_candidate_counterfactual",
            "interpretation": (
                "Offline fixed-candidate definition screen only; candidate metrics "
                "do not establish matched closed-loop improvement."
            ),
            "base_feasible_reconstruction": {
                "ignored_infeasibility_reasons": sorted(ignored),
                "all_other_reasons_remain_hard_constraints": True,
            },
            "contract": {
                "order": ["progress", "planned_red", "jerk", "lateral"],
                "finite_candidate": True,
                "preselection_independent_of_camp_weights": True,
                "nonempty_when_base_feasible": True,
                "new_fallback_records": 0,
            },
            "config": {
                "progress_epsilon_m": float(progress_epsilon_m),
                "planned_red_epsilon": float(red_epsilon),
                "jerk_epsilon": float(jerk_epsilon),
                "lateral_epsilon": float(lateral_epsilon),
            },
        },
        "records": {
            "logs": log_count,
            "total": record_count,
            "base_feasible": len(rows),
            "base_all_infeasible": all_infeasible_records,
            "reason_counts": reason_counts,
        },
        "selection": {
            "change_vs_base_rate": float(
                np.mean(
                    [
                        row["selected_index"] != row["baseline_index"]
                        for row in rows
                    ]
                )
            ),
            "change_vs_source_rate": float(
                np.mean(
                    [
                        row["selected_index"] != row["source_selected_index"]
                        for row in rows
                    ]
                )
            ),
            "mean_stage_candidate_counts": {
                stage: float(np.mean([counts[stage] for counts in stage_count_rows]))
                for stage in ("base", "progress", "planned_red", "jerk", "lateral")
            },
        },
        "paired_selected_minus_base": {
            metric: _difference_summary(
                rows,
                metric,
                higher_is_better=metric in ("step_reach", "progress"),
            )
            for metric in metric_names
        },
    }


def _candidate_metrics(
    record: dict[str, Any],
    candidate_count: int,
    log_path: Path,
    record_idx: int,
) -> dict[str, np.ndarray]:
    rewards = record.get("dp_candidate_rewards")
    if not isinstance(rewards, list) or len(rewards) != candidate_count:
        raise ValueError(
            f"{log_path} record {record_idx} lacks complete DP candidate rewards."
        )
    metrics = {
        "step_reach": _finite_vector(
            record, "candidate_step_reach", candidate_count, log_path, record_idx
        ),
        "progress": np.asarray(
            [float(reward["progress"]) for reward in rewards], dtype=np.float64
        ),
        "planned_red": np.asarray(
            [
                max(-float(reward.get("red_light", 0.0)), 0.0)
                for reward in rewards
            ],
            dtype=np.float64,
        ),
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
        "lateral_excess": _finite_vector(
            record,
            "candidate_dp_prior_lateral_acceleration_excess_cost",
            candidate_count,
            log_path,
            record_idx,
        ),
    }
    for name, values in metrics.items():
        if not np.all(np.isfinite(values)):
            raise ValueError(
                f"{log_path} record {record_idx} has nonfinite {name}."
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


def _difference_summary(
    rows: list[dict[str, Any]],
    metric: str,
    *,
    higher_is_better: bool,
) -> dict[str, float]:
    differences = np.asarray(
        [
            row["selected"][metric] - row["baseline"][metric]
            for row in rows
        ],
        dtype=np.float64,
    )
    return {
        "mean": float(np.mean(differences)),
        "median": float(np.median(differences)),
        "p05": float(np.percentile(differences, 5)),
        "p95": float(np.percentile(differences, 95)),
        "nonworse_rate": float(
            np.mean(
                differences >= -1e-12
                if higher_is_better
                else differences <= 1e-12
            )
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    config = report["analysis"]["config"]
    records = report["records"]
    selection = report["selection"]
    paired = report["paired_selected_minus_base"]
    lines = [
        "# DP+CAMP Lexicographic Fixed-Candidate Screen",
        "",
        "This is an offline definition screen, not closed-loop evidence.",
        "",
        "## Configuration",
        "",
        f"- Progress epsilon: `{config['progress_epsilon_m']}` m",
        f"- Planned-red epsilon: `{config['planned_red_epsilon']}`",
        f"- Jerk-excess epsilon: `{config['jerk_epsilon']}`",
        f"- Lateral epsilon: `{config['lateral_epsilon']}`",
        "- Order: progress -> planned red -> jerk -> lateral -> CAMP score",
        "",
        "## Coverage",
        "",
        f"- Logs: `{records['logs']}`",
        f"- Records: `{records['total']}`",
        f"- Base-feasible records: `{records['base_feasible']}`",
        f"- Base all-infeasible records: `{records['base_all_infeasible']}`",
        "- New fallback records: `0`",
        "",
        "## Selection",
        "",
        f"- Change vs base: `{selection['change_vs_base_rate']:.6f}`",
        f"- Change vs source: `{selection['change_vs_source_rate']:.6f}`",
        "",
        "| Metric | Mean delta | Median | p05 | p95 | Nonworse rate |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for metric, summary in paired.items():
        lines.append(
            f"| `{metric}` | {summary['mean']:.9f} | "
            f"{summary['median']:.9f} | {summary['p05']:.9f} | "
            f"{summary['p95']:.9f} | {summary['nonworse_rate']:.6f} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    paths = [*args.root, *args.selection_log]
    if not paths:
        raise ValueError("At least one --root or --selection_log is required.")
    report = compute_lexicographic_counterfactual_report(
        paths,
        ignored_infeasibility_reasons=tuple(args.ignore_infeasibility_reason),
        progress_epsilon_m=args.progress_epsilon_m,
        red_epsilon=args.red_epsilon,
        jerk_epsilon=args.jerk_epsilon,
        lateral_epsilon=args.lateral_epsilon,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")


if __name__ == "__main__":
    main()
