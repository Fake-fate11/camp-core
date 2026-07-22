#!/usr/bin/env python3
"""Independently reconstruct and review a sealed V25 paired calibration plan."""

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


SCHEMA_VERSION = "camp_dp_v25_paired_calibration_plan_review_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"


def review(
    *,
    base_plan_artifact: Path,
    base_plan_root_sha256: str,
    paired_plan_artifact: Path,
    paired_plan_root_sha256: str,
    output_dir: Path,
) -> str:
    base_root = base_plan_artifact.resolve()
    paired_root = paired_plan_artifact.resolve()
    output = output_dir.resolve()
    if output.exists():
        raise FileExistsError(f"paired calibration plan review output exists: {output}")
    verify_complete_seal(
        base_root, base_plan_root_sha256, label="signal-complete calibration plan"
    )
    paired_seal = verify_complete_seal(
        paired_root, paired_plan_root_sha256, label="paired calibration plan"
    )
    base = _canonical_json(base_root / "execution_plan.json")
    actual = _canonical_json(paired_root / "paired_calibration_plan.json")
    expected = build_paired_calibration_execution_plan(base)
    if not _strict_equal(actual, expected):
        raise ValueError("paired calibration plan differs from independent reconstruction")
    report = _canonical_json(paired_root / "report.json")
    if (
        report.get("status") != "paired_calibration_plan_frozen"
        or report.get("base_plan_root_sha256") != base_plan_root_sha256
        or report.get("paired_plan_sha256")
        != _sha256(paired_root / "paired_calibration_plan.json")
        or report.get("fresh_b2_opened") is not False
        or report.get("fresh_outcome_fields_consumed") != []
    ):
        raise ValueError("paired calibration plan report drifted")
    output.mkdir(parents=True, exist_ok=False)
    _write_json(
        output / "report.json",
        {
            "schema_version": SCHEMA_VERSION,
            "status": "passed_independent_paired_calibration_plan_review",
            "camp_head": _git_head(ROOT),
            "fixed_dp_head": FIXED_DP_HEAD,
            "reviewed_artifact": str(paired_root),
            "reviewed_root_sha256": paired_seal["root_sha256"],
            "base_plan_artifact": str(base_root),
            "base_plan_root_sha256": base_plan_root_sha256,
            "pair_count": expected["pair_count"],
            "arm_run_count": expected["arm_run_count"],
            "total_tick_capacity": expected["total_tick_capacity"],
            "arm_rotation_reconstructed": True,
            "denominator_reconstructed": True,
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
    return seal_artifact(output, label="V25 paired calibration plan review")


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


def _strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(
            _strict_equal(left[key], right[key]) for key in left
        )
    if type(left) is list:
        return len(left) == len(right) and all(
            _strict_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return bool(left == right)


def _git_head(root: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-plan-artifact", type=Path, required=True)
    parser.add_argument("--base-plan-root-sha256", required=True)
    parser.add_argument("--paired-plan-artifact", type=Path, required=True)
    parser.add_argument("--paired-plan-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = review(**vars(args))
    print(json.dumps({"status": "sealed", "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
