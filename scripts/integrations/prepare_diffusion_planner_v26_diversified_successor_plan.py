"""Materialize the read-only V26 Stage8b successor route-plan identity."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Sequence


ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT, ROOT / "camp_core"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_v26_diversified_successor import (  # noqa: E402
    materialize_successor_plan,
)


def _git_head(path: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=path, text=True, encoding="utf-8"
    ).strip()


def _tracked_changes(path: Path) -> bool:
    return bool(
        subprocess.check_output(
            ["git", "status", "--short", "--untracked-files=no"],
            cwd=path,
            text=True,
            encoding="utf-8",
        ).strip()
    )


def run(args: argparse.Namespace) -> Path:
    if _tracked_changes(ROOT) or _git_head(ROOT) != args.expected_camp_head:
        raise ValueError("V26 successor plan requires an exact clean CAMP checkout")
    paths = materialize_successor_plan(
        parent_revised_plan_path=args.parent_revised_plan,
        parent_recovered_root=args.parent_recovered_root,
        output_dir=args.output_dir,
        camp_head=args.expected_camp_head,
    )
    plan = json.loads(paths["plan"].read_text(encoding="utf-8"))
    if plan["parent_revised_plan"]["route_plan_sha256"] != args.expected_parent_revised_plan_sha256:
        raise ValueError("V26 successor plan parent revised-plan SHA drifted")
    return paths["manifest"]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-revised-plan", type=Path, required=True)
    parser.add_argument("--parent-recovered-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-camp-head", required=True)
    parser.add_argument("--expected-parent-revised-plan-sha256", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    print(run(parse_args(argv)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
