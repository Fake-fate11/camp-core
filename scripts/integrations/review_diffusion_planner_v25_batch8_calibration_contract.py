"""Seal an independent literal review of the batch8-only calibration contract."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_batch8_calibration_contract_review import (  # noqa: E402
    independent_literal_review,
)


def review(*, source: Path, source_root: str, output: Path) -> str:
    verify_complete_seal(source, source_root, label="batch8 calibration contract")
    source_report = _read_object(source / "report.json")
    if (
        source_report.get("schema_version")
        != "camp_dp_v25_batch8_primary_calibration_contract_artifact_v1"
        or source_report.get("status")
        != "sealed_outcome_independent_batch8_calibration_contract"
        or source_report.get("outcome_values_read") is not False
        or source_report.get("new_model_pool_selector_call_count") != 0
        or source_report.get("actual_calibration_acquisition_count") != 0
        or source_report.get("threshold_materialization_count") != 0
        or source_report.get("old_artifact_or_cas_write_count") != 0
        or source_report.get("fixed_dp", {}).get("head")
        != "7a1d33da277a1992ec474b5383a0c963c72e04e4"
        or source_report.get("fixed_dp", {}).get("tracked_clean") is not True
    ):
        raise ValueError("producer artifact invariant drifted")
    contract = _object(source_report.get("contract"), "contract")
    implementation = _object(contract.get("implementation"), "implementation")
    literal = independent_literal_review(
        contract,
        expected_implementation_head=implementation.get("head"),
        expected_exact_dirs=implementation.get("exact_dirs"),
        expected_source_sha256=implementation.get("source_sha256"),
    )
    report = {
        **literal,
        "schema_version": (
            "camp_dp_v25_batch8_primary_calibration_contract_"
            "artifact_independent_review_v1"
        ),
        "status": "passed_independent_batch8_calibration_contract_review",
        "source": {
            "path": str(source.resolve()),
            "root_sha256": source_root,
        },
        "review_head": _git_head(),
        "outcome_values_read": False,
        "new_model_pool_selector_call_count": 0,
        "actual_calibration_acquisition_count": 0,
        "threshold_materialization_count": 0,
        "old_artifact_or_cas_write_count": 0,
    }
    return _atomic(output, report, "V25 batch8 calibration contract review")


def _atomic(output: Path, report: dict[str, Any], label: str) -> str:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=str(output.parent))
    )
    try:
        (staging / "report.json").write_bytes(_bytes(report))
        (staging / "HEADS.json").write_bytes(
            _bytes(
                {
                    "role": "batch8_calibration_contract_review",
                    "review_head": report["review_head"],
                }
            )
        )
        root = seal_artifact(staging, label=label)
        os.replace(staging, output)
        verify_complete_seal(output, root, label=label)
        return root
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def _bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("ascii")


def _read_object(path: Path) -> dict[str, Any]:
    return _object(json.loads(path.read_text(encoding="utf-8")), str(path))


def _object(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError(f"{label} must contain an object")
    return dict(value)


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(review(source=args.source, source_root=args.source_root, output=args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
