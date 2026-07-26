"""Independent raw-byte review of the 320-run input/latent preflight."""

from __future__ import annotations

import argparse
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
    F32, LATENT_SHAPE, latent, review_latent_manifest, sha256_bytes, source_specs,
)


def review(preflight: Path, root_sha: str, output: Path) -> str:
    verify_complete_seal(preflight, root_sha, label="generator calibration preflight")
    receipt = json.loads((preflight / "receipt.json").read_text("ascii"))
    if receipt["status"] != "PASS_before_first_model_call" or receipt["run_manifest_count"] != 320:
        raise RuntimeError("preflight status drifted")
    if any(receipt[key] != 0 for key in ("model_call_count", "pool_call_count", "selector_call_count")):
        raise RuntimeError("preflight call counter drifted")
    specs = source_specs()
    manifests = receipt["run_manifests"]
    latent_instances = set()
    for row in manifests:
        spec = specs[row["state_index"]]
        if row["state_spec"] != spec or row["repeat_index"] not in range(5):
            raise RuntimeError("preflight state/repeat drifted")
        expected = latent(spec["state_spec_sha256"], row["repeat_index"])
        path = preflight / row["latent_relpath"]
        actual = np.fromfile(path, dtype=F32).reshape(LATENT_SHAPE)
        if not np.array_equal(actual, expected):
            raise RuntimeError("latent raw bytes drifted")
        review_latent_manifest(row["latent_manifest"], spec["state_spec_sha256"], row["repeat_index"])
        if sha256_bytes(path.read_bytes()) != row["latent_manifest"]["tensor_sha256"]:
            raise RuntimeError("latent file SHA drifted")
        input_path = preflight / row["input_npz_relpath"]
        with np.load(input_path, allow_pickle=False) as archive:
            if list(archive.files) != row["old_input_manifest"]["actual_input_tensor_manifest"]["tensor_order"]:
                raise RuntimeError("input tensor order drifted")
            for tensor in row["old_input_manifest"]["actual_input_tensor_manifest"]["tensors"]:
                value = np.ascontiguousarray(archive[tensor["name"]])
                if list(value.shape) != tensor["shape"] or value.dtype.str != tensor["dtype"]:
                    raise RuntimeError("input tensor shape/dtype drifted")
                if sha256_bytes(value.tobytes(order="C")) != tensor["tensor_sha256"]:
                    raise RuntimeError("input tensor SHA drifted")
        latent_instances.add(row["latent_instance_sha256"])
    if len(latent_instances) != 320:
        raise RuntimeError("latent instance uniqueness drifted")
    overlap = receipt["zero_overlap"]
    if (
        overlap["future_validation_execution_count"] != 0
        or any(overlap[key] != 0 for key in (
            "future_validation_overlap_count", "old_executed_nonholdout_overlap_count",
            "fresh_b2_b3_b4_overlap_count", "training_overlap_count"
        ))
    ):
        raise RuntimeError("zero-overlap receipt failed")
    report = {
        "schema_version": "camp_dp_v25_batch8_generator_calibration_preflight_independent_review_v1",
        "status": "PASS",
        "reviewed_preflight_root_sha256": root_sha,
        "raw_input_tensor_manifests_rebuilt": 320,
        "raw_latent_preimages_rebuilt": 320,
        "unique_latent_instance_count": 320,
        "state_count": 64,
        "repeat_count": 5,
        "model_pool_selector_call_count": 0,
        "outcome_read": False,
        "producer_manifest_oracle_imported": False,
    }
    return _atomic(output, report)


def _atomic(output: Path, report: dict) -> str:
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=output.parent))
    try:
        (staging / "report.json").write_text(json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n", encoding="ascii")
        root = seal_artifact(staging, label="V25 batch8 generator calibration preflight independent review")
        os.replace(staging, output)
        verify_complete_seal(output, root, label="V25 batch8 generator calibration preflight independent review")
        return root
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", type=Path, default=Path(EXACT_DIRS["preflight"]))
    parser.add_argument("--preflight-root", required=True)
    parser.add_argument("--output", type=Path, default=Path(EXACT_DIRS["preflight_review"]))
    args = parser.parse_args()
    print(review(args.preflight, args.preflight_root, args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
