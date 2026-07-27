"""Create the explicit 1783-route Stage 8b successor plan from immutable evidence.

The command is deliberately read-only with respect to its parent plan and
qualification root.  It does not import a model, Diffusion Planner, torch, or
any outcome data.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence


ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT, ROOT / "camp_core"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_v26_diversified_plan_revision import (  # noqa: E402
    materialize_revised_plan,
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-route-plan", type=Path, required=True)
    parser.add_argument("--original-qualification-receipt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    paths = materialize_revised_plan(
        parent_plan_path=args.parent_route_plan,
        qualification_receipt_path=args.original_qualification_receipt,
        output_dir=args.output_dir,
    )
    print(paths["review"])
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
