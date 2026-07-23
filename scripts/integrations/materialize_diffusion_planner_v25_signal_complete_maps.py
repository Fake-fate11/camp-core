#!/usr/bin/env python3
"""Seal project-authored V25 signal-complete calibration/Fresh map inputs."""

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

from camp_core.integrations.diffusion_planner_artifact_seal import seal_artifact  # noqa: E402
from camp_core.integrations.diffusion_planner_v25_signal_complete_maps import (  # noqa: E402
    build_signal_complete_suite,
    validate_signal_complete_suite,
)


SCHEMA_VERSION = "camp_dp_v25_signal_complete_map_artifact_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
GENERATOR_SOURCE = (
    PACKAGE_ROOT
    / "camp_core"
    / "integrations"
    / "diffusion_planner_v25_signal_complete_maps.py"
)


def build(*, split: str, output_dir: Path) -> str:
    if _tracked_dirty():
        raise ValueError("CAMP tracked worktree must be clean")
    if output_dir.exists():
        raise FileExistsError(output_dir)
    output_dir.mkdir(parents=True)
    try:
        suite = build_signal_complete_suite(split)
        receipt = validate_signal_complete_suite(suite)
        for relative, data in suite["map_payloads"].items():
            destination = output_dir / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        _write_json(output_dir / "signal_complete_suite.json", receipt)
        license_receipt = {
            "schema_version": "camp_dp_v25_project_authored_map_license_receipt_v1",
            "spdx": "MIT",
            "repository_license_path": str((ROOT / "LICENSE").resolve()),
            "repository_license_sha256": _sha256(ROOT / "LICENSE"),
            "third_party_map_payload_derived": False,
        }
        _write_json(output_dir / "LICENSE_RECEIPT.json", license_receipt)
        report = {
            "schema_version": SCHEMA_VERSION,
            "status": "passed_signal_complete_map_materialization",
            "camp_head": _git_head(),
            "fixed_dp_head": FIXED_DP_HEAD,
            "split": split,
            "suite_schema_version": receipt["schema_version"],
            "suite_sha256": _sha256(output_dir / "signal_complete_suite.json"),
            "map_count": receipt["map_count"],
            "corridor_count": receipt["corridor_count"],
            "route_count": receipt["route_count"],
            "generator_source": str(GENERATOR_SOURCE.resolve()),
            "generator_source_sha256": _sha256(GENERATOR_SOURCE),
            "license_receipt_sha256": _sha256(output_dir / "LICENSE_RECEIPT.json"),
            "fixed_dp_modified": False,
            "candidate_tensor_modified": False,
            "model_loaded": False,
            "candidate_generation_executed": False,
            "training_executed": False,
            "calibration_outcomes_consumed": False,
            "fresh_b2_opened": False,
            "outcome_fields_consumed": [],
        }
        _write_json(output_dir / "report.json", report)
        (output_dir / "HEADS").write_bytes(
            f"camp_head={report['camp_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n".encode(
                "ascii"
            )
        )
        (output_dir / "COMMAND").write_bytes(
            (" ".join(sys.argv) + "\n").encode("utf-8")
        )
        (output_dir / "run.exit").write_bytes(b"0\n")
        return seal_artifact(output_dir, label="V25 signal-complete map artifact")
    except BaseException as exc:
        _write_json(
            output_dir / "failure.json",
            {"schema_version": SCHEMA_VERSION, "status": "failed", "reason": str(exc)},
        )
        (output_dir / "run.exit").write_bytes(b"1\n")
        seal_artifact(output_dir, label="failed V25 signal-complete map artifact")
        raise


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()


def _tracked_dirty() -> bool:
    return bool(
        subprocess.check_output(
            ["git", "-C", str(ROOT), "status", "--short", "--untracked-files=no"],
            text=True,
        ).strip()
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(
        (
            json.dumps(
                value,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--split",
        choices=("calibration", "fresh_b2", "fresh_b3", "fresh_b4"),
        required=True,
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = build(split=args.split, output_dir=args.output_dir)
    print(json.dumps({"status": "passed", "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
