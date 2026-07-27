from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "camp_core", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_v25_stage_orchestration import (  # noqa: E402
    execute_orchestration,
)


def _command(path: Path | None) -> list[str] | None:
    if path is None:
        return None
    value: Any = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not list or not all(type(item) is str for item in value):
        raise ValueError("command JSON must be a string array")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--mode", choices=("producer-and-reviewer", "review-only"), required=True
    )
    parser.add_argument("--implementation-head", required=True)
    parser.add_argument("--authority-sha256", required=True)
    parser.add_argument("--expected-interpreter", required=True)
    parser.add_argument("--cwd", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--source-root")
    parser.add_argument("--producer-command-json", type=Path)
    parser.add_argument("--producer-target-dir", type=Path)
    parser.add_argument("--reviewer-command-json", type=Path, required=True)
    parser.add_argument("--reviewer-target-dir", type=Path, required=True)
    args = parser.parse_args()
    root, result = execute_orchestration(
        output=args.output,
        mode=args.mode,
        implementation_head=args.implementation_head,
        authority_sha256=args.authority_sha256,
        expected_interpreter=args.expected_interpreter,
        cwd=args.cwd,
        source_dir=args.source_dir,
        source_root=args.source_root,
        producer_command=_command(args.producer_command_json),
        producer_target_dir=args.producer_target_dir,
        reviewer_command=_command(args.reviewer_command_json) or [],
        reviewer_target_dir=args.reviewer_target_dir,
    )
    print(root)
    return int(result["overall_exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
