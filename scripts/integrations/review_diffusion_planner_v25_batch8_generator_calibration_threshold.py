"""Independent threshold review from raw calibration bytes."""

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
from camp_core.integrations.diffusion_planner_v25_batch8_generator_calibration import EXACT_DIRS  # noqa: E402
from camp_core.integrations.diffusion_planner_v25_batch8_generator_calibration_review import (  # noqa: E402
    CANDIDATE_SHAPE, F32, NEIGHBOR_SHAPE, bootstrap, endpoint_registry,
    pair_errors, state_q99,
)


def review(raw_dir: Path, raw_root: str, threshold_dir: Path, threshold_root: str, output: Path) -> str:
    verify_complete_seal(raw_dir, raw_root, label="generator calibration raw")
    verify_complete_seal(threshold_dir, threshold_root, label="generator calibration thresholds")
    supplied = json.loads((threshold_dir / "report.json").read_text("ascii"))
    runs = {}
    latent_by_state = {}
    input_by_state = {}
    for slot in range(320):
        receipt = json.loads((raw_dir / "runs" / f"{slot:03d}" / "receipt.json").read_text("ascii"))
        candidate = np.fromfile(raw_dir / receipt["candidate_relpath"], dtype=F32).reshape(CANDIDATE_SHAPE)
        neighbor = np.fromfile(raw_dir / receipt["neighbor_relpath"], dtype=F32).reshape(NEIGHBOR_SHAPE)
        runs[(receipt["state_index"], receipt["repeat_index"])] = (candidate, neighbor)
        latent_by_state.setdefault(receipt["state_index"], set()).add(
            receipt["latent_manifest"]["tensor_sha256"]
        )
        input_by_state.setdefault(receipt["state_index"], set()).add(
            receipt["input_npz_sha256"]
        )
    if (
        any(len(values) != 1 for values in latent_by_state.values())
        or any(len(values) != 1 for values in input_by_state.values())
    ):
        raise RuntimeError("threshold input/latent reuse drifted")
    expected = {}
    for row in endpoint_registry():
        states = []
        for state in range(64):
            pairs = []
            for left, right in combinations(range(5), 2):
                pairs.append(pair_errors(*runs[(state, left)], *runs[(state, right)])[row["endpoint_id"]])
            states.append(state_q99(pairs))
        threshold, ucb, preimage = bootstrap(states, row["resolution_floor"])
        expected[row["endpoint_id"]] = {
            "units": row["units"],
            "state_q99_values": states,
            "bootstrap_ucb": ucb,
            "resolution_floor": row["resolution_floor"],
            "threshold": threshold,
            "comparison": "error <= threshold",
            "bootstrap_index_preimage_sha256": preimage,
        }
    if supplied["thresholds"] != expected or supplied["pair_count"] != 640:
        raise RuntimeError("threshold independent reconstruction drifted")
    report = {
        "schema_version": "camp_dp_v25_batch8_generator_repeatability_corrected_threshold_independent_review_v1",
        "status": "PASS",
        "reviewed_raw_root_sha256": raw_root,
        "reviewed_threshold_root_sha256": threshold_root,
        "endpoint_count": len(expected),
        "run_count": 320,
        "pair_count": 640,
        "state_count": 64,
        "bootstrap_preimage_rebuilt": True,
        "same_state_input_sha_cardinality": 1,
        "same_state_latent_tensor_sha_cardinality": 1,
        "producer_endpoint_threshold_oracle_imported": False,
        "selector_training_support_effect_claim_count": 0,
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
        root = seal_artifact(staging, label="V25 batch8 generator calibration threshold independent review")
        os.replace(staging, output)
        verify_complete_seal(output, root, label="V25 batch8 generator calibration threshold independent review")
        return root
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--raw-dir", type=Path, default=Path(EXACT_DIRS["raw"]))
    p.add_argument("--raw-root", required=True)
    p.add_argument("--threshold-dir", type=Path, default=Path(EXACT_DIRS["threshold"]))
    p.add_argument("--threshold-root", required=True)
    p.add_argument("--output", type=Path, default=Path(EXACT_DIRS["threshold_review"]))
    a = p.parse_args()
    print(review(a.raw_dir, a.raw_root, a.threshold_dir, a.threshold_root, a.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
