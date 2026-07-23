#!/usr/bin/env python3
"""Independently review a sealed V25 calibration freeze artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
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
from camp_core.integrations.diffusion_planner_v25_calibration_artifact import (  # noqa: E402
    validate_calibration_freeze_payload,
)


SCHEMA_VERSION = "camp_dp_v25_calibration_freeze_review_v2"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"


def review(artifact: Path, expected_root: str) -> dict[str, Any]:
    seal = verify_complete_seal(artifact, expected_root, label="calibration freeze")
    if set(seal["manifest_paths"]) != {
        "COMMAND",
        "HEADS",
        "calibration_freeze.json",
        "report.json",
        "run.exit",
    }:
        raise ValueError("calibration freeze inventory drifted")
    if (artifact / "run.exit").read_bytes() != b"0\n":
        raise ValueError("calibration freeze exit drifted")
    report = _canonical_json(artifact / "report.json")
    payload = validate_calibration_freeze_payload(
        _canonical_json(artifact / "calibration_freeze.json")
    )
    inputs_path = Path(str(report.get("inputs_path"))).resolve()
    calibration_artifact = Path(str(report.get("calibration_artifact"))).resolve()
    calibration_review_artifact = Path(
        str(report.get("calibration_review_artifact"))
    ).resolve()
    calibration_seal = verify_complete_seal(
        calibration_artifact,
        str(report.get("calibration_root_sha256")),
        label="candidate0 calibration execution",
    )
    calibration_review_seal = verify_complete_seal(
        calibration_review_artifact,
        str(report.get("calibration_review_root_sha256")),
        label="candidate0 calibration execution review",
    )
    calibration_review = _canonical_json(calibration_review_artifact / "report.json")
    if (
        report.get("inputs_sha256") != _sha256(inputs_path)
        or calibration_review.get("status")
        != "passed_independent_candidate0_calibration_execution_review"
        or calibration_review.get("reviewed_root_sha256")
        != calibration_seal["root_sha256"]
        or calibration_review_seal["root_sha256"]
        != report.get("calibration_review_root_sha256")
        or report.get("calibration_freeze_sha256")
        != _sha256(artifact / "calibration_freeze.json")
        or report.get("status") != payload["status"]
        or report.get("candidate0_row_count") != payload["candidate0_row_count"]
        or report.get("heterogeneity_cluster_count")
        != payload["noninferiority_resolvability"]["heterogeneity_cluster_count"]
        or report.get("repeatability_status")
        != payload["noninferiority_resolvability"]["repeatability_status"]
        or report.get("exact_duplicate_repeatability_group_count")
        != payload["noninferiority_resolvability"]["exact_duplicate_group_count"]
        or report.get("margin_enlargement_authorized") is not False
        or report.get("camp_method_outcomes_consumed") is not False
        or report.get("fresh_b2_opened") is not False
        or report.get("fresh_outcome_fields_consumed") != []
        or report.get("fresh_open_authorized") is not False
        or report.get("fixed_dp_head") != FIXED_DP_HEAD
    ):
        raise ValueError("calibration freeze report drifted")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_calibration_freeze_review",
        "reviewed_artifact": str(artifact.resolve()),
        "reviewed_root_sha256": seal["root_sha256"],
        "calibration_status": payload["status"],
        "candidate0_row_count": payload["candidate0_row_count"],
        "heterogeneity_cluster_count": payload["noninferiority_resolvability"][
            "heterogeneity_cluster_count"
        ],
        "repeatability_status": payload["noninferiority_resolvability"][
            "repeatability_status"
        ],
        "exact_duplicate_repeatability_group_count": payload[
            "noninferiority_resolvability"
        ]["exact_duplicate_group_count"],
        "operational_overspeed_tolerance_mps": payload[
            "calibration_contract"
        ]["operational_overspeed_tolerance_mps"],
        "margin_enlargement_authorized": False,
        "fresh_b2_opened": False,
        "fresh_open_authorized": False,
        "fresh_outcome_fields_consumed": [],
    }


def _canonical_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"))
    if type(value) is not dict:
        raise ValueError("calibration authority JSON must be a mapping")
    expected = (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode()
    if raw != expected:
        raise ValueError("calibration authority JSON is not canonical")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(
        (
            json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
            + "\n"
        ).encode()
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = review(args.artifact, args.root_sha256)
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    _write_json(args.output_dir / "report.json", report)
    (args.output_dir / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode())
    (args.output_dir / "run.exit").write_bytes(b"0\n")
    root = seal_artifact(args.output_dir, label="V25 calibration freeze review")
    print(json.dumps({"status": report["status"], "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
