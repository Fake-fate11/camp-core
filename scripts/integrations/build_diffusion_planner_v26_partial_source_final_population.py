"""Close the V26 partial-source final training population without row materialization."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence


ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT, ROOT / "camp_core"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_v26_partial_source_training import (  # noqa: E402
    materialize_final_training_population_receipt,
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--partial-source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-camp-head", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    paths = materialize_final_training_population_receipt(
        partial_source_manifest_path=args.partial_source_manifest,
        output_dir=args.output_dir,
        camp_head=args.expected_camp_head,
    )
    print(paths["receipt"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
