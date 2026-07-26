"""Materialize frozen generator repeatability thresholds from reviewed raw bytes."""

from __future__ import annotations

import argparse
from itertools import combinations
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "camp_core"
if str(PACKAGE) not in sys.path:
    sys.path.insert(0, str(PACKAGE))

from camp_core.integrations.diffusion_planner_artifact_seal import seal_artifact, verify_complete_seal  # noqa: E402
from camp_core.integrations.diffusion_planner_v25_batch8_generator_calibration import (  # noqa: E402
    CANDIDATE_SHAPE, EXACT_DIRS, NEIGHBOR_SHAPE, OUTPUT_DTYPE, bootstrap_ucb,
    endpoint_registry, pair_errors, state_q99_higher,
)


def materialize(raw_dir: Path, raw_root: str, review_dir: Path, review_root: str, output: Path) -> str:
    verify_complete_seal(raw_dir, raw_root, label="generator calibration raw")
    verify_complete_seal(review_dir, review_root, label="generator calibration raw review")
    raw_report = json.loads((raw_dir / "report.json").read_text("ascii"))
    review_report = json.loads((review_dir / "report.json").read_text("ascii"))
    if (
        raw_report["completed_run_count"] != 320
        or raw_report["hard_integrity_failure_count"] != 0
        or raw_report["slot_failure_count"] != 0
        or review_report["status"] != "PASS"
        or review_report["pair_receipt_count"] != 640
    ):
        raise RuntimeError("threshold materialization prerequisites failed")
    runs = {}
    for slot in range(320):
        receipt = json.loads((raw_dir / "runs" / f"{slot:03d}" / "receipt.json").read_text("ascii"))
        candidate = np.fromfile(raw_dir / receipt["candidate_relpath"], dtype=OUTPUT_DTYPE).reshape(CANDIDATE_SHAPE)
        neighbor = np.fromfile(raw_dir / receipt["neighbor_relpath"], dtype=OUTPUT_DTYPE).reshape(NEIGHBOR_SHAPE)
        runs[(receipt["state_index"], receipt["repeat_index"])] = (candidate, neighbor)
    registry = endpoint_registry()
    state_values = {row["endpoint_id"]: [] for row in registry}
    pair_count = 0
    for state in range(64):
        per_endpoint = {key: [] for key in state_values}
        for left, right in combinations(range(5), 2):
            values = pair_errors(*runs[(state, left)], *runs[(state, right)])
            pair_count += 1
            for key, value in values.items():
                per_endpoint[key].append(value)
        for key, values in per_endpoint.items():
            state_values[key].append(state_q99_higher(values))
    thresholds = {}
    for row in registry:
        threshold, ucb, preimage_sha = bootstrap_ucb(
            state_values[row["endpoint_id"]],
            resolution_floor=row["resolution_floor"],
        )
        thresholds[row["endpoint_id"]] = {
            "units": row["units"],
            "state_q99_values": state_values[row["endpoint_id"]],
            "bootstrap_ucb": ucb,
            "resolution_floor": row["resolution_floor"],
            "threshold": threshold,
            "comparison": "error <= threshold",
            "bootstrap_index_preimage_sha256": preimage_sha,
        }
    report = {
        "schema_version": "camp_dp_v25_batch8_generator_calibration_threshold_v1",
        "status": "PASS",
        "raw_root_sha256": raw_root,
        "raw_review_root_sha256": review_root,
        "run_count": 320,
        "pair_count": pair_count,
        "independent_state_count": 64,
        "thresholds": thresholds,
        "interpretation": "bounded_development_repeatability_envelope_not_validation_or_effect_claim",
        "selector_training_support_safetycost_claim_count": 0,
        "outcome_read": False,
    }
    return _atomic(output, report)


def _atomic(output: Path, report: dict) -> str:
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=output.parent))
    try:
        (staging / "report.json").write_text(json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n", encoding="ascii")
        root = seal_artifact(staging, label="V25 batch8 generator calibration thresholds")
        os.replace(staging, output)
        verify_complete_seal(output, root, label="V25 batch8 generator calibration thresholds")
        return root
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--raw-dir", type=Path, default=Path(EXACT_DIRS["raw"]))
    p.add_argument("--raw-root", required=True)
    p.add_argument("--raw-review-dir", type=Path, default=Path(EXACT_DIRS["raw_review"]))
    p.add_argument("--raw-review-root", required=True)
    p.add_argument("--output", type=Path, default=Path(EXACT_DIRS["threshold"]))
    a = p.parse_args()
    print(materialize(a.raw_dir, a.raw_root, a.raw_review_dir, a.raw_review_root, a.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
