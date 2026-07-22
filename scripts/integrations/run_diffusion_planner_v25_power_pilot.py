#!/usr/bin/env python3
"""Build a sealed candidate0-only V25 cluster-variance power pilot."""

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
from camp_core.integrations.diffusion_planner_v25_power_pilot import (  # noqa: E402
    build_power_pilot_variance_receipt,
    project_candidate0_power_pilot_rows,
)


SCHEMA_VERSION = "camp_dp_v25_candidate0_power_pilot_artifact_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"


def build(
    *,
    calibration_artifact: Path,
    calibration_root_sha256: str,
    calibration_review_artifact: Path,
    calibration_review_root_sha256: str,
    plan_artifact: Path,
    plan_root_sha256: str,
    output_dir: Path,
) -> str:
    if _tracked_dirty():
        raise ValueError("CAMP tracked worktree must be clean")
    if output_dir.exists():
        raise FileExistsError(output_dir)
    calibration = calibration_artifact.resolve()
    calibration_review = calibration_review_artifact.resolve()
    plan = plan_artifact.resolve()
    verify_complete_seal(calibration, calibration_root_sha256, label="candidate0 calibration")
    verify_complete_seal(
        calibration_review,
        calibration_review_root_sha256,
        label="candidate0 calibration review",
    )
    verify_complete_seal(plan, plan_root_sha256, label="signal-complete calibration plan")
    for artifact in (calibration, calibration_review, plan):
        if (artifact / "run.exit").read_bytes() != b"0\n":
            raise ValueError("power pilot upstream run.exit drifted")
    calibration_report = _canonical_json(calibration / "report.json")
    review_report = _canonical_json(calibration_review / "report.json")
    plan_report = _canonical_json(plan / "report.json")
    if (
        calibration_report.get("status") != "passed_candidate0_calibration_execution"
        or calibration_report.get("fresh_b2_opened") is not False
        or calibration_report.get("fresh_outcome_fields_consumed") != []
        or review_report.get("status")
        != "passed_independent_candidate0_calibration_execution_review"
        or review_report.get("reviewed_root_sha256") != calibration_root_sha256
        or review_report.get("fresh_b2_opened") is not False
        or review_report.get("fresh_outcome_fields_consumed") != []
        or plan_report.get("split") != "calibration"
        or plan_report.get("fresh_b2_opened") is not False
        or plan_report.get("outcome_fields_consumed") != []
        or calibration_report.get("input_roots", {}).get("plan_root_sha256")
        != plan_root_sha256
    ):
        raise ValueError("power pilot reviewed upstream authority drifted")
    plan_payload = _canonical_json(plan / "execution_plan.json")
    results = _canonical_json_list(calibration / "run_results.json")
    output_dir.mkdir(parents=True)
    try:
        rows = project_candidate0_power_pilot_rows(plan_payload, results)
        receipt = build_power_pilot_variance_receipt(
            rows,
            source_artifact_root_sha256=calibration_root_sha256,
            source_split="calibration_pilot",
        )
        _write_json(output_dir / "power_pilot_rows.json", rows)
        _write_json(output_dir / "power_pilot_receipt.json", receipt)
        report = {
            "schema_version": SCHEMA_VERSION,
            "status": "passed_candidate0_power_pilot_variance",
            "camp_head": _git_head(),
            "fixed_dp_head": FIXED_DP_HEAD,
            "calibration_artifact": str(calibration),
            "calibration_root_sha256": calibration_root_sha256,
            "calibration_review_artifact": str(calibration_review),
            "calibration_review_root_sha256": calibration_review_root_sha256,
            "plan_artifact": str(plan),
            "plan_root_sha256": plan_root_sha256,
            "row_count": len(rows),
            "rows_sha256": _sha256(output_dir / "power_pilot_rows.json"),
            "receipt_sha256": _sha256(output_dir / "power_pilot_receipt.json"),
            "total_independent_cluster_count": receipt[
                "total_independent_cluster_count"
            ],
            "red_independent_cluster_count": receipt[
                "red_independent_cluster_count"
            ],
            "camp_method_outcomes_consumed": False,
            "fresh_b2_opened": False,
            "fresh_outcome_fields_consumed": [],
        }
        _write_json(output_dir / "report.json", report)
        (output_dir / "HEADS").write_bytes(
            f"camp_head={report['camp_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n".encode()
        )
        (output_dir / "COMMAND").write_bytes((" ".join(sys.argv) + "\n").encode())
        (output_dir / "run.exit").write_bytes(b"0\n")
        return seal_artifact(output_dir, label="V25 candidate0 power pilot")
    except BaseException as exc:
        _write_json(
            output_dir / "failure.json",
            {"schema_version": SCHEMA_VERSION, "status": "failed", "reason": str(exc)},
        )
        (output_dir / "run.exit").write_bytes(b"1\n")
        seal_artifact(output_dir, label="failed V25 candidate0 power pilot")
        raise


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


def _git_head() -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()


def _tracked_dirty() -> bool:
    return bool(
        subprocess.check_output(
            ["git", "-C", str(ROOT), "status", "--short", "--untracked-files=no"], text=True
        ).strip()
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calibration-artifact", type=Path, required=True)
    parser.add_argument("--calibration-root-sha256", required=True)
    parser.add_argument("--calibration-review-artifact", type=Path, required=True)
    parser.add_argument("--calibration-review-root-sha256", required=True)
    parser.add_argument("--plan-artifact", type=Path, required=True)
    parser.add_argument("--plan-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = build(**vars(args))
    print(json.dumps({"status": "sealed", "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
