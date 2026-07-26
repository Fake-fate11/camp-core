"""Freeze 64 canonical input/latents and their 320-repeat expansion."""

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
    PREFLIGHT_SCHEMA, SOURCE_SPEC_MANIFEST_SHA256, canonical_bytes,
    latent_manifest, latent_tensor,
    planned_run_ids, sha256_bytes, sha256_file, source_specs,
    validate_canonical_expansion,
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
    canonical_records: list[dict] = []
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
            clone_key = old_manifest["clone_key_sha256"]
            latent = latent_tensor(clone_key)
            lm = latent_manifest(spec["state_spec_sha256"], clone_key)
            latent_name = f"development_calibration_{state_index:03d}.f32le"
            latent_path = staging / "latents" / latent_name
            latent_path.write_bytes(latent.tobytes(order="C"))
            if sha256_file(latent_path) != lm["tensor_sha256"]:
                raise RuntimeError("canonical latent write drifted")
            canonical_record = {
                "state_index": state_index,
                "state_spec": spec,
                "canonical_state_clone_key_sha256": clone_key,
                "old_input_manifest": old_manifest,
                "input_npz_relpath": f"input_tensors/{source_npz.name}",
                "input_npz_sha256": sha256_file(target_npz),
                "latent_relpath": f"latents/{latent_name}",
                "latent_manifest": lm,
            }
            canonical_record["canonical_record_sha256"] = sha256_bytes(
                canonical_bytes(canonical_record)
            )
            canonical_records.append(canonical_record)
            for repeat_index in range(5):
                manifests.append({
                    "run_id": planned_run_ids()[state_index * 5 + repeat_index],
                    "state_index": state_index,
                    "repeat_index": repeat_index,
                    "canonical_record_sha256": canonical_record[
                        "canonical_record_sha256"
                    ],
                    **{
                        key: canonical_record[key]
                        for key in (
                            "state_spec",
                            "canonical_state_clone_key_sha256",
                            "old_input_manifest",
                            "input_npz_relpath",
                            "input_npz_sha256",
                            "latent_relpath",
                            "latent_manifest",
                        )
                    },
                })
        if len(manifests) != RUN_COUNT:
            raise RuntimeError("run manifest denominator drifted")
        if len({row["run_id"] for row in manifests}) != RUN_COUNT:
            raise RuntimeError("run ID collision")
        validate_canonical_expansion(manifests)
        if len(canonical_records) != 64:
            raise RuntimeError("canonical record denominator drifted")
        new_latent_shas = {
            row["latent_manifest"]["tensor_sha256"]
            for row in canonical_records
        }
        old_calibration_latent_shas = {
            row["actual_latent_tensor_manifest"]["tensor_sha256"]
            for row in old["calibration_manifests"]
        }
        future_validation_latent_shas = {
            row["actual_latent_tensor_manifest"]["tensor_sha256"]
            for row in old["validation_manifests"]
        }
        if (
            new_latent_shas.intersection(old_calibration_latent_shas)
            or new_latent_shas.intersection(future_validation_latent_shas)
        ):
            raise RuntimeError("canonical latent instance overlap drifted")
        for state_index in range(64):
            rows = [
                row for row in manifests if row["state_index"] == state_index
            ]
            if (
                len(rows) != 5
                or len({row["input_npz_sha256"] for row in rows}) != 1
                or len(
                    {
                        row["latent_manifest"]["tensor_sha256"]
                        for row in rows
                    }
                )
                != 1
                or len({row["canonical_record_sha256"] for row in rows}) != 1
            ):
                raise RuntimeError("same-state canonical expansion drifted")
        projected = sum(path.stat().st_size for path in staging.rglob("*") if path.is_file()) + 2 * 1024**3
        free = shutil.disk_usage(output.parent).free
        if free - projected < CAPACITY_FLOOR_BYTES:
            raise RuntimeError("projected disk floor failed before model")
        receipt = {
            "schema_version": PREFLIGHT_SCHEMA,
            "status": "PASS_before_first_model_call",
            "authority_sha256": AUTHORITY_SHA256,
            "contract_root_sha256": contract_root,
            "contract_review_root_sha256": review_root,
            "source_spec_manifest_sha256": SOURCE_SPEC_MANIFEST_SHA256,
            "old_preflight_root_sha256": OLD_PREFLIGHT_ROOT,
            "old_preflight_review_root_sha256": OLD_PREFLIGHT_REVIEW_ROOT,
            "old_extended_overlap_sha256": sha256_file(OLD_PREFLIGHT / "extended_overlap.json"),
            "run_manifest_count": len(manifests),
            "canonical_state_latent_record_count": len(canonical_records),
            "canonical_state_latent_records": canonical_records,
            "run_manifests": manifests,
            "zero_overlap": {
                "dimensions": ["route", "state", "geometry", "source", "scenario_seed", "latent_instance"],
                "future_validation_execution_count": 0,
                "future_validation_overlap_count": 0,
                "old_executed_nonholdout_overlap_count": 0,
                "fresh_b2_b3_b4_overlap_count": 0,
                "training_overlap_count": 0,
                "training_basis": "new_development_scene_namespace_bound_by_sealed_source_preflight",
                "old_calibration_latent_tensor_overlap_count": 0,
                "future_validation_latent_tensor_overlap_count": 0,
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
            "scientific_contract_correction": {
                "classification": (
                    "same_input_same_latent_repeatability_replacement"
                ),
                "superseded_classification": (
                    "bounded_development_latent_resampled_candidate_pool_"
                    "dispersion_diagnostic"
                ),
                "active_implementation_head": subprocess.check_output(
                    ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
                ).strip(),
                "old_raw_or_threshold_used": False,
                "seed_depends_on_repeat_index": False,
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
