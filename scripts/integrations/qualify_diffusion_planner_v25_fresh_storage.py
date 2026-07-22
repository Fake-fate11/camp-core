#!/usr/bin/env python3
"""Qualify new-artifact-only Fresh B2 storage from accepted calibration bytes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
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
from camp_core.integrations.diffusion_planner_v25_fresh_storage import (  # noqa: E402
    MINIMUM_RETAINED_FREE_BYTES,
    analyze_storage_tree,
)


SCHEMA_VERSION = "camp_dp_v25_fresh_storage_qualification_artifact_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
FAILED_CALIBRATION_ROOT = "5cd071b6ac9dd805422d7fe572f3db273abe9fce5cd4f910a0cf6fa9296e8249"
RECOVERY_ROOT = "9d67e57bfa4a96ff3bf318c5aafd17f024207645344f076963fc5f756caa6551"
RECOVERY_REVIEW_ROOT = "650e6749bda63f23b073a5491c0f57dd9f97136a644be8ab7c918a48a3f609f7"


def qualify(
    *,
    calibration_artifact: Path,
    calibration_root_sha256: str,
    recovery_artifact: Path,
    recovery_root_sha256: str,
    recovery_review_artifact: Path,
    recovery_review_root_sha256: str,
    output_dir: Path,
) -> str:
    output = output_dir.resolve()
    if output.exists():
        raise FileExistsError(output)
    calibration = calibration_artifact.resolve()
    recovery = recovery_artifact.resolve()
    review = recovery_review_artifact.resolve()
    if (
        calibration_root_sha256 != FAILED_CALIBRATION_ROOT
        or recovery_root_sha256 != RECOVERY_ROOT
        or recovery_review_root_sha256 != RECOVERY_REVIEW_ROOT
    ):
        raise ValueError("accepted calibration storage roots drifted")
    for path, root, exit_code, label in (
        (calibration, calibration_root_sha256, b"1\n", "immutable calibration raw evidence"),
        (recovery, recovery_root_sha256, b"0\n", "accepted calibration recovery"),
        (review, recovery_review_root_sha256, b"0\n", "accepted calibration recovery review"),
    ):
        verify_complete_seal(path, root, label=label)
        if (path / "run.exit").read_bytes() != exit_code:
            raise ValueError(f"{label} run.exit drifted")
    recovery_report = _canonical_json(recovery / "report.json")
    review_report = _canonical_json(review / "report.json")
    if (
        recovery_report.get("status")
        != "recovered_calibration_analysis_complete_fresh_closed"
        or recovery_report.get("original_execution_root_sha256")
        != calibration_root_sha256
        or recovery_report.get("fresh_b2_opened") is not False
        or recovery_report.get("fresh_outcome_fields_consumed") != []
        or review_report.get("status")
        != "passed_independent_paired_calibration_recovery_review"
        or review_report.get("reviewed_recovery_root_sha256") != recovery_root_sha256
        or review_report.get("original_execution_root_sha256")
        != calibration_root_sha256
        or review_report.get("fresh_b2_opened") is not False
        or review_report.get("fresh_outcome_fields_consumed") != []
    ):
        raise ValueError("accepted calibration recovery chain drifted")
    samples = _regression_samples(calibration)
    free_before = shutil.disk_usage(output.parent).free
    manifest = analyze_storage_tree(
        calibration,
        work_root=output,
        retained_sample_relpaths=samples,
        minimum_free_bytes=MINIMUM_RETAINED_FREE_BYTES,
    )
    metrics = manifest["metrics"]
    budget = free_before - MINIMUM_RETAINED_FREE_BYTES
    capacity_passed = budget >= 0 and metrics["projected_1500_arm_upper_bound_nbytes"] <= budget
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": (
            "passed_fresh_storage_equivalence_and_capacity"
            if capacity_passed
            else "failed_fresh_storage_capacity"
        ),
        "camp_head": _git_head(ROOT),
        "fixed_dp_head": FIXED_DP_HEAD,
        "calibration_artifact": str(calibration),
        "calibration_root_sha256": calibration_root_sha256,
        "calibration_run_exit": 1,
        "recovery_artifact": str(recovery),
        "recovery_root_sha256": recovery_root_sha256,
        "recovery_review_artifact": str(review),
        "recovery_review_root_sha256": recovery_review_root_sha256,
        "source_terminal_arm_count": 300,
        "retained_regression_samples": samples,
        "storage_manifest_sha256": _sha256(output / "storage_manifest.json"),
        "logical_tree_sha256": manifest["logical_tree_sha256"],
        "free_before_bytes": free_before,
        "minimum_retained_free_bytes": MINIMUM_RETAINED_FREE_BYTES,
        "fresh_incremental_budget_bytes": max(budget, 0),
        "projected_1500_arm_upper_bound_nbytes": metrics[
            "projected_1500_arm_upper_bound_nbytes"
        ],
        "capacity_gate_passed": capacity_passed,
        "new_artifact_only": True,
        "original_calibration_artifact_modified": False,
        "preopen_dp_forward_executed": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }
    _write_json(output / "report.json", report)
    (output / "HEADS").write_text(
        f"camp_head={report['camp_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n",
        encoding="ascii",
    )
    (output / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
    (output / "run.exit").write_text("0\n" if capacity_passed else "1\n", encoding="ascii")
    root = seal_artifact(output, label="V25 Fresh B2 storage qualification")
    if not capacity_passed:
        raise RuntimeError(f"Fresh storage capacity gate failed; sealed root={root}")
    return root


def _regression_samples(root: Path) -> list[str]:
    runs = sorted((root / "runs").iterdir())
    if len(runs) != 300:
        raise ValueError("calibration storage source must contain 300 run directories")
    by_arm: dict[str, list[tuple[int, str]]] = {
        "candidate0_operational_default": [],
        "camp_static14d": [],
        "camp_scene14d_no_v2i": [],
    }
    for run in runs:
        if not run.is_dir() or run.is_symlink():
            raise ValueError("calibration run inventory is unsafe")
        matched = next((arm for arm in by_arm if run.name.endswith(arm)), None)
        evidence = run / "decision_evidence.json"
        if matched is None or not evidence.is_file() or evidence.is_symlink():
            raise ValueError("calibration decision evidence inventory drifted")
        by_arm[matched].append((evidence.stat().st_size, evidence.relative_to(root).as_posix()))
    result: list[str] = []
    for arm, values in by_arm.items():
        values.sort()
        if len(values) != 100:
            raise ValueError(f"calibration storage {arm} denominator drifted")
        index = 0 if arm == "candidate0_operational_default" else (94 if arm == "camp_static14d" else 99)
        result.append(values[index][1])
    return sorted(result)


def _canonical_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicates, parse_constant=_bad_constant)
    if type(value) is not dict or raw != _canonical_bytes(value):
        raise ValueError(f"noncanonical authority JSON: {path}")
    return value


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _bad_constant(value: str) -> Any:
    raise ValueError(value)


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode()


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_bytes(value))


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head(path: Path) -> str:
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calibration-artifact", type=Path, required=True)
    parser.add_argument("--calibration-root-sha256", required=True)
    parser.add_argument("--recovery-artifact", type=Path, required=True)
    parser.add_argument("--recovery-root-sha256", required=True)
    parser.add_argument("--recovery-review-artifact", type=Path, required=True)
    parser.add_argument("--recovery-review-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = qualify(**vars(args))
    print(json.dumps({"status": "sealed", "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
