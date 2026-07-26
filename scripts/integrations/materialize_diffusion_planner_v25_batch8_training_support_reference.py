"""Acquire the one authorized 1000-pool batch8 training-support reference."""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_causal_atoms import (  # noqa: E402
    materialize_canonical_14d,
)
from camp_core.integrations.diffusion_planner_v25_batch8_training_support_reference import (  # noqa: E402
    CAPACITY_FLOOR_BYTES,
    FIXED_DP_HEAD,
    POOL_COUNT,
    PROHIBITED_RUNS,
    ROW_COUNT,
    canonical_bytes,
    inclusive_reference_interval,
    pool_field_registry,
    row_field_registry,
    sha256_bytes,
    validate_contract,
)
from camp_core.integrations.diffusion_planner_v25_context import (  # noqa: E402
    CONTEXT_SCHEMA_VERSION,
    RAW_FEATURE_NAMES,
    build_v25_raw_context,
)
from camp_core.integrations.diffusion_planner_v25_scene_runtime import (  # noqa: E402
    load_v25_runtime_selector_assets,
)
from scripts.integrations.run_diffusion_planner_camp_replay import (  # noqa: E402
    _load_model,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v18 import (  # noqa: E402
    _fixed_dp_red_cost,
    candidate_signal_source_available_mask,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v19_worker import (  # noqa: E402
    select_camp_candidate,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: E402
    V22_SOURCE_VALID_SELECTION,
)


TRAINING_ARTIFACT = Path(
    "/root/autodl-tmp/camp_dp_v25_camp_training_863e28da_20260722T103219CST"
)
TRAINING_ROOT = (
    "8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9"
)
TRAINING_REVIEW = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_camp_training_review_8fecda47_20260722T122701CST"
)
TRAINING_REVIEW_ROOT = (
    "ef2e9748a9ba0fff5b35f010cba6efd1b16d8e1dc0d562f5a7960c8dcb3d9be9"
)
PROBE_CONFIG = Path(
    "/root/autodl-tmp/"
    "camp_dp_v24_fixed_dp_single_record_source_probe_preflight_retry_"
    "a53d6ee3_20260715T204719CST/prepared/probe_config.json"
)


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"{path} must contain object")
    return value


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True
    ).strip()


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _arrays(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as archive:
        return {
            name: np.ascontiguousarray(np.asarray(archive[name]))
            for name in archive.files
        }


def _expand(
    inputs: Mapping[str, np.ndarray], latent: np.ndarray
) -> dict[str, np.ndarray]:
    expanded = {}
    for name, value in inputs.items():
        if value.shape[0] != 1:
            raise RuntimeError("preflight input ceased to be single ego")
        expanded[name] = np.ascontiguousarray(np.repeat(value, 8, axis=0))
    if expanded["sampled_trajectories"].shape != latent.shape:
        raise RuntimeError("expanded model latent shape drifted")
    expanded["sampled_trajectories"] = np.ascontiguousarray(latent.copy())
    if any(
        not np.array_equal(value[0], value[index])
        for name, value in expanded.items()
        if name != "sampled_trajectories"
        for index in range(1, 8)
    ):
        raise RuntimeError("expanded nonlatent input rows differ")
    return expanded


def _runtime_fingerprint(device: str, torch: Any) -> dict[str, Any]:
    value = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "torch": str(torch.__version__),
        "cuda": str(torch.version.cuda),
        "device": device,
        "device_name": (
            torch.cuda.get_device_name(torch.device(device))
            if device.startswith("cuda")
            else "cpu"
        ),
    }
    value["sha256"] = sha256_bytes(canonical_bytes(value))
    return value


def _mask_margin(selection: Mapping[str, Any]) -> tuple[np.ndarray, float, int]:
    mask = np.asarray(selection["source_valid_mask"])
    scores = np.asarray(selection["scores"], dtype=np.float64)
    if mask.dtype != np.bool_ or mask.shape != (8,) or scores.shape != (8,):
        raise RuntimeError("selector mask/score shape drifted")
    eligible = np.flatnonzero(mask)
    if eligible.size < 2:
        raise RuntimeError("selector margin needs at least two eligible rows")
    ordered = np.sort(scores[eligible], kind="stable")
    return mask.copy(), float(ordered[1] - ordered[0]), int(eligible.size)


def _pool_first(values: np.ndarray) -> dict[str, Any]:
    if values.shape[0] != POOL_COUNT:
        raise ValueError("pool-first denominator drifted")
    finite = np.isfinite(values)
    return {
        "pool_count": POOL_COUNT,
        "complete_pool_count": int(np.all(finite, axis=1).sum()),
        "missing_pool_count": int((~np.all(finite, axis=1)).sum()),
        "per_pool_mean": np.where(
            np.all(finite, axis=1), np.mean(values, axis=1), np.nan
        ).tolist(),
        "per_pool_min": np.where(
            np.all(finite, axis=1), np.min(values, axis=1), np.nan
        ).tolist(),
        "per_pool_max": np.where(
            np.all(finite, axis=1), np.max(values, axis=1), np.nan
        ).tolist(),
    }


def _reference(values: np.ndarray, expected: int) -> dict[str, Any]:
    flat = np.asarray(values, dtype=np.float64).reshape(-1)
    if flat.size != expected:
        raise ValueError("reference denominator drifted")
    if not np.isfinite(flat).all():
        return {
            "status": "evidence_missing",
            "expected_value_count": expected,
            "finite_value_count": int(np.isfinite(flat).sum()),
            "values_sha256": sha256_bytes(
                np.ascontiguousarray(flat).tobytes(order="C")
            ),
        }
    return {
        "status": "computed",
        "expected_value_count": expected,
        "finite_value_count": expected,
        "values_sha256": sha256_bytes(
            np.ascontiguousarray(flat).tobytes(order="C")
        ),
        "interval": inclusive_reference_interval(flat.tolist()),
    }


def materialize(
    *,
    repo: Path,
    fixed_dp_repo: Path,
    implementation_head: str,
    contract_dir: Path,
    contract_root: str,
    contract_review_dir: Path,
    contract_review_root: str,
    preflight_dir: Path,
    preflight_root: str,
    preflight_review_dir: Path,
    preflight_review_root: str,
    output: Path,
    device: str,
) -> str:
    import torch

    if (
        output.exists()
        or _git(repo, "rev-parse", "HEAD") != implementation_head
        or _git(repo, "status", "--porcelain=v1", "--untracked-files=no")
        or _git(fixed_dp_repo, "rev-parse", "HEAD") != FIXED_DP_HEAD
        or _git(
            fixed_dp_repo, "status", "--porcelain=v1", "--untracked-files=no"
        )
        or shutil.disk_usage(output.parent).free < CAPACITY_FLOOR_BYTES
    ):
        raise RuntimeError("raw acquisition tracked/capacity authority drifted")
    for path, root, label in (
        (contract_dir, contract_root, "training-support contract"),
        (contract_review_dir, contract_review_root, "training-support contract review"),
        (preflight_dir, preflight_root, "training-support input preflight"),
        (preflight_review_dir, preflight_review_root, "training-support input preflight review"),
        (TRAINING_ARTIFACT, TRAINING_ROOT, "accepted training"),
        (TRAINING_REVIEW, TRAINING_REVIEW_ROOT, "accepted training review"),
    ):
        verify_complete_seal(path, root, label=label)
    contract = validate_contract(_json(contract_dir / "contract.json"))
    preflight = _json(preflight_dir / "report.json")
    preflight_review = _json(preflight_review_dir / "report.json")
    manifest = _json(preflight_dir / "manifest.json")
    if (
        contract["implementation_head"] != implementation_head
        or contract["exact_dirs"]["raw"] != str(output)
        or preflight.get("status")
        != "passed_before_first_training_support_model_call"
        or preflight_review.get("status")
        != "passed_independent_input_preflight_review"
        or manifest.get("selected_pool_count") != POOL_COUNT
    ):
        raise RuntimeError("raw acquisition upstream binding drifted")

    config = _json(PROBE_CONFIG)
    checkpoint = Path(config["fixed_dp"]["checkpoint"]["path"])
    args_json = Path(config["fixed_dp"]["args_json"]["path"])
    model, _model_args = _load_model(checkpoint, args_json, device)
    model.eval()
    model_source = Path(inspect.getsourcefile(model.__class__) or "")
    if not model_source.is_file():
        raise RuntimeError("fixed DP model source unavailable")
    runtime = _runtime_fingerprint(device, torch)
    assets = load_v25_runtime_selector_assets(
        training_artifact=TRAINING_ARTIFACT,
        training_root_sha256=TRAINING_ROOT,
        training_review_artifact=TRAINING_REVIEW,
        training_review_root_sha256=TRAINING_REVIEW_ROOT,
    )
    if assets.atom_scales_sha256 != contract["training_scale_sha256"]:
        raise RuntimeError("training scale authority drifted")

    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output.name}.staging.", dir=str(output.parent))
    )
    slots_dir = staging / "pool_slots"
    slots_dir.mkdir()
    atoms = np.full((POOL_COUNT, 8, 14), np.nan, dtype=np.float64)
    static_scores = np.full((POOL_COUNT, 8), np.nan, dtype=np.float64)
    scene_scores = np.full((POOL_COUNT, 8), np.nan, dtype=np.float64)
    static_masks = np.zeros((POOL_COUNT, 8), dtype=np.bool_)
    scene_masks = np.zeros((POOL_COUNT, 8), dtype=np.bool_)
    static_margin = np.full(POOL_COUNT, np.nan, dtype=np.float64)
    scene_margin = np.full(POOL_COUNT, np.nan, dtype=np.float64)
    static_eligible = np.full(POOL_COUNT, -1, dtype=np.int64)
    scene_eligible = np.full(POOL_COUNT, -1, dtype=np.int64)
    static_selected = np.full(POOL_COUNT, -1, dtype=np.int64)
    scene_selected = np.full(POOL_COUNT, -1, dtype=np.int64)
    receipts = []
    model_calls = 0
    selector_receipts = 0
    failures: dict[str, int] = {}
    try:
        receipt_path = staging / "pool_receipts.jsonl"
        with receipt_path.open("w", encoding="utf-8", newline="\n") as stream:
            for ordinal, entry in enumerate(manifest["entries"]):
                pool_id = entry["pool_id"]
                source = preflight_dir / "pools" / pool_id.replace(":", "_")
                slot = slots_dir / pool_id.replace(":", "_")
                slot.mkdir()
                failure = None
                started_ns = time.perf_counter_ns()
                candidate = np.empty((0,), dtype=np.float32)
                neighbor = np.empty((0,), dtype=np.float32)
                try:
                    inputs = _arrays(source / "model_input.npz")
                    latent = np.frombuffer(
                        (source / "latent_tensor.f32le").read_bytes(), dtype="<f4"
                    ).reshape(8, 321, 81, 4).copy()
                    expanded = _expand(inputs, latent)
                    torch_inputs = {
                        name: torch.from_numpy(value.copy()).to(device=device)
                        for name, value in expanded.items()
                    }
                    model_calls += 1
                    with torch.no_grad():
                        _encoded, outputs = model(torch_inputs)
                    prediction = np.ascontiguousarray(
                        outputs["prediction"].detach().cpu().numpy(),
                        dtype=np.float32,
                    )
                    if prediction.shape != (8, 321, 80, 4):
                        raise RuntimeError("batch8 prediction shape drifted")
                    candidate = np.ascontiguousarray(prediction[:, 0])
                    neighbor = np.ascontiguousarray(prediction[:, 1:33])
                    np.savez(
                        slot / "model_output.npz",
                        candidate=candidate,
                        neighbor=neighbor,
                    )
                    row_sha = [
                        sha256_bytes(row.tobytes(order="C")) for row in candidate
                    ]
                    if (
                        not np.isfinite(candidate).all()
                        or not np.isfinite(neighbor).all()
                        or len(set(row_sha)) != 8
                    ):
                        raise RuntimeError("batch8 pool finite/diversity hard gate failed")
                    causal = _arrays(source / "causal_input.npz")
                    signal = _json(source / "causal_signal_atom_input.json")
                    dt = float((source / "dt.txt").read_text("ascii"))
                    signals = candidate_signal_source_available_mask(
                        candidate, causal["route_lanes"]
                    )
                    red_cost = _fixed_dp_red_cost(
                        candidate, causal, fixed_dp_repo, dt
                    )
                    neighbor_valid = np.any(
                        np.abs(causal["neighbor_agents_past"]) > 1e-8,
                        axis=(1, 2),
                    )
                    materialized = materialize_canonical_14d(
                        candidates=candidate,
                        causal_input=causal,
                        neighbor_predictions=neighbor,
                        neighbor_valid_mask=neighbor_valid,
                        signal_mask=signals,
                        planned_red_light_cost=red_cost,
                        causal_signal_atom_input=signal,
                        dt=dt,
                        eligibility_policy=V22_SOURCE_VALID_SELECTION,
                    )
                    atoms[ordinal] = np.asarray(
                        materialized["atom_matrix"], dtype=np.float64
                    )
                    np.savez(
                        slot / "atom_preimage.npz",
                        atoms=atoms[ordinal],
                        physical_mask=np.asarray(
                            materialized["physical_feasible_mask"], dtype=np.bool_
                        ),
                        source_mask=np.asarray(
                            materialized["source_valid_mask"], dtype=np.bool_
                        ),
                    )
                    static = select_camp_candidate(
                        candidates=candidate,
                        materialized=materialized,
                        atom_scales=assets.atom_scales,
                        weights=assets.static14d_weights,
                        eligibility_mask_name="source_valid_mask",
                    )
                    context = build_v25_raw_context(
                        causal_input=causal,
                        candidates=candidate,
                        source_valid_mask=np.asarray(
                            materialized["source_valid_mask"], dtype=bool
                        ),
                        causal_signal_atom_input=signal,
                        v2i_signal_timing=None,
                    )
                    context_payload = {
                        "schema_version": CONTEXT_SCHEMA_VERSION,
                        "raw_context": context.as_dict(),
                        "source_complete": dict(
                            zip(
                                RAW_FEATURE_NAMES,
                                context.source_complete,
                            )
                        ),
                        "source_receipt": dict(context.source_receipt),
                    }
                    scene_weight = assets.scene14d_weight_provider(context_payload)
                    scene = select_camp_candidate(
                        candidates=candidate,
                        materialized=materialized,
                        atom_scales=assets.atom_scales,
                        weights=np.asarray(scene_weight["weights"], dtype=np.float64),
                        eligibility_mask_name="source_valid_mask",
                        simplex_nonnegative_atol=1e-12,
                    )
                    np.savez(
                        slot / "selector_preimage.npz",
                        static_scores=np.asarray(
                            static.get("scores", np.full(8, np.nan)),
                            dtype=np.float64,
                        ),
                        scene_scores=np.asarray(
                            scene.get("scores", np.full(8, np.nan)),
                            dtype=np.float64,
                        ),
                        static_mask=np.asarray(
                            static.get("source_valid_mask", np.zeros(8)),
                            dtype=np.bool_,
                        ),
                        scene_mask=np.asarray(
                            scene.get("source_valid_mask", np.zeros(8)),
                            dtype=np.bool_,
                        ),
                    )
                    for arm_name, selection, score_store, mask_store, margin_store, eligible_store, selected_store in (
                        ("Static14D", static, static_scores, static_masks, static_margin, static_eligible, static_selected),
                        ("Scene14D", scene, scene_scores, scene_masks, scene_margin, scene_eligible, scene_selected),
                    ):
                        selector_receipts += 1
                        if selection.get("status") != "ok":
                            raise RuntimeError(f"{arm_name} selector failed")
                        mask, margin, eligible_count = _mask_margin(selection)
                        score_store[ordinal] = np.asarray(
                            selection["scores"], dtype=np.float64
                        )
                        mask_store[ordinal] = mask
                        margin_store[ordinal] = margin
                        eligible_store[ordinal] = eligible_count
                        selected_store[ordinal] = int(selection["selected_index"])
                    before_sha = sha256_bytes(candidate.tobytes(order="C"))
                    np.savez(
                        slot / "raw_semantic_preimage.npz",
                        latent=latent,
                        candidate=candidate,
                        neighbor=neighbor,
                        atoms=atoms[ordinal],
                        static_scores=static_scores[ordinal],
                        scene_scores=scene_scores[ordinal],
                        static_mask=static_masks[ordinal],
                        scene_mask=scene_masks[ordinal],
                        static_selected_action=candidate[static_selected[ordinal]],
                        scene_selected_action=candidate[scene_selected[ordinal]],
                    )
                    if sha256_bytes(candidate.tobytes(order="C")) != before_sha:
                        raise RuntimeError("candidate tensor mutated after pool formation")
                except BaseException as error:
                    failure = f"{type(error).__name__}:{error}"
                    taxonomy = type(error).__name__
                    failures[taxonomy] = failures.get(taxonomy, 0) + 1
                    # Both typed selector slots are retained even when pool
                    # generation or atom evidence prevents selector execution.
                    while selector_receipts < (ordinal + 1) * 2:
                        selector_receipts += 1
                candidate_sha = (
                    sha256_bytes(candidate.tobytes(order="C"))
                    if candidate.size
                    else None
                )
                neighbor_sha = (
                    sha256_bytes(neighbor.tobytes(order="C"))
                    if neighbor.size
                    else None
                )
                receipt = {
                    "schema_version": (
                        "camp_dp_v25_batch8_training_support_pool_receipt_v1"
                    ),
                    "pool_ordinal": ordinal,
                    "pool_id": pool_id,
                    "manifest_entry_sha256": entry["manifest_entry_sha256"],
                    "input_manifest_sha256": entry[
                        "actual_input_tensor_manifest"
                    ]["bundle_sha256"],
                    "actual_state_sha256": entry["actual_state_sha256"],
                    "route_geometry_sha256": entry["source_record"][
                        "route_geometry_sha256"
                    ],
                    "source_record_sha256": entry["source_record_sha256"],
                    "latent_manifest_sha256": entry["latent_manifest"][
                        "manifest_sha256"
                    ],
                    "model_source_sha256": _sha_file(model_source),
                    "checkpoint_sha256": _sha_file(checkpoint),
                    "runtime_fingerprint_sha256": runtime["sha256"],
                    "forward_id": sha256_bytes(
                        canonical_bytes(
                            {
                                "pool_id": pool_id,
                                "model_call_ordinal": model_calls,
                                "input": entry["actual_state_sha256"],
                                "latent": entry["latent_manifest"][
                                    "manifest_sha256"
                                ],
                                "candidate": candidate_sha,
                            }
                        )
                    ),
                    "candidate_tensor_sha256": candidate_sha,
                    "neighbor_tensor_sha256": neighbor_sha,
                    "candidate_row_sha256": (
                        [
                            sha256_bytes(row.tobytes(order="C"))
                            for row in candidate
                        ]
                        if candidate.shape == (8, 80, 4)
                        else []
                    ),
                    "pool_id_binding_sha256": sha256_bytes(
                        canonical_bytes(
                            {
                                "pool_id": pool_id,
                                "candidate_tensor_sha256": candidate_sha,
                            }
                        )
                    ),
                    "candidate0_row_index": 0,
                    "formal_model_call_count": 1,
                    "selector_receipt_count": 2,
                    "post_pool_model_call_count": 0,
                    "post_pool_dp_call_count": 0,
                    "post_pool_latent_generation_count": 0,
                    "post_pool_candidate_generation_count": 0,
                    "status": "complete" if failure is None else "failed_retained",
                    "failure": failure,
                    "pool_generation_latency_ns": time.perf_counter_ns()
                    - started_ns,
                    "outcome_fields_read": [],
                }
                receipt["receipt_sha256"] = sha256_bytes(canonical_bytes(receipt))
                receipts.append(receipt)
                stream.write(
                    json.dumps(
                        receipt,
                        sort_keys=True,
                        separators=(",", ":"),
                        allow_nan=False,
                    )
                    + "\n"
                )
                stream.flush()

        row_values = {
            **{
                f"normalized_atom_{index:02d}": atoms[:, :, index]
                / float(assets.atom_scales[index])
                for index in range(14)
            },
            "score_static14d": static_scores,
            "score_scene14d": scene_scores,
        }
        pool_values = {
            "margin_static14d": static_margin,
            "margin_scene14d": scene_margin,
            "eligible_count_static14d": static_eligible.astype(np.float64),
            "eligible_count_scene14d": scene_eligible.astype(np.float64),
        }
        row_references = {
            field: _reference(values, ROW_COUNT)
            for field, values in row_values.items()
        }
        pool_references = {
            field: _reference(values, POOL_COUNT)
            for field, values in pool_values.items()
        }
        pool_first = {
            field: _pool_first(values) for field, values in row_values.items()
        }
        successful = sum(row["status"] == "complete" for row in receipts)
        report = {
            "schema_version": (
                "camp_dp_v25_batch8_training_support_reference_raw_artifact_v1"
            ),
            "status": (
                "passed_full_reference"
                if successful == POOL_COUNT
                and all(row["status"] == "computed" for row in row_references.values())
                and all(row["status"] == "computed" for row in pool_references.values())
                else "failed_reference_retained_full_denominator"
            ),
            "contract_root_sha256": contract_root,
            "contract_review_root_sha256": contract_review_root,
            "preflight_root_sha256": preflight_root,
            "preflight_review_root_sha256": preflight_review_root,
            "manifest_sha256": manifest["manifest_sha256"],
            "pool_slot_count": len(receipts),
            "successful_pool_count": successful,
            "failed_pool_count": POOL_COUNT - successful,
            "formal_model_call_count": model_calls,
            "selector_receipt_count": selector_receipts,
            "row_field_registry": row_field_registry(),
            "pool_field_registry": pool_field_registry(),
            "row_field_references": row_references,
            "pool_field_references": pool_references,
            "row_field_pool_first_summaries": pool_first,
            "failure_taxonomy": failures,
            "all_slots_retained": len(receipts) == POOL_COUNT,
            "weighted_total_created": False,
            "outcome_fields_read": [],
            "old_artifact_or_cas_written": False,
            "prohibited_run_counts": {key: 0 for key in PROHIBITED_RUNS},
            "runtime": runtime,
            "model_source_sha256": _sha_file(model_source),
            "checkpoint_sha256": _sha_file(checkpoint),
            "training_root_sha256": TRAINING_ROOT,
            "training_review_root_sha256": TRAINING_REVIEW_ROOT,
            "training_scale_sha256": assets.atom_scales_sha256,
        }
        np.savez(
            staging / "support_values.npz",
            atoms=atoms,
            static_scores=static_scores,
            scene_scores=scene_scores,
            static_masks=static_masks,
            scene_masks=scene_masks,
            static_margin=static_margin,
            scene_margin=scene_margin,
            static_eligible=static_eligible,
            scene_eligible=scene_eligible,
            static_selected=static_selected,
            scene_selected=scene_selected,
        )
        (staging / "report.json").write_bytes(canonical_bytes(report))
        (staging / "HEADS.json").write_bytes(
            canonical_bytes(
                {
                    "implementation_head": implementation_head,
                    "fixed_dp_head": FIXED_DP_HEAD,
                }
            )
        )
        (staging / "COMMAND").write_text(" ".join(sys.argv) + "\n", "utf-8")
        (staging / "run.exit").write_text("0\n", "ascii")
        if shutil.disk_usage(output.parent).free < CAPACITY_FLOOR_BYTES:
            raise RuntimeError("raw artifact would violate 10 GiB disk floor")
        root = seal_artifact(
            staging, label="V25 batch8 training-support raw reference"
        )
        os.replace(staging, output)
        verify_complete_seal(
            output, root, label="V25 batch8 training-support raw reference"
        )
        return root
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--fixed-dp-repo", type=Path, required=True)
    parser.add_argument("--implementation-head", required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-root", required=True)
    parser.add_argument("--contract-review", type=Path, required=True)
    parser.add_argument("--contract-review-root", required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--preflight-root", required=True)
    parser.add_argument("--preflight-review", type=Path, required=True)
    parser.add_argument("--preflight-review-root", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()
    print(
        materialize(
            repo=args.repo,
            fixed_dp_repo=args.fixed_dp_repo,
            implementation_head=args.implementation_head,
            contract_dir=args.contract,
            contract_root=args.contract_root,
            contract_review_dir=args.contract_review,
            contract_review_root=args.contract_review_root,
            preflight_dir=args.preflight,
            preflight_root=args.preflight_root,
            preflight_review_dir=args.preflight_review,
            preflight_review_root=args.preflight_review_root,
            output=args.output,
            device=args.device,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
