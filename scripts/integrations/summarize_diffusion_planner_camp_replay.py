#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner import (  # noqa: E402
    summarize_replay_artifacts,
)


REPLAY_METADATA_FIELDS = (
    "camp_selection_log",
    "camp_metric_log",
    "camp_evaluation_state_log",
    "num_candidates",
    "candidate_noise_scale",
    "camp_lane_corridor_buffer",
    "camp_feasibility_source",
    "camp_min_progress_ratio",
    "camp_min_candidate0_progress_ratio",
    "camp_min_candidate0_route_progress_ratio",
    "camp_min_candidate0_step_reach_ratio",
    "camp_reward_horizon_steps",
    "camp_collect_closed_loop_outcomes",
    "camp_outcome_horizon_steps",
    "camp_shadow_red_stopping_margin",
    "camp_shadow_dp_prior_comfort_excess",
    "camp_shadow_lateral_comfort",
    "selector_mode",
    "camp_fallback_mode",
    "advance_mode",
    "dp_scene_feature_names",
    "model_args",
    "using_no_ros_projection_fallback",
    "benchmark",
)


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"Missing replay artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def merge_replay_metadata(
    summary: dict[str, Any],
    replay_summary: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(summary)
    for field in REPLAY_METADATA_FIELDS:
        if field in replay_summary:
            merged[field] = replay_summary[field]
    return merged


def merge_existing_summary(
    existing_summary: dict[str, Any] | None,
    recomputed_summary: dict[str, Any],
) -> dict[str, Any]:
    if existing_summary is None:
        return dict(recomputed_summary)
    merged = dict(existing_summary)
    for key, value in recomputed_summary.items():
        if value is not None:
            merged[key] = value
    return merged


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize CAMP selection behavior from a replay output directory."
    )
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument(
        "--summary_path",
        type=Path,
        default=None,
        help="Defaults to OUTPUT_DIR/camp_validation_summary.json.",
    )
    parser.add_argument("--near_miss_threshold_m", type=float, default=2.0)
    args = parser.parse_args()

    replay_summary = _read_json(args.output_dir / "camp_replay_summary.json")
    replay_result = replay_summary.get("replay_result")
    selection_log = args.output_dir / "camp_selection_log.json"
    records = _read_json(selection_log) if selection_log.is_file() else None
    metric_log = args.output_dir / "camp_metric_log.json"
    metric_records = _read_json(metric_log) if metric_log.is_file() else None
    evaluation_log = args.output_dir / "camp_evaluation_state_log.json"
    evaluation_records = (
        _read_json(evaluation_log) if evaluation_log.is_file() else None
    )
    summary_path = (
        args.summary_path
        if args.summary_path is not None
        else args.output_dir / "camp_validation_summary.json"
    )
    existing_summary = (
        _read_json(summary_path) if summary_path.is_file() else None
    )
    summary = summarize_replay_artifacts(
        args.output_dir,
        selection_records=records,
        replay_result=replay_result,
        metric_records=metric_records,
        evaluation_records=evaluation_records,
        near_miss_threshold_m=args.near_miss_threshold_m,
    )
    summary = merge_existing_summary(existing_summary, summary)
    summary = merge_replay_metadata(summary, replay_summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
