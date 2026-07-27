"""Create a new immutable full-denominator union from V26 continuation units."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence


ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT, ROOT / "camp_core"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_v26_diversified_successor import (  # noqa: E402
    materialize_immutable_union_manifest,
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--successor-plan", type=Path, required=True)
    parser.add_argument("--parent-revised-plan", type=Path, required=True)
    parser.add_argument("--parent-recovered-root", type=Path, required=True)
    parser.add_argument("--successor-acquisition-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    print(
        materialize_immutable_union_manifest(
            successor_plan_path=args.successor_plan,
            parent_revised_plan_path=args.parent_revised_plan,
            parent_recovered_root=args.parent_recovered_root,
            successor_acquisition_root=args.successor_acquisition_root,
            output_dir=args.output_dir,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
