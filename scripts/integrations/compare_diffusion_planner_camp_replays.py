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
    summarize_selection_records,
)


SUMMARY_KEYS = (
    "selection_steps",
    "num_candidates",
    "nonzero_selection_rate",
    "fallback_rate",
    "candidate_feasible_rate",
    "mean_selection_latency_ms",
    "p95_selection_latency_ms",
    "replay_reason",
    "goal_reached",
)


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"Missing replay artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_or_build_summary(output_dir: Path) -> dict[str, Any]:
    summary_path = output_dir / "camp_validation_summary.json"
    if summary_path.is_file():
        return _read_json(summary_path)

    records = _read_json(output_dir / "camp_selection_log.json")
    replay_summary = _read_json(output_dir / "camp_replay_summary.json")
    summary = summarize_selection_records(
        records,
        replay_summary.get("replay_result"),
    )
    summary["num_candidates"] = replay_summary.get("num_candidates")
    summary["candidate_noise_scale"] = replay_summary.get("candidate_noise_scale")
    return summary


def _parse_variant(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError(
            "variant must have the form NAME=/path/to/replay_output"
        )
    name, path = value.split("=", 1)
    name = name.strip()
    if not name:
        raise argparse.ArgumentTypeError("variant name must not be empty")
    return name, Path(path)


def _markdown_table(rows: list[dict[str, Any]]) -> str:
    headers = ("variant",) + SUMMARY_KEYS
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        values = []
        for key in headers:
            value = row.get(key)
            if isinstance(value, float):
                values.append(f"{value:.6g}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare multiple DP+CAMP replay summaries under matched settings."
    )
    parser.add_argument(
        "--variant",
        action="append",
        type=_parse_variant,
        required=True,
        help="NAME=/path/to/replay_output. Repeat for each comparable variant.",
    )
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_markdown", type=Path, default=None)
    args = parser.parse_args()

    rows = []
    for name, output_dir in args.variant:
        summary = _load_or_build_summary(output_dir)
        row = {"variant": name, "output_dir": str(output_dir)}
        for key in SUMMARY_KEYS:
            row[key] = summary.get(key)
        rows.append(row)

    result = {
        "comparison_type": "diffusion_planner_camp_replay_variants",
        "variants": rows,
        "caveat": (
            "Rows are comparable only when route, map, seed, NPC settings, "
            "steps, DP checkpoint, candidate count, and spawn config match."
        ),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2), encoding="utf-8")

    if args.output_markdown is not None:
        args.output_markdown.parent.mkdir(parents=True, exist_ok=True)
        args.output_markdown.write_text(_markdown_table(rows), encoding="utf-8")

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
