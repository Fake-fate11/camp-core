#!/usr/bin/env python3
"""Freeze the V26 three-city, DB-only academic source boundary.

The input contains archive metadata only.  It must not include source records,
candidate pools, trajectories, labels, outcomes, cookies, or signed URLs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "camp_core"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_v26_nuplan import (  # noqa: E402
    build_v26_nuplan_academic_city_source_plan,
    canonical_json_bytes,
    validate_v26_nuplan_academic_city_source_plan,
)


def _read_json(path: Path, label: str) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    archive_input = _read_json(args.city_archives, "city archive input")
    if not isinstance(archive_input, dict) or set(archive_input) != {"city_archives"}:
        raise ValueError("city archive input must contain exactly city_archives")
    if not isinstance(archive_input["city_archives"], list):
        raise ValueError("city_archives must be a list")
    fixed_dp = _read_json(args.fixed_dp_binding, "fixed-DP binding")
    return build_v26_nuplan_academic_city_source_plan(
        archive_input["city_archives"],
        fixed_dp=fixed_dp,
        camp_source_head=args.camp_source_head,
    )


def write_plan(path: Path, plan: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical_json_bytes(plan))
    temporary.replace(path)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city-archives", type=Path, required=True)
    parser.add_argument("--fixed-dp-binding", type=Path, required=True)
    parser.add_argument("--camp-source-head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    plan = build_plan(args)
    validate_v26_nuplan_academic_city_source_plan(plan)
    write_plan(args.output, plan)
    print(json.dumps({"output": str(args.output), "source_plan_sha256": plan["source_plan_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
