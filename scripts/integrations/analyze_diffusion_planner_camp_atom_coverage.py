#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner_coverage import (  # noqa: E402
    compute_atom_coverage_report,
    render_markdown_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit DP-compatible CAMP atom coverage using Diffusion Planner "
            "selection logs with online rewards and optional closed-loop labels."
        )
    )
    parser.add_argument(
        "--root",
        type=Path,
        action="append",
        default=[],
        help="Directory to scan recursively for camp_selection_log.json.",
    )
    parser.add_argument(
        "--selection_log",
        type=Path,
        action="append",
        default=[],
        help="Single camp_selection_log.json file to include.",
    )
    parser.add_argument(
        "--mode",
        choices=("static", "theta", "uniform"),
        action="append",
        default=[],
        help="Optional selector mode filter. Can be passed multiple times.",
    )
    parser.add_argument(
        "--extra_scale_percentile",
        type=float,
        default=95.0,
        help="Positive-value percentile used to normalize diagnostic extra costs.",
    )
    parser.add_argument("--output_json", type=Path, default=None)
    parser.add_argument("--output_md", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    inputs = list(args.root) + list(args.selection_log)
    if not inputs:
        raise SystemExit("Provide at least one --root or --selection_log.")

    report = compute_atom_coverage_report(
        inputs,
        mode_filter=set(args.mode) if args.mode else None,
        extra_scale_percentile=args.extra_scale_percentile,
    )
    markdown = render_markdown_report(report)

    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(markdown, encoding="utf-8")

    if args.output_json is None and args.output_md is None:
        print(markdown)
    else:
        summary = report["summary"]
        print(
            "Atom coverage report: "
            f"{summary['log_count']} logs, "
            f"{summary['record_count']} records, "
            f"{summary['candidate_count']} candidates."
        )
        if args.output_json is not None:
            print(f"JSON: {args.output_json}")
        if args.output_md is not None:
            print(f"Markdown: {args.output_md}")


if __name__ == "__main__":
    main()
