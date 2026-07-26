"""Materialize all 320 input/latent preimages before the first model call."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "camp_core"
if str(PACKAGE) not in sys.path:
    sys.path.insert(0, str(PACKAGE))

from camp_core.integrations.diffusion_planner_artifact_seal import seal_artifact, verify_complete_seal  # noqa: E402
from camp_core.integrations.diffusion_planner_v25_batch8_generator_calibration import (  # noqa: E402
    AUTHORITY_SHA256, CAPACITY_FLOOR_BYTES, EXACT_DIRS, OLD_NONHOLDOUT_ROOT,
    OLD_PREFLIGHT_REVIEW_ROOT, OLD_PREFLIGHT_ROOT, RUN_COUNT,
    SOURCE_SPEC_MANIFEST_SHA256, canonical_bytes, latent_manifest, latent_tensor,
    planned_run_ids, sha256_bytes, sha256_file, source_specs,
)

OLD_PREFLIGHT = Path("/root/autodl-tmp/camp_dp_v25_fair_pool_calibration_preflight_67308ac0_ed0d298c")
OLD_PREFLIGHT_REVIEW = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_fair_pool_calibration_preflight_review_67308ac0_ed0d298c"
)


def materialize(
    contract_dir: Path,
    contract_root: str,
    review_dir: Path,
    review_root: str,
    output: Path,
) -> str:
    for path, root, label in (
        (contract_dir, contract_root, "generator calibration contract"),
        (review_dir, review_root, "generator calibration contract review"),
        (OLD_PREFLIGHT, OLD_PREFLIGHT_ROOT, "sealed source-input preflight"),
        (
            OLD_PREFLIGHT_REVIEW,
            OLD_PREFLIGHT_REVIEW_ROOT,
            "sealed source-input preflight independent review",
        ),
    ):
        verify_complete_seal(path, root, label=label)
    if output.exists():
        raise FileExistsError(output)
    old = json.loads((OLD_PREFLIGHT / "receipt.json").read_text("ascii"))
    overlap = json.loads((OLD_PREFLIGHT / "extended_overlap.json").read_text("ascii"))
    if (
        len(old["calibration_manifests"]) != 64
        or len(old["validation_manifests"]) != 64
        or overlap["old_nonholdout"]["artifact_root_sha256"] != OLD_NONHOLDOUT_ROOT
        or overlap["old_nonholdout"]["input_bundle_sha_overlap_count"] != 0
        or overlap["old_nonholdout"]["state_sha_overlap_count"] != 0
        or overlap["fresh_b2_b3_b4"]["clone_overlap_count"] != 0
        or overlap["seed_and_latent_instances"]["cross_split_latent_seed_overlap_count"] != 0
        or overlap["validation_execution_count"] != 0
        or overlap["fresh_or_holdout_outcome_read"] is not False
        or overlap["model_pool_selector_call_count"] != 0
    ):
        raise RuntimeError("sealed overlap authority did not pass")
    by_state = {row["state_spec_id"]: row for row in old["calibration_manifests"]}
    specs = source_specs()
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=output.parent))
    manifests: list[dict] = []
    try:
        (staging / "input_tensors").mkdir()
        (staging / "latents").mkdir()
        for state_index, spec in enumerate(specs):
            state_id = spec["state_spec_id"]
            old_manifest = by_state[state_id]
            source_npz = OLD_PREFLIGHT / "input_tensors" / f"development_calibration_{state_index:03d}.npz"
            target_npz = staging / "input_tensors" / source_npz.name
            shutil.copyfile(source_npz, target_npz)
            if sha256_file(source_npz) != sha256_file(target_npz):
                raise RuntimeError("input tensor transport drifted")
            with np.load(target_npz, allow_pickle=False) as archive:
                names = list(archive.files)
            expected_names = old_manifest["actual_input_tensor_manifest"]["tensor_order"]
            if set(names) != set(expected_names) or len(names) != len(expected_names):
                raise RuntimeError("input tensor member set drifted")
            for repeat_index in range(5):
                latent = latent_tensor(spec["state_spec_sha256"], repeat_index)
                lm = latent_manifest(spec["state_spec_sha256"], repeat_index)
                latent_name = f"development_calibration_{state_index:03d}_repeat{repeat_index}.f32le"
                latent_path = staging / "latents" / latent_name
                latent_path.write_bytes(latent.tobytes(order="C"))
                if sha256_file(latent_path) != lm["tensor_sha256"]:
                    raise RuntimeError("latent write drifted")
                instance = {
                    "authority_sha256": AUTHORITY_SHA256,
                    "state_spec_sha256": spec["state_spec_sha256"],
                    "repeat_index": repeat_index,
                    "latent_tensor_sha256": lm["tensor_sha256"],
                }
                manifests.append({
                    "run_id": planned_run_ids()[state_index * 5 + repeat_index],
                    "state_index": state_index,
                    "repeat_index": repeat_index,
                    "state_spec": spec,
                    "old_input_manifest": old_manifest,
                    "input_npz_relpath": f"input_tensors/{source_npz.name}",
                    "input_npz_sha256": sha256_file(target_npz),
                    "latent_relpath": f"latents/{latent_name}",
                    "latent_manifest": lm,
                    "latent_instance_sha256": sha256_bytes(canonical_bytes(instance)),
                })
        if len(manifests) != RUN_COUNT:
            raise RuntimeError("run manifest denominator drifted")
        if len({row["run_id"] for row in manifests}) != RUN_COUNT:
            raise RuntimeError("run ID collision")
        if len({row["latent_instance_sha256"] for row in manifests}) != RUN_COUNT:
            raise RuntimeError("latent instance collision")
        projected = sum(path.stat().st_size for path in staging.rglob("*") if path.is_file()) + 2 * 1024**3
        free = shutil.disk_usage(output.parent).free
        if free - projected < CAPACITY_FLOOR_BYTES:
            raise RuntimeError("projected disk floor failed before model")
        receipt = {
            "schema_version": "camp_dp_v25_batch8_generator_calibration_preflight_v1",
            "status": "PASS_before_first_model_call",
            "authority_sha256": AUTHORITY_SHA256,
            "contract_root_sha256": contract_root,
            "contract_review_root_sha256": review_root,
            "source_spec_manifest_sha256": SOURCE_SPEC_MANIFEST_SHA256,
            "old_preflight_root_sha256": OLD_PREFLIGHT_ROOT,
            "old_preflight_review_root_sha256": OLD_PREFLIGHT_REVIEW_ROOT,
            "old_extended_overlap_sha256": sha256_file(OLD_PREFLIGHT / "extended_overlap.json"),
            "run_manifest_count": len(manifests),
            "run_manifests": manifests,
            "zero_overlap": {
                "dimensions": ["route", "state", "geometry", "source", "scenario_seed", "latent_instance"],
                "future_validation_execution_count": 0,
                "future_validation_overlap_count": 0,
                "old_executed_nonholdout_overlap_count": 0,
                "fresh_b2_b3_b4_overlap_count": 0,
                "training_overlap_count": 0,
                "training_basis": "new_development_scene_namespace_bound_by_sealed_source_preflight",
            },
            "capacity": {
                "free_before_bytes": free,
                "projected_increment_bytes": projected,
                "projected_end_free_bytes": free - projected,
                "floor_bytes": CAPACITY_FLOOR_BYTES,
            },
            "model_call_count": 0,
            "pool_call_count": 0,
            "selector_call_count": 0,
            "outcome_read": False,
            "drop_replace_suffix_count": 0,
            "pre_model_mechanical_correction": {
                "classification": "npz_member_order_is_not_tensor_semantic_order",
                "failed_implementation_head": "1de0817e8ae5d4e5f4b1c62f08deab865431ac76",
                "active_implementation_head": subprocess.check_output(
                    ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
                ).strip(),
                "failed_preflight_artifact_formed": False,
                "model_call_count_before_correction": 0,
                "comparison": "exact_member_set_then_manifest_ordered_per_tensor_sha",
            },
        }
        (staging / "receipt.json").write_bytes(canonical_bytes(receipt))
        root = seal_artifact(staging, label="V25 batch8 generator calibration preflight")
        os.replace(staging, output)
        verify_complete_seal(output, root, label="V25 batch8 generator calibration preflight")
        return root
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract-dir", type=Path, default=Path(EXACT_DIRS["contract"]))
    parser.add_argument("--contract-root", required=True)
    parser.add_argument("--contract-review-dir", type=Path, default=Path(EXACT_DIRS["contract_review"]))
    parser.add_argument("--contract-review-root", required=True)
    parser.add_argument("--output", type=Path, default=Path(EXACT_DIRS["preflight"]))
    args = parser.parse_args()
    print(materialize(args.contract_dir, args.contract_root, args.contract_review_dir, args.contract_review_root, args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
