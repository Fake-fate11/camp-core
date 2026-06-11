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

from camp_core.integrations.diffusion_planner import (  # noqa: E402
    sanitize_lanelet2_map,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create a no-ROS Lanelet2 map copy by removing Autoware-only "
            "regulatory elements unsupported by the PyPI lanelet2 wheel."
        )
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    print(json.dumps(sanitize_lanelet2_map(args.input, args.output), indent=2))


if __name__ == "__main__":
    main()
