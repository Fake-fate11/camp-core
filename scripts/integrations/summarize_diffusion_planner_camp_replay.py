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


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"Missing replay artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


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
    summary = summarize_replay_artifacts(
        args.output_dir,
        selection_records=records,
        replay_result=replay_result,
        metric_records=metric_records,
        evaluation_records=evaluation_records,
        near_miss_threshold_m=args.near_miss_threshold_m,
    )
    summary["selector_mode"] = replay_summary.get("selector_mode")
    summary["num_candidates"] = replay_summary.get("num_candidates")
    summary["candidate_noise_scale"] = replay_summary.get("candidate_noise_scale")
    if "benchmark" in replay_summary:
        summary["benchmark"] = replay_summary["benchmark"]

    summary_path = (
        args.summary_path
        if args.summary_path is not None
        else args.output_dir / "camp_validation_summary.json"
    )
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
