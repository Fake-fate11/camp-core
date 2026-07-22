#!/usr/bin/env python3
"""Independently review a V25 candidate0 cluster-variance power pilot."""

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
from camp_core.integrations.diffusion_planner_v25_power_pilot import (  # noqa: E402
    build_power_pilot_variance_receipt,
    project_candidate0_power_pilot_rows,
    validate_power_pilot_variance_receipt,
)


SCHEMA_VERSION = "camp_dp_v25_candidate0_power_pilot_review_v1"
ARTIFACT_SCHEMA_VERSION = "camp_dp_v25_candidate0_power_pilot_artifact_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"


def review(artifact: Path, root_sha256: str) -> dict[str, Any]:
    root = artifact.resolve()
    seal = verify_complete_seal(root, root_sha256, label="candidate0 power pilot")
    if set(seal["manifest_paths"]) != {
        "COMMAND",
        "HEADS",
        "power_pilot_receipt.json",
        "power_pilot_rows.json",
        "report.json",
        "run.exit",
    } or (root / "run.exit").read_bytes() != b"0\n":
        raise ValueError("power pilot inventory/exit drifted")
    report = _canonical_json(root / "report.json")
    rows = _canonical_json_list(root / "power_pilot_rows.json")
    receipt = _canonical_json(root / "power_pilot_receipt.json")
    calibration = Path(str(report.get("calibration_artifact")))
    calibration_review = Path(str(report.get("calibration_review_artifact")))
    plan = Path(str(report.get("plan_artifact")))
    for path in (calibration, calibration_review, plan):
        if not path.is_absolute() or str(path.resolve()) != str(path):
            raise ValueError("power pilot upstream path drifted")
    verify_complete_seal(
        calibration,
        str(report.get("calibration_root_sha256")),
        label="candidate0 calibration",
    )
    verify_complete_seal(
        calibration_review,
        str(report.get("calibration_review_root_sha256")),
        label="candidate0 calibration review",
    )
    verify_complete_seal(
        plan, str(report.get("plan_root_sha256")), label="calibration plan"
    )
    for path in (calibration, calibration_review, plan):
        if (path / "run.exit").read_bytes() != b"0\n":
            raise ValueError("power pilot upstream exit drifted")
    calibration_report = _canonical_json(calibration / "report.json")
    review_report = _canonical_json(calibration_review / "report.json")
    plan_report = _canonical_json(plan / "report.json")
    if (
        calibration_report.get("status") != "passed_candidate0_calibration_execution"
        or calibration_report.get("input_roots", {}).get("plan_root_sha256")
        != report.get("plan_root_sha256")
        or review_report.get("status")
        != "passed_independent_candidate0_calibration_execution_review"
        or review_report.get("reviewed_root_sha256")
        != report.get("calibration_root_sha256")
        or plan_report.get("split") != "calibration"
        or any(
            item.get("fresh_b2_opened") is not False
            or item.get("fresh_outcome_fields_consumed", item.get("outcome_fields_consumed"))
            != []
            for item in (calibration_report, review_report, plan_report)
        )
    ):
        raise ValueError("power pilot reviewed upstream authority drifted")
    expected_rows = project_candidate0_power_pilot_rows(
        _canonical_json(plan / "execution_plan.json"),
        _canonical_json_list(calibration / "run_results.json"),
    )
    expected_receipt = build_power_pilot_variance_receipt(
        expected_rows,
        source_artifact_root_sha256=str(report["calibration_root_sha256"]),
        source_split="calibration_pilot",
    )
    if not _strict_equal(rows, expected_rows) or not _strict_equal(receipt, expected_receipt):
        raise ValueError("power pilot rows/receipt differ from independent reconstruction")
    validate_power_pilot_variance_receipt(
        receipt, expected_root_sha256=str(report["calibration_root_sha256"])
    )
    heads = _heads(root)
    expected_report = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "status": "passed_candidate0_power_pilot_variance",
        "camp_head": heads["camp_head"],
        "fixed_dp_head": FIXED_DP_HEAD,
        "calibration_artifact": str(calibration),
        "calibration_root_sha256": report["calibration_root_sha256"],
        "calibration_review_artifact": str(calibration_review),
        "calibration_review_root_sha256": report["calibration_review_root_sha256"],
        "plan_artifact": str(plan),
        "plan_root_sha256": report["plan_root_sha256"],
        "row_count": len(expected_rows),
        "rows_sha256": _sha256(root / "power_pilot_rows.json"),
        "receipt_sha256": _sha256(root / "power_pilot_receipt.json"),
        "total_independent_cluster_count": expected_receipt[
            "total_independent_cluster_count"
        ],
        "red_independent_cluster_count": expected_receipt[
            "red_independent_cluster_count"
        ],
        "camp_method_outcomes_consumed": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }
    if not _strict_equal(report, expected_report):
        raise ValueError("power pilot report drifted")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_candidate0_power_pilot_review",
        "fixed_dp_head": FIXED_DP_HEAD,
        "reviewed_artifact": str(root),
        "reviewed_root_sha256": seal["root_sha256"],
        "source_calibration_root_sha256": report["calibration_root_sha256"],
        "row_count": len(expected_rows),
        "total_independent_cluster_count": expected_receipt[
            "total_independent_cluster_count"
        ],
        "red_independent_cluster_count": expected_receipt[
            "red_independent_cluster_count"
        ],
        "camp_method_outcomes_consumed": False,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }


def _heads(root: Path) -> dict[str, str]:
    lines = (root / "HEADS").read_text(encoding="ascii").splitlines()
    if len(lines) != 2 or any("=" not in line for line in lines):
        raise ValueError("power pilot HEADS drifted")
    value = dict(line.split("=", 1) for line in lines)
    if set(value) != {"camp_head", "fixed_dp_head"} or value["fixed_dp_head"] != FIXED_DP_HEAD:
        raise ValueError("power pilot HEADS authority drifted")
    if len(value["camp_head"]) != 40 or set(value["camp_head"]) - set("0123456789abcdef"):
        raise ValueError("power pilot CAMP HEAD drifted")
    return value


def _canonical_json(path: Path) -> dict[str, Any]:
    value = _canonical_value(path)
    if type(value) is not dict:
        raise ValueError(f"authority JSON must be an object: {path}")
    return value


def _canonical_json_list(path: Path) -> list[dict[str, Any]]:
    value = _canonical_value(path)
    if type(value) is not list or any(type(row) is not dict for row in value):
        raise ValueError(f"authority JSON must be a list of objects: {path}")
    return value


def _canonical_value(path: Path) -> Any:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicate_pairs)
    if raw != _canonical_bytes(value):
        raise ValueError(f"authority JSON is not canonical: {path}")
    return value


def _no_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode()


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_bytes(value))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(_strict_equal(left[key], right[key]) for key in left)
    if type(left) is list:
        return len(left) == len(right) and all(
            _strict_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return bool(left == right)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    report = review(args.artifact, args.root_sha256)
    args.output_dir.mkdir(parents=True)
    _write_json(args.output_dir / "report.json", report)
    (args.output_dir / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode())
    (args.output_dir / "run.exit").write_bytes(b"0\n")
    root = seal_artifact(args.output_dir, label="V25 candidate0 power pilot review")
    print(json.dumps({"status": report["status"], "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
