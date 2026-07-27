"""Prepare the independent V26 zero-shot-versus-adapted development plan.

Only the prior profiling manifest's route metadata is read.  No profiling
trajectory, selection result, outcome, model, DP, simulator, or adaptation
artifact is consumed by this planning entry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "camp_core"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from camp_core.integrations.diffusion_planner_v26_selector_adaptation import (  # noqa: E402
    build_development_comparison_plan,
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True, separators=(",", ":"), allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        Path(temporary_name).replace(path)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def run(args: argparse.Namespace) -> Path:
    manifest_path = args.profiling_manifest.resolve()
    output_path = args.output.resolve()
    if output_path.exists():
        raise FileExistsError(output_path)
    value = json.loads(manifest_path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError("V26 profiling manifest must be a JSON object")
    plan = build_development_comparison_plan(
        value, profiling_manifest_sha256=_sha256_file(manifest_path)
    )
    _atomic_write_json(output_path, plan)
    return output_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiling-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    output = run(parse_args(argv))
    print(json.dumps({"status": "prepared_no_execution_no_claim", "output": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
