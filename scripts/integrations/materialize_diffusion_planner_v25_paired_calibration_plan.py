#!/usr/bin/env python3
"""Seal the outcome-blind V25 three-arm paired calibration plan."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_paired_calibration import (  # noqa: E402
    build_paired_calibration_execution_plan,
)


SCHEMA_VERSION = "camp_dp_v25_paired_calibration_plan_artifact_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"


def materialize(
    *, base_plan_artifact: Path, base_plan_root_sha256: str, output_dir: Path
) -> str:
    base_root = base_plan_artifact.resolve()
    output = output_dir.resolve()
    if output.exists():
        raise FileExistsError(f"paired calibration plan output exists: {output}")
    verify_complete_seal(
        base_root, base_plan_root_sha256, label="signal-complete calibration plan"
    )
    base = _canonical_json(base_root / "execution_plan.json")
    paired = build_paired_calibration_execution_plan(base)
    output.mkdir(parents=True, exist_ok=False)
    _write_json(output / "paired_calibration_plan.json", paired)
    _write_json(
        output / "report.json",
        {
            "schema_version": SCHEMA_VERSION,
            "status": "paired_calibration_plan_frozen",
            "camp_head": _git_head(ROOT),
            "fixed_dp_head": FIXED_DP_HEAD,
            "base_plan_artifact": str(base_root),
            "base_plan_root_sha256": base_plan_root_sha256,
            "paired_plan_sha256": _sha256(
                output / "paired_calibration_plan.json"
            ),
            "pair_count": paired["pair_count"],
            "arm_run_count": paired["arm_run_count"],
            "total_tick_capacity": paired["total_tick_capacity"],
            "fresh_b2_opened": False,
            "fresh_outcome_fields_consumed": [],
        },
    )
    (output / "HEADS").write_text(
        f"camp_head={_git_head(ROOT)}\nfixed_dp_head={FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (output / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
    (output / "run.exit").write_bytes(b"0\n")
    return seal_artifact(output, label="V25 paired calibration plan")


def _canonical_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"))
    if type(value) is not dict or raw != _canonical_bytes(value):
        raise ValueError(f"noncanonical JSON object: {path}")
    return value


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_bytes(value))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head(root: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-plan-artifact", type=Path, required=True)
    parser.add_argument("--base-plan-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = materialize(**vars(args))
    print(json.dumps({"status": "sealed", "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
