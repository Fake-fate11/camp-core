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
    F32, LATENT_SHAPE, latent, review_canonical_expansion,
    review_latent_manifest, sha256_bytes, source_specs,
)

OLD_PREFLIGHT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_fair_pool_calibration_preflight_67308ac0_ed0d298c"
)
OLD_PREFLIGHT_ROOT = (
    "5156f98f0172fbd22ed2c21dfd79d236ce53544bf796006e41e29918ec667a22"
)


def review(preflight: Path, root_sha: str, output: Path) -> str:
    verify_complete_seal(preflight, root_sha, label="generator calibration preflight")
    verify_complete_seal(
        OLD_PREFLIGHT,
        OLD_PREFLIGHT_ROOT,
        label="sealed source-input preflight",
    )
    receipt = json.loads((preflight / "receipt.json").read_text("ascii"))
    old = json.loads((OLD_PREFLIGHT / "receipt.json").read_text("ascii"))
    if receipt["status"] != "PASS_before_first_model_call" or receipt["run_manifest_count"] != 320:
        raise RuntimeError("preflight status drifted")
    if any(receipt[key] != 0 for key in ("model_call_count", "pool_call_count", "selector_call_count")):
        raise RuntimeError("preflight call counter drifted")
    specs = source_specs()
    manifests = receipt["run_manifests"]
    review_canonical_expansion(manifests)
    records = receipt["canonical_state_latent_records"]
    if len(records) != 64:
        raise RuntimeError("canonical record denominator drifted")
    rebuilt_record_shas = {}
    for record in records:
        payload = dict(record)
        digest = payload.pop("canonical_record_sha256", None)
        rebuilt = sha256_bytes(
            (
                json.dumps(
                    payload,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                    allow_nan=False,
                )
                + "\n"
            ).encode("ascii")
        )
        if digest != rebuilt:
            raise RuntimeError("canonical record SHA drifted")
        rebuilt_record_shas[record["state_index"]] = digest
    latent_tensors_by_state: dict[int, set[str]] = {}
    input_tensors_by_state: dict[int, set[str]] = {}
    records_by_state: dict[int, set[str]] = {}
    for row in manifests:
        spec = specs[row["state_index"]]
        if row["state_spec"] != spec or row["repeat_index"] not in range(5):
            raise RuntimeError("preflight state/repeat drifted")
        clone_key = row["old_input_manifest"]["clone_key_sha256"]
        if row["canonical_state_clone_key_sha256"] != clone_key:
            raise RuntimeError("canonical clone key drifted")
        if row["canonical_record_sha256"] != rebuilt_record_shas[
            row["state_index"]
        ]:
            raise RuntimeError("run expansion canonical record binding drifted")
        expected = latent(clone_key)
        path = preflight / row["latent_relpath"]
        actual = np.fromfile(path, dtype=F32).reshape(LATENT_SHAPE)
        if not np.array_equal(actual, expected):
            raise RuntimeError("latent raw bytes drifted")
        review_latent_manifest(
            row["latent_manifest"], spec["state_spec_sha256"], clone_key
        )
        if sha256_bytes(path.read_bytes()) != row["latent_manifest"]["tensor_sha256"]:
            raise RuntimeError("latent file SHA drifted")
        input_path = preflight / row["input_npz_relpath"]
        with np.load(input_path, allow_pickle=False) as archive:
            expected_names = row["old_input_manifest"]["actual_input_tensor_manifest"]["tensor_order"]
            if set(archive.files) != set(expected_names) or len(archive.files) != len(expected_names):
                raise RuntimeError("input tensor member set drifted")
            for tensor in row["old_input_manifest"]["actual_input_tensor_manifest"]["tensors"]:
                value = np.ascontiguousarray(archive[tensor["name"]])
                if list(value.shape) != tensor["shape"] or value.dtype.str != tensor["dtype"]:
                    raise RuntimeError("input tensor shape/dtype drifted")
                if sha256_bytes(value.tobytes(order="C")) != tensor["tensor_sha256"]:
                    raise RuntimeError("input tensor SHA drifted")
        latent_tensors_by_state.setdefault(row["state_index"], set()).add(
            row["latent_manifest"]["tensor_sha256"]
        )
        input_tensors_by_state.setdefault(row["state_index"], set()).add(
            row["input_npz_sha256"]
        )
        records_by_state.setdefault(row["state_index"], set()).add(
            row["canonical_record_sha256"]
        )
    if (
        set(latent_tensors_by_state) != set(range(64))
        or any(len(values) != 1 for values in latent_tensors_by_state.values())
        or any(len(values) != 1 for values in input_tensors_by_state.values())
        or any(len(values) != 1 for values in records_by_state.values())
        or receipt["canonical_state_latent_record_count"] != 64
        or len(receipt["canonical_state_latent_records"]) != 64
    ):
        raise RuntimeError("same-state input/latent reuse invariant drifted")
    new_latent_shas = {
        row["latent_manifest"]["tensor_sha256"] for row in records
    }
    for split in ("calibration_manifests", "validation_manifests"):
        old_latent_shas = {
            row["actual_latent_tensor_manifest"]["tensor_sha256"]
            for row in old[split]
        }
        if new_latent_shas.intersection(old_latent_shas):
            raise RuntimeError("independent latent overlap reconstruction failed")
    overlap = receipt["zero_overlap"]
    if (
        overlap["future_validation_execution_count"] != 0
        or any(overlap[key] != 0 for key in (
            "future_validation_overlap_count", "old_executed_nonholdout_overlap_count",
            "fresh_b2_b3_b4_overlap_count", "training_overlap_count",
            "old_calibration_latent_tensor_overlap_count",
            "future_validation_latent_tensor_overlap_count",
        ))
    ):
        raise RuntimeError("zero-overlap receipt failed")
    report = {
        "schema_version": "camp_dp_v25_batch8_generator_repeatability_corrected_preflight_independent_review_v1",
        "status": "PASS",
        "reviewed_preflight_root_sha256": root_sha,
        "raw_input_tensor_manifests_rebuilt": 320,
        "raw_latent_expansions_rebuilt": 320,
        "canonical_state_latent_preimages_rebuilt": 64,
        "same_state_input_sha_cardinality": 1,
        "same_state_latent_tensor_sha_cardinality": 1,
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
